# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CashRegisterBankLine(models.Model):
    _name = 'cash.register.bank.line'
    _description = 'Línea de Cuenta Bancaria en Cierre de Caja'
    _order = 'account_id'

    close_id = fields.Many2one(
        'cash.register.close',
        string='Cierre de Caja',
        required=True,
        ondelete='cascade'
    )
    account_id = fields.Many2one(
        'account.account',
        string='Cuenta Bancaria',
        required=True,
        domain="[('is_bank_account', '=', True)]"
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='account_id.currency_id',
        store=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        related='close_id.company_id',
        store=True
    )
    closing_balance = fields.Monetary(
        string='Saldo de Cierre',
        currency_field='currency_id',
        help='Saldo de la cuenta bancaria al momento del cierre'
    )
    notes = fields.Char(
        string='Notas'
    )
