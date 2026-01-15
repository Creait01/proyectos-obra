# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CashRegisterDenominationLine(models.Model):
    _name = 'cash.register.denomination.line'
    _description = 'Línea de Denominación en Cierre de Caja'
    _order = 'denomination_value desc'

    close_line_id = fields.Many2one(
        'cash.register.close.line',
        string='Línea de Cierre',
        required=True,
        ondelete='cascade'
    )
    denomination_id = fields.Many2one(
        'cash.denomination',
        string='Denominación',
        required=True
    )
    denomination_value = fields.Float(
        related='denomination_id.value',
        string='Valor',
        store=True
    )
    denomination_type = fields.Selection(
        related='denomination_id.denomination_type',
        string='Tipo',
        store=True
    )
    currency_id = fields.Many2one(
        related='denomination_id.currency_id',
        string='Moneda',
        store=True
    )
    quantity = fields.Integer(
        string='Cantidad',
        default=0
    )
    total = fields.Monetary(
        string='Total',
        compute='_compute_total',
        store=True,
        currency_field='currency_id'
    )
    
    @api.depends('denomination_value', 'quantity')
    def _compute_total(self):
        for rec in self:
            rec.total = rec.denomination_value * rec.quantity
