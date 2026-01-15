# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CashRegisterCopyPreviousWizard(models.TransientModel):
    _name = 'cash.register.copy.previous.wizard'
    _description = 'Wizard para copiar y verificar cierre anterior'

    close_line_id = fields.Many2one(
        'cash.register.close.line',
        string='Línea de Cierre',
        required=True,
        ondelete='cascade'
    )
    previous_close_line_id = fields.Many2one(
        'cash.register.close.line',
        string='Cierre Anterior',
        readonly=True
    )
    previous_date = fields.Date(
        string='Fecha del Cierre Anterior',
        related='previous_close_line_id.close_id.date',
        readonly=True
    )
    account_id = fields.Many2one(
        'account.account',
        string='Cuenta',
        related='close_line_id.account_id',
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='close_line_id.currency_id',
        readonly=True
    )
    
    # Líneas de denominaciones (previsualización editable)
    denomination_line_ids = fields.One2many(
        'cash.register.copy.previous.wizard.denom.line',
        'wizard_id',
        string='Denominaciones'
    )
    
    # Líneas de billetes en mal estado (previsualización editable)
    bad_bills_line_ids = fields.One2many(
        'cash.register.copy.previous.wizard.bad.line',
        'wizard_id',
        string='Billetes en Mal Estado'
    )
    
    # Totales
    total_denominations = fields.Float(
        string='Total Denominaciones',
        compute='_compute_totals',
        store=True
    )
    total_bad_bills = fields.Float(
        string='Total Billetes Mal Estado',
        compute='_compute_totals',
        store=True
    )
    total_counted = fields.Float(
        string='Total Contado',
        compute='_compute_totals',
        store=True
    )
    
    # Qué copiar
    copy_denominations = fields.Boolean(
        string='Copiar Denominaciones',
        default=True
    )
    copy_bad_bills = fields.Boolean(
        string='Copiar Billetes en Mal Estado',
        default=True
    )
    
    @api.depends('denomination_line_ids.total', 'bad_bills_line_ids.total')
    def _compute_totals(self):
        for wizard in self:
            wizard.total_denominations = sum(wizard.denomination_line_ids.mapped('total'))
            wizard.total_bad_bills = sum(wizard.bad_bills_line_ids.mapped('total'))
            wizard.total_counted = wizard.total_denominations + wizard.total_bad_bills
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        
        close_line_id = self._context.get('active_id')
        if not close_line_id:
            return res
        
        close_line = self.env['cash.register.close.line'].browse(close_line_id)
        res['close_line_id'] = close_line_id
        
        # Buscar el cierre anterior
        previous_line = self.env['cash.register.close.line'].search([
            ('account_id', '=', close_line.account_id.id),
            ('company_id', '=', close_line.company_id.id),
            ('close_id.state', 'in', ['closed', 'confirmed']),
            ('close_id.date', '<', close_line.close_id.date),
        ], order='close_id desc', limit=1)
        
        if not previous_line:
            raise UserError(_('No se encontró un cierre anterior para esta cuenta.'))
        
        res['previous_close_line_id'] = previous_line.id
        
        # Obtener la moneda de la cuenta para buscar denominaciones
        account_currency = close_line.account_id.currency_id or close_line.company_id.currency_id
        
        # Precargar denominaciones del cierre anterior
        denom_lines = []
        for prev_denom in previous_line.denomination_line_ids:
            denomination = prev_denom.denomination_id
            
            # Si no tiene denomination_id pero tiene valor, intentar encontrar la denominación
            if not denomination and prev_denom.denomination_value:
                denomination = self.env['cash.denomination'].search([
                    ('value', '=', prev_denom.denomination_value),
                    ('currency_id', '=', account_currency.id),
                ], limit=1)
            
            if denomination:
                denom_lines.append((0, 0, {
                    'denomination_id': denomination.id,
                    'quantity': prev_denom.quantity or 0,
                }))
        
        # Solo asignar si hay líneas válidas
        if denom_lines:
            res['denomination_line_ids'] = denom_lines
        
        # Precargar billetes en mal estado del cierre anterior
        bad_lines = []
        for prev_bad in previous_line.bad_bills_ids:
            denomination = prev_bad.denomination_id
            
            # Si no tiene denomination_id pero tiene valor, intentar encontrar la denominación
            if not denomination and prev_bad.denomination_value:
                denomination = self.env['cash.denomination'].search([
                    ('value', '=', prev_bad.denomination_value),
                    ('currency_id', '=', account_currency.id),
                    ('denomination_type', '=', 'bill'),
                ], limit=1)
            
            if denomination:
                bad_lines.append((0, 0, {
                    'denomination_id': denomination.id,
                    'quantity': prev_bad.quantity or 0,
                    'condition': prev_bad.condition or 'damaged',
                    'notes': prev_bad.notes or '',
                }))
        
        # Solo asignar si hay líneas válidas
        if bad_lines:
            res['bad_bills_line_ids'] = bad_lines
        
        return res
    
    def action_confirm(self):
        """Confirma la copia y aplica los cambios al cierre actual"""
        self.ensure_one()
        
        close_line = self.close_line_id
        copied_denoms = 0
        copied_bad = 0
        
        # Copiar denominaciones si está marcado
        if self.copy_denominations:
            close_line.denomination_line_ids.unlink()
            for wiz_denom in self.denomination_line_ids.filtered(lambda l: l.denomination_id):
                self.env['cash.register.denomination.line'].create({
                    'close_line_id': close_line.id,
                    'denomination_id': wiz_denom.denomination_id.id,
                    'quantity': wiz_denom.quantity,
                })
                copied_denoms += 1
        
        # Copiar billetes en mal estado si está marcado
        if self.copy_bad_bills:
            close_line.bad_bills_ids.unlink()
            for wiz_bad in self.bad_bills_line_ids.filtered(lambda l: l.denomination_id):
                self.env['cash.register.bad.bills'].create({
                    'close_line_id': close_line.id,
                    'denomination_id': wiz_bad.denomination_id.id,
                    'quantity': wiz_bad.quantity,
                    'condition': wiz_bad.condition,
                    'notes': wiz_bad.notes,
                })
                copied_bad += 1
        
        # Mostrar mensaje de éxito
        message = _('Se copiaron %s denominaciones y %s billetes en mal estado del cierre del %s') % (
            copied_denoms, copied_bad,
            self.previous_date.strftime('%d/%m/%Y') if self.previous_date else ''
        )
        
        # Cerrar el wizard y mostrar notificación
        return {
            'type': 'ir.actions.act_window_close',
        }


class CashRegisterCopyPreviousWizardDenomLine(models.TransientModel):
    _name = 'cash.register.copy.previous.wizard.denom.line'
    _description = 'Línea de denominación del wizard'

    def init(self):
        """Eliminar constraint NOT NULL si existe"""
        self.env.cr.execute("""
            ALTER TABLE IF EXISTS cash_register_copy_previous_wizard_denom_line 
            ALTER COLUMN denomination_id DROP NOT NULL;
        """)

    wizard_id = fields.Many2one(
        'cash.register.copy.previous.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    denomination_id = fields.Many2one(
        'cash.denomination',
        string='Denominación'
    )
    denomination_type = fields.Selection(
        related='denomination_id.denomination_type',
        string='Tipo',
        readonly=True
    )
    denomination_value = fields.Float(
        related='denomination_id.value',
        string='Valor',
        readonly=True
    )
    quantity = fields.Integer(
        string='Cantidad',
        default=0
    )
    total = fields.Float(
        string='Total',
        compute='_compute_total',
        store=True
    )
    
    @api.depends('denomination_value', 'quantity')
    def _compute_total(self):
        for line in self:
            line.total = line.denomination_value * line.quantity


class CashRegisterCopyPreviousWizardBadLine(models.TransientModel):
    _name = 'cash.register.copy.previous.wizard.bad.line'
    _description = 'Línea de billetes mal estado del wizard'

    def init(self):
        """Eliminar constraint NOT NULL si existe"""
        self.env.cr.execute("""
            ALTER TABLE IF EXISTS cash_register_copy_previous_wizard_bad_line 
            ALTER COLUMN denomination_id DROP NOT NULL;
        """)

    wizard_id = fields.Many2one(
        'cash.register.copy.previous.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    denomination_id = fields.Many2one(
        'cash.denomination',
        string='Denominación',
        domain="[('denomination_type', '=', 'bill')]"
    )
    denomination_value = fields.Float(
        related='denomination_id.value',
        string='Valor',
        readonly=True
    )
    quantity = fields.Integer(
        string='Cantidad',
        default=0
    )
    condition = fields.Selection([
        ('damaged', 'Deteriorado'),
        ('torn', 'Roto'),
        ('wet', 'Mojado'),
        ('marked', 'Marcado'),
        ('other', 'Otro')
    ], string='Estado', default='damaged')
    notes = fields.Char(string='Notas')
    total = fields.Float(
        string='Total',
        compute='_compute_total',
        store=True
    )
    
    @api.depends('denomination_value', 'quantity')
    def _compute_total(self):
        for line in self:
            line.total = line.denomination_value * line.quantity
