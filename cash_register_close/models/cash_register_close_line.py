# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CashRegisterCloseLine(models.Model):
    _name = 'cash.register.close.line'
    _description = 'Línea de Cierre de Caja'
    _order = 'account_id'

    close_id = fields.Many2one(
        'cash.register.close',
        string='Cierre',
        required=True,
        ondelete='cascade'
    )
    account_id = fields.Many2one(
        'account.account',
        string='Cuenta Contable',
        required=True,
        domain=[('is_cash_account', '=', True)]
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        required=True,
        help='Moneda de esta cuenta de efectivo (USD o VEF/Bs)'
    )
    
    # Indica si la cuenta es en USD (para filtros y agrupaciones)
    is_usd_account = fields.Boolean(
        string='Es USD',
        compute='_compute_currency_type',
        store=True,
        help='Indica si esta cuenta maneja USD'
    )
    
    # Indica si la cuenta es en EUR
    is_eur_account = fields.Boolean(
        string='Es EUR',
        compute='_compute_currency_type',
        store=True,
        help='Indica si esta cuenta maneja EUR'
    )
    
    # =============================================
    # CAMPOS ÚNICOS CON MONEDA
    # =============================================
    initial_balance = fields.Monetary(
        string='Saldo Inicial',
        currency_field='currency_id',
        help='Saldo inicial de la cuenta'
    )
    total_income = fields.Monetary(
        string='Ingresos',
        currency_field='currency_id',
        help='Total de ingresos del día (débitos)'
    )
    total_expense = fields.Monetary(
        string='Egresos',
        currency_field='currency_id',
        help='Total de egresos del día (créditos)'
    )
    final_balance = fields.Monetary(
        string='Saldo Final',
        currency_field='currency_id',
        compute='_compute_final_balance',
        store=True,
        help='Saldo final = Inicial + Ingresos - Egresos'
    )
    counted_amount = fields.Monetary(
        string='Contado',
        currency_field='currency_id',
        help='Monto físico contado'
    )
    difference = fields.Monetary(
        string='Diferencia',
        currency_field='currency_id',
        compute='_compute_difference',
        store=True,
        help='Diferencia = Contado - Saldo Final'
    )
    
    # Estado de conteo
    is_counted = fields.Boolean(
        string='Contado',
        default=False,
        help='Indica si ya se realizó el conteo de efectivo'
    )
    
    # Denominaciones
    denomination_line_ids = fields.One2many(
        'cash.register.denomination.line',
        'close_line_id',
        string='Denominaciones'
    )
    
    # Billetes en mal estado
    bad_bills_ids = fields.One2many(
        'cash.register.bad.bills',
        'close_line_id',
        string='Billetes en Mal Estado'
    )
    total_bad_bills = fields.Monetary(
        string='Total Billetes Mal Estado',
        currency_field='currency_id',
        compute='_compute_total_bad_bills',
        store=True
    )
    
    # Movimientos del día
    movement_count = fields.Integer(
        string='Movimientos',
        compute='_compute_movement_count'
    )
    
    notes = fields.Text(string='Observaciones')
    
    # Campos relacionados
    date = fields.Date(related='close_id.date', store=True)
    company_id = fields.Many2one(related='close_id.company_id', store=True)
    state = fields.Selection(related='close_id.state', store=True)
    
    @api.depends('currency_id')
    def _compute_currency_type(self):
        for rec in self:
            currency_name = rec.currency_id.name if rec.currency_id else ''
            rec.is_usd_account = currency_name == 'USD'
            rec.is_eur_account = currency_name == 'EUR'
    
    @api.depends('initial_balance', 'total_income', 'total_expense')
    def _compute_final_balance(self):
        for rec in self:
            rec.final_balance = rec.initial_balance + rec.total_income - rec.total_expense
    
    @api.depends('final_balance', 'counted_amount')
    def _compute_difference(self):
        for rec in self:
            rec.difference = rec.counted_amount - rec.final_balance
    
    @api.depends('bad_bills_ids', 'bad_bills_ids.total')
    def _compute_total_bad_bills(self):
        for rec in self:
            rec.total_bad_bills = sum(rec.bad_bills_ids.mapped('total'))
    
    @api.depends('account_id', 'close_id.date')
    def _compute_movement_count(self):
        for rec in self:
            if rec.account_id and rec.close_id.date:
                count = self.env['account.move.line'].search_count([
                    ('account_id', '=', rec.account_id.id),
                    ('date', '=', rec.close_id.date),
                    ('parent_state', '=', 'posted'),
                ])
                rec.movement_count = count
            else:
                rec.movement_count = 0
    
    def action_load_denominations(self):
        """Carga las denominaciones disponibles para esta moneda"""
        self.ensure_one()
        
        # Eliminar denominaciones existentes
        self.denomination_line_ids.unlink()
        
        # Buscar denominaciones para esta moneda
        denominations = self.env['cash.denomination'].search([
            ('currency_id', '=', self.currency_id.id),
            ('active', '=', True)
        ], order='value desc')
        
        if not denominations:
            raise UserError(_('No hay denominaciones configuradas para la moneda %s.\n'
                            'Por favor, configure las denominaciones primero.') % self.currency_id.name)
        
        for denom in denominations:
            self.env['cash.register.denomination.line'].create({
                'close_line_id': self.id,
                'denomination_id': denom.id,
                'quantity': 0,
            })
        
        return True
    
    def action_copy_from_previous_close(self):
        """Copia las cantidades del cierre anterior directamente a las líneas actuales"""
        self.ensure_one()
        
        # Buscar el cierre anterior de la misma cuenta y empresa
        previous_line = self.env['cash.register.close.line'].search([
            ('account_id', '=', self.account_id.id),
            ('company_id', '=', self.company_id.id),
            ('close_id.state', 'in', ['closed', 'confirmed']),
            ('close_id.date', '<', self.close_id.date),
        ], order='close_id desc', limit=1)
        
        if not previous_line:
            raise UserError(_('No se encontró un cierre anterior para esta cuenta.'))
        
        # Si no hay denominaciones cargadas, cargarlas primero
        if not self.denomination_line_ids:
            self.action_load_denominations()
        
        # Copiar cantidades de denominaciones
        for prev_denom in previous_line.denomination_line_ids:
            if prev_denom.denomination_id:
                # Buscar la línea correspondiente en el cierre actual
                current_denom = self.denomination_line_ids.filtered(
                    lambda d: d.denomination_id.id == prev_denom.denomination_id.id
                )
                if current_denom:
                    current_denom.write({'quantity': prev_denom.quantity})
        
        # Copiar billetes en mal estado
        self.bad_bills_ids.unlink()
        for prev_bad in previous_line.bad_bills_ids:
            if prev_bad.denomination_id:
                self.env['cash.register.bad.bills'].create({
                    'close_line_id': self.id,
                    'denomination_id': prev_bad.denomination_id.id,
                    'quantity': prev_bad.quantity,
                    'condition': prev_bad.condition,
                    'notes': prev_bad.notes,
                })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Copiado Exitoso'),
                'message': _('Se copiaron las cantidades del cierre del %s') % (
                    previous_line.close_id.date.strftime('%d/%m/%Y') if previous_line.close_id.date else ''
                ),
                'sticky': False,
                'type': 'success',
            }
        }
    
    def action_count_cash(self):
        """Abre el wizard para contar efectivo"""
        self.ensure_one()
        
        # Si no hay denominaciones cargadas, cargarlas primero
        if not self.denomination_line_ids:
            self.action_load_denominations()
        
        return {
            'name': _('Contar Efectivo - %s') % self.account_id.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'cash.register.close.line',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'form_view_initial_mode': 'edit',
            },
            'views': [(self.env.ref('cash_register_close.view_cash_register_close_line_count_form').id, 'form')],
        }
    
    def action_confirm_count(self):
        """Confirma el conteo de efectivo"""
        self.ensure_one()
        
        # Calcular el total desde las denominaciones (billetes en buen estado)
        total_from_denominations = sum(self.denomination_line_ids.mapped('total'))
        
        # Sumar los billetes en mal estado (se cuentan por separado para no duplicar trabajo)
        total_bad_bills = sum(self.bad_bills_ids.mapped('total'))
        
        self.write({
            'counted_amount': total_from_denominations + total_bad_bills,
            'is_counted': True,
        })
        
        return {'type': 'ir.actions.act_window_close'}
    
    def action_view_movements(self):
        """Ver movimientos de esta cuenta - vista simplificada"""
        self.ensure_one()
        return {
            'name': _('Movimientos - %s') % self.account_id.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('cash_register_close.view_account_move_line_cash_close_tree').id, 'tree'),
                (self.env.ref('cash_register_close.view_account_move_line_cash_close_form').id, 'form'),
            ],
            'domain': [
                ('account_id', '=', self.account_id.id),
                ('date', '=', self.close_id.date),
                ('parent_state', '=', 'posted'),
            ],
            'context': {
                'create': False,
                'edit': False,
                'delete': False,
            }
        }
    
    def get_movements_for_report(self):
        """Obtiene los movimientos formateados para el reporte"""
        self.ensure_one()
        moves = self.env['account.move.line'].search([
            ('account_id', '=', self.account_id.id),
            ('date', '=', self.close_id.date),
            ('parent_state', '=', 'posted'),
        ], order='date, id')
        
        result = []
        for move in moves:
            # Determinar el monto según la moneda de la cuenta
            if self.is_usd_account:
                # USD: usar debit_usd - credit_usd
                debit_usd = getattr(move, 'debit_usd', 0) or 0
                credit_usd = getattr(move, 'credit_usd', 0) or 0
                amount = debit_usd - credit_usd
            elif self.is_eur_account:
                # EUR: usar debit_usd - credit_usd igual que USD
                debit_usd = getattr(move, 'debit_usd', 0) or 0
                credit_usd = getattr(move, 'credit_usd', 0) or 0
                amount = debit_usd - credit_usd
            else:
                # Bs: usar balance (debit - credit)
                amount = move.balance or 0
            
            result.append({
                'date': move.date.strftime('%d/%m/%Y') if move.date else '',
                'name': move.name or move.move_id.name or '',
                'ref': move.ref or '',
                'partner': move.partner_id.name if move.partner_id else '-',
                'amount': amount,
                'move_type': 'Ingreso' if amount >= 0 else 'Egreso',
            })
        
        return result
