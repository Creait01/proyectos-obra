# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CashDenomination(models.Model):
    _name = 'cash.denomination'
    _description = 'Denominación de Billetes/Monedas'
    _order = 'currency_id, value desc'

    name = fields.Char(
        string='Nombre',
        compute='_compute_name',
        store=True
    )
    value = fields.Float(
        string='Valor',
        required=True,
        help='Valor nominal de la denominación'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        required=True,
        default=lambda self: self.env.company.currency_id
    )
    denomination_type = fields.Selection([
        ('bill', 'Billete'),
        ('coin', 'Moneda')
    ], string='Tipo', default='bill', required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    
    @api.depends('value', 'currency_id', 'denomination_type')
    def _compute_name(self):
        for rec in self:
            type_name = 'Billete' if rec.denomination_type == 'bill' else 'Moneda'
            rec.name = f"{type_name} de {rec.currency_id.symbol}{rec.value:,.0f}" if rec.currency_id else f"{type_name} de {rec.value:,.0f}"
    
    _sql_constraints = [
        ('unique_denomination', 'unique(value, currency_id, denomination_type)', 
         'Ya existe una denominación con este valor para esta moneda!')
    ]
