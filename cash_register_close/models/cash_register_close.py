# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta
import json


class CashRegisterClose(models.Model):
    _name = 'cash.register.close'
    _description = 'Cierre de Caja Diario'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Referencia',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nuevo')
    )
    date = fields.Date(
        string='Fecha de Cierre',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
        tracking=True
    )
    user_id = fields.Many2one(
        'res.users',
        string='Responsable',
        required=True,
        default=lambda self: self.env.user,
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('in_progress', 'En Proceso'),
        ('closed', 'Cerrado'),
        ('confirmed', 'Confirmado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='draft', tracking=True)
    
    # Campos de confirmación
    confirmed_by_id = fields.Many2one(
        'res.users',
        string='Confirmado por',
        readonly=True,
        tracking=True
    )
    confirmed_date = fields.Datetime(
        string='Fecha de Confirmación',
        readonly=True,
        tracking=True
    )
    
    # Campos de firma digital
    closed_signature = fields.Binary(
        string='Firma del Responsable',
        help='Firma digital del responsable del cierre',
        copy=False
    )
    closed_date = fields.Datetime(
        string='Fecha de Cierre',
        readonly=True,
        copy=False
    )
    confirmed_signature = fields.Binary(
        string='Firma del Supervisor',
        help='Firma digital del supervisor que confirma',
        copy=False
    )
    
    # Líneas de cierre por cuenta
    line_ids = fields.One2many(
        'cash.register.close.line',
        'close_id',
        string='Líneas de Cierre'
    )
    
    # Líneas de cuentas bancarias
    bank_line_ids = fields.One2many(
        'cash.register.bank.line',
        'close_id',
        string='Cuentas Bancarias'
    )
    
    # Moneda de la compañía (Bs)
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda Local',
        related='company_id.currency_id',
        store=True
    )
    
    # Moneda USD para referencia
    currency_usd_id = fields.Many2one(
        'res.currency',
        string='Moneda USD',
        compute='_compute_currency_usd',
        store=True
    )
    
    # =============================================
    # TOTALES EN BOLÍVARES (Bs)
    # =============================================
    total_initial_balance_bs = fields.Float(
        string='Total Saldo Inicial Bs',
        compute='_compute_totals_bs',
        store=True,
        digits='Product Price'
    )
    total_income_bs = fields.Float(
        string='Total Ingresos Bs',
        compute='_compute_totals_bs',
        store=True,
        digits='Product Price'
    )
    total_expense_bs = fields.Float(
        string='Total Egresos Bs',
        compute='_compute_totals_bs',
        store=True,
        digits='Product Price'
    )
    total_final_balance_bs = fields.Float(
        string='Total Saldo Final Bs',
        compute='_compute_totals_bs',
        store=True,
        digits='Product Price'
    )
    total_counted_bs = fields.Float(
        string='Total Contado Bs',
        compute='_compute_totals_bs',
        store=True,
        digits='Product Price'
    )
    total_difference_bs = fields.Float(
        string='Total Diferencia Bs',
        compute='_compute_totals_bs',
        store=True,
        digits='Product Price'
    )
    
    # =============================================
    # TOTALES EN USD
    # =============================================
    total_initial_balance_usd = fields.Float(
        string='Total Saldo Inicial USD',
        compute='_compute_totals_usd',
        store=True,
        digits='Product Price'
    )
    total_income_usd = fields.Float(
        string='Total Ingresos USD',
        compute='_compute_totals_usd',
        store=True,
        digits='Product Price'
    )
    total_expense_usd = fields.Float(
        string='Total Egresos USD',
        compute='_compute_totals_usd',
        store=True,
        digits='Product Price'
    )
    total_final_balance_usd = fields.Float(
        string='Total Saldo Final USD',
        compute='_compute_totals_usd',
        store=True,
        digits='Product Price'
    )
    total_counted_usd = fields.Float(
        string='Total Contado USD',
        compute='_compute_totals_usd',
        store=True,
        digits='Product Price'
    )
    total_difference_usd = fields.Float(
        string='Total Diferencia USD',
        compute='_compute_totals_usd',
        store=True,
        digits='Product Price'
    )
    
    # =============================================
    # TOTALES EN EUR
    # =============================================
    total_initial_balance_eur = fields.Float(
        string='Total Saldo Inicial EUR',
        compute='_compute_totals_eur',
        store=True,
        digits='Product Price'
    )
    total_income_eur = fields.Float(
        string='Total Ingresos EUR',
        compute='_compute_totals_eur',
        store=True,
        digits='Product Price'
    )
    total_expense_eur = fields.Float(
        string='Total Egresos EUR',
        compute='_compute_totals_eur',
        store=True,
        digits='Product Price'
    )
    total_final_balance_eur = fields.Float(
        string='Total Saldo Final EUR',
        compute='_compute_totals_eur',
        store=True,
        digits='Product Price'
    )
    total_counted_eur = fields.Float(
        string='Total Contado EUR',
        compute='_compute_totals_eur',
        store=True,
        digits='Product Price'
    )
    total_difference_eur = fields.Float(
        string='Total Diferencia EUR',
        compute='_compute_totals_eur',
        store=True,
        digits='Product Price'
    )
    
    notes = fields.Html(string='Observaciones')
    
    # Estadísticas para el dashboard
    accounts_count = fields.Integer(
        string='Número de Cuentas',
        compute='_compute_accounts_count'
    )
    accounts_bs_count = fields.Integer(
        string='Cuentas en Bs',
        compute='_compute_accounts_count'
    )
    accounts_usd_count = fields.Integer(
        string='Cuentas en USD',
        compute='_compute_accounts_count'
    )
    accounts_eur_count = fields.Integer(
        string='Cuentas en EUR',
        compute='_compute_accounts_count'
    )
    
    # JSON para datos del dashboard
    dashboard_data = fields.Text(
        string='Datos Dashboard',
        compute='_compute_dashboard_data'
    )
    
    @api.depends('company_id')
    def _compute_currency_usd(self):
        usd = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
        for rec in self:
            rec.currency_usd_id = usd.id if usd else False
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('Nuevo')) == _('Nuevo'):
            vals['name'] = self.env['ir.sequence'].next_by_code('cash.register.close') or _('Nuevo')
        return super().create(vals)
    
    @api.depends('line_ids', 'line_ids.initial_balance', 'line_ids.total_income',
                 'line_ids.total_expense', 'line_ids.final_balance', 
                 'line_ids.counted_amount', 'line_ids.difference', 'line_ids.is_usd_account', 'line_ids.is_eur_account')
    def _compute_totals_bs(self):
        """Suma totales de líneas cuya moneda NO es USD ni EUR (Bs/VEF)"""
        for rec in self:
            lines_bs = rec.line_ids.filtered(lambda l: not l.is_usd_account and not l.is_eur_account)
            rec.total_initial_balance_bs = sum(lines_bs.mapped('initial_balance'))
            rec.total_income_bs = sum(lines_bs.mapped('total_income'))
            rec.total_expense_bs = sum(lines_bs.mapped('total_expense'))
            rec.total_final_balance_bs = sum(lines_bs.mapped('final_balance'))
            rec.total_counted_bs = sum(lines_bs.mapped('counted_amount'))
            rec.total_difference_bs = sum(lines_bs.mapped('difference'))
    
    @api.depends('line_ids', 'line_ids.initial_balance', 'line_ids.total_income',
                 'line_ids.total_expense', 'line_ids.final_balance', 
                 'line_ids.counted_amount', 'line_ids.difference', 'line_ids.is_usd_account')
    def _compute_totals_usd(self):
        """Suma totales de líneas cuya moneda es USD"""
        for rec in self:
            lines_usd = rec.line_ids.filtered('is_usd_account')
            rec.total_initial_balance_usd = sum(lines_usd.mapped('initial_balance'))
            rec.total_income_usd = sum(lines_usd.mapped('total_income'))
            rec.total_expense_usd = sum(lines_usd.mapped('total_expense'))
            rec.total_final_balance_usd = sum(lines_usd.mapped('final_balance'))
            rec.total_counted_usd = sum(lines_usd.mapped('counted_amount'))
            rec.total_difference_usd = sum(lines_usd.mapped('difference'))
    
    @api.depends('line_ids', 'line_ids.initial_balance', 'line_ids.total_income',
                 'line_ids.total_expense', 'line_ids.final_balance', 
                 'line_ids.counted_amount', 'line_ids.difference', 'line_ids.is_eur_account')
    def _compute_totals_eur(self):
        """Suma totales de líneas cuya moneda es EUR"""
        for rec in self:
            lines_eur = rec.line_ids.filtered('is_eur_account')
            rec.total_initial_balance_eur = sum(lines_eur.mapped('initial_balance'))
            rec.total_income_eur = sum(lines_eur.mapped('total_income'))
            rec.total_expense_eur = sum(lines_eur.mapped('total_expense'))
            rec.total_final_balance_eur = sum(lines_eur.mapped('final_balance'))
            rec.total_counted_eur = sum(lines_eur.mapped('counted_amount'))
            rec.total_difference_eur = sum(lines_eur.mapped('difference'))
    
    @api.depends('line_ids', 'line_ids.is_usd_account', 'line_ids.is_eur_account')
    def _compute_accounts_count(self):
        for rec in self:
            rec.accounts_count = len(rec.line_ids)
            rec.accounts_usd_count = len(rec.line_ids.filtered('is_usd_account'))
            rec.accounts_eur_count = len(rec.line_ids.filtered('is_eur_account'))
            rec.accounts_bs_count = len(rec.line_ids.filtered(lambda l: not l.is_usd_account and not l.is_eur_account))
    
    @api.depends('line_ids')
    def _compute_dashboard_data(self):
        for rec in self:
            data = {
                'total_accounts': len(rec.line_ids),
                'accounts_bs': rec.accounts_bs_count,
                'accounts_usd': rec.accounts_usd_count,
                'totals_bs': {
                    'initial': rec.total_initial_balance_bs,
                    'income': rec.total_income_bs,
                    'expense': rec.total_expense_bs,
                    'final': rec.total_final_balance_bs,
                    'counted': rec.total_counted_bs,
                    'difference': rec.total_difference_bs,
                },
                'totals_usd': {
                    'initial': rec.total_initial_balance_usd,
                    'income': rec.total_income_usd,
                    'expense': rec.total_expense_usd,
                    'final': rec.total_final_balance_usd,
                    'counted': rec.total_counted_usd,
                    'difference': rec.total_difference_usd,
                },
                'accounts': []
            }
            for line in rec.line_ids:
                data['accounts'].append({
                    'id': line.id,
                    'name': line.account_id.name,
                    'code': line.account_id.code,
                    'is_usd': line.is_usd_account,
                    'currency': line.currency_id.symbol if line.currency_id else 'Bs',
                    'initial': line.initial_balance,
                    'income': line.total_income,
                    'expense': line.total_expense,
                    'final': line.final_balance,
                    'counted': line.counted_amount,
                    'difference': line.difference,
                })
            rec.dashboard_data = json.dumps(data)
    
    def action_generate_lines(self):
        """Genera las líneas de cierre basándose en las cuentas de efectivo"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Solo puede generar líneas en estado Borrador'))
        
        # Eliminar líneas existentes
        self.line_ids.unlink()
        
        # IMPORTANTE: Buscar cuentas usando el contexto correcto de la empresa del cierre
        # Usamos sudo() y with_company() para acceso cross-company
        cash_accounts = self.env['account.account'].sudo().with_company(self.company_id).search([
            ('is_cash_account', '=', True),
            ('company_id', '=', self.company_id.id),
            ('deprecated', '=', False)
        ])
        
        if not cash_accounts:
            raise UserError(_('No hay cuentas de efectivo configuradas para esta compañía.\n'
                            'Por favor, marque las cuentas contables como "Cuenta de Efectivo".'))
        
        line_vals = []
        
        for account in cash_accounts:
            # Obtener la moneda específica del cierre de caja (NO la nativa de Odoo)
            account_currency = account.cash_close_currency_id or self.currency_id
            currency_name = account_currency.name if account_currency else ''
            
            # Obtener los saldos usando los métodos del account
            balances = account.get_cash_balances_dual_currency(self.date)
            
            # Usar los valores según la moneda de la cuenta
            if currency_name == 'USD':
                initial = balances.get('initial_usd', 0)
                income = balances.get('income_usd', 0)
                expense = balances.get('expense_usd', 0)
            elif currency_name == 'EUR':
                initial = balances.get('initial_eur', 0)
                income = balances.get('income_eur', 0)
                expense = balances.get('expense_eur', 0)
            else:
                # Bs u otra moneda local
                initial = balances.get('initial_bs', 0)
                income = balances.get('income_bs', 0)
                expense = balances.get('expense_bs', 0)
            
            line_vals.append({
                'close_id': self.id,
                'account_id': account.id,
                'currency_id': account_currency.id,
                'initial_balance': initial,
                'total_income': income,
                'total_expense': expense,
            })
        
        self.env['cash.register.close.line'].create(line_vals)
        self.state = 'in_progress'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Líneas Generadas'),
                'message': _('Se generaron %s líneas de cierre correctamente.') % len(line_vals),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def _get_user_signature(self, user=None):
        """Obtiene la firma del usuario desde su configuración"""
        if user is None:
            user = self.env.user
        # Buscar firma en los campos comunes de Odoo
        signature = None
        # Campo de firma digital (módulo sign o hr)
        if hasattr(user, 'sign_signature') and user.sign_signature:
            signature = user.sign_signature
        # Campo de firma del empleado relacionado
        elif hasattr(user, 'employee_id') and user.employee_id:
            emp = user.employee_id
            if hasattr(emp, 'sign_signature') and emp.sign_signature:
                signature = emp.sign_signature
        return signature
    
    def action_close(self):
        """Cierra el cierre de caja con la firma del usuario"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_('Solo puede cerrar un cierre en estado "En Proceso"'))
        
        # Auto-marcar como contado las líneas con saldo final = 0
        for line in self.line_ids:
            if not line.is_counted and line.final_balance == 0:
                line.is_counted = True
                line.counted_amount = 0
        
        # Validar que todas las líneas con saldo > 0 tengan conteo
        for line in self.line_ids:
            if not line.is_counted and line.final_balance != 0:
                raise UserError(_('Debe contar el efectivo de todas las cuentas con saldo antes de cerrar.\n'
                                'Cuenta pendiente: %s (Saldo: %s)') % (line.account_id.display_name, line.final_balance))
        
        # Obtener la firma del usuario que cierra
        user_signature = self._get_user_signature(self.user_id)
        
        self.write({
            'state': 'closed',
            'closed_signature': user_signature,
            'closed_date': fields.Datetime.now(),
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }
    
    def action_confirm(self):
        """Confirma el cierre de caja con la firma del supervisor"""
        self.ensure_one()
        if self.state != 'closed':
            raise UserError(_('Solo puede confirmar un cierre en estado "Cerrado"'))
        
        # Obtener la firma del usuario que confirma
        user_signature = self._get_user_signature()
        
        self.write({
            'state': 'confirmed',
            'confirmed_by_id': self.env.user.id,
            'confirmed_date': fields.Datetime.now(),
            'confirmed_signature': user_signature,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }
    
    def action_cancel(self):
        """Cancela el cierre de caja"""
        self.ensure_one()
        if self.state == 'closed':
            raise UserError(_('No puede cancelar un cierre que ya ha sido cerrado.'))
        self.state = 'cancelled'
    
    def action_draft(self):
        """Regresa a borrador"""
        self.ensure_one()
        if self.state == 'closed':
            raise UserError(_('No puede pasar a borrador un cierre que ya ha sido cerrado.'))
        self.state = 'draft'
    
    def action_print_report(self):
        """Imprime el reporte PDF del cierre"""
        self.ensure_one()
        return self.env.ref('cash_register_close.action_report_cash_register_close').report_action(self)
    
    def action_view_movements(self):
        """Abre vista de movimientos contables del día"""
        self.ensure_one()
        account_ids = self.line_ids.mapped('account_id').ids
        return {
            'name': _('Movimientos del Día'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': [
                ('account_id', 'in', account_ids),
                ('date', '=', self.date),
                ('parent_state', '=', 'posted'),
            ],
            'context': {
                'search_default_group_by_account': 1,
            }
        }
    
    @api.model
    def get_historical_balances(self, days=7):
        """Obtiene los balances históricos de los últimos X días"""
        result = []
        today = fields.Date.context_today(self)
        
        cash_accounts = self.env['account.account'].search([
            ('is_cash_account', '=', True),
            ('company_id', '=', self.env.company.id),
            ('deprecated', '=', False)
        ])
        
        for i in range(days):
            check_date = today - timedelta(days=i)
            day_data = {
                'date': check_date.strftime('%Y-%m-%d'),
                'date_display': check_date.strftime('%d/%m/%Y'),
                'accounts': []
            }
            
            for account in cash_accounts:
                balances = account.get_cash_balances_dual_currency(check_date)
                day_data['accounts'].append({
                    'account_id': account.id,
                    'account_name': account.display_name,
                    'balance_bs': balances.get('balance_bs', 0),
                    'balance_usd': balances.get('balance_usd', 0),
                    'currency': account.cash_close_currency_id.symbol if account.cash_close_currency_id else 'Bs'
                })
            
            result.append(day_data)
        
        return result
    
    def action_open_wizard_mass_close(self):
        """Abre el wizard para cierre masivo"""
        return {
            'name': _('Cierre Masivo de Cajas'),
            'type': 'ir.actions.act_window',
            'res_model': 'cash.register.close.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_date': self.date or fields.Date.context_today(self),
            }
        }


class CashRegisterCloseAllCompanies(models.TransientModel):
    """Modelo transitorio para cierre de todas las empresas"""
    _name = 'cash.register.close.all'
    _description = 'Cierre de Caja Todas las Empresas'
    
    date = fields.Date(
        string='Fecha de Cierre',
        required=True,
        default=fields.Date.context_today
    )
    company_ids = fields.Many2many(
        'res.company',
        string='Compañías',
        default=lambda self: self.env['res.company'].search([])
    )
    
    def action_create_closes(self):
        """Crea cierres de caja para todas las compañías seleccionadas"""
        closes = self.env['cash.register.close']
        for company in self.company_ids:
            # Verificar si ya existe un cierre para esta fecha y compañía
            existing = self.env['cash.register.close'].search([
                ('date', '=', self.date),
                ('company_id', '=', company.id),
                ('state', '!=', 'cancelled')
            ], limit=1)
            
            if existing:
                closes |= existing
                continue
            
            close = self.env['cash.register.close'].create({
                'date': self.date,
                'company_id': company.id,
                'user_id': self.env.user.id,
            })
            close.action_generate_lines()
            closes |= close
        
        if len(closes) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'cash.register.close',
                'res_id': closes.id,
                'view_mode': 'form',
                'target': 'current',
            }
        
        return {
            'name': _('Cierres de Caja'),
            'type': 'ir.actions.act_window',
            'res_model': 'cash.register.close',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', closes.ids)],
            'target': 'current',
        }
