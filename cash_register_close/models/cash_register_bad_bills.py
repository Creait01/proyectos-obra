# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CashRegisterBadBills(models.Model):
    _name = 'cash.register.bad.bills'
    _description = 'Billetes en Mal Estado'
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
        required=True,
        domain=[('denomination_type', '=', 'bill')]
    )
    denomination_value = fields.Float(
        related='denomination_id.value',
        string='Valor',
        store=True
    )
    currency_id = fields.Many2one(
        related='denomination_id.currency_id',
        string='Moneda',
        store=True
    )
    quantity = fields.Integer(
        string='Cantidad',
        default=0,
        help='Cantidad de billetes en mal estado'
    )
    total = fields.Monetary(
        string='Total',
        compute='_compute_total',
        store=True,
        currency_field='currency_id'
    )
    condition = fields.Selection([
        ('damaged', 'Dañado'),
        ('torn', 'Roto'),
        ('worn', 'Desgastado'),
        ('counterfeit', 'Sospecha Falsificación'),
        ('other', 'Otro')
    ], string='Condición', default='damaged', required=True)
    notes = fields.Char(string='Observaciones')
    
    @api.depends('denomination_value', 'quantity')
    def _compute_total(self):
        for rec in self:
            rec.total = rec.denomination_value * rec.quantity
