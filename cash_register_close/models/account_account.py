# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import timedelta


class AccountAccount(models.Model):
    _inherit = 'account.account'

    is_cash_account = fields.Boolean(
        string='Cuenta de Efectivo',
        default=False,
        help='Marcar si esta cuenta es una cuenta de efectivo para el cierre de caja'
    )
    is_bank_account = fields.Boolean(
        string='Cuenta Bancaria',
        default=False,
        help='Marcar si esta cuenta es una cuenta bancaria para el cierre de caja'
    )
    cash_close_currency_id = fields.Many2one(
        'res.currency',
        string='Moneda Cierre de Caja',
        help='Moneda específica para el cierre de caja. Si es USD, se usarán los campos debit_usd/credit_usd del módulo account_dual_currency. Este campo es independiente de la moneda contable nativa de Odoo.'
    )
    
    def _is_usd_account(self):
        """Verifica si la cuenta está configurada en USD para el cierre de caja"""
        self.ensure_one()
        # Usar específicamente el campo de moneda de cierre, NO el currency_id nativo
        currency = self.cash_close_currency_id
        return currency and currency.name == 'USD'
    
    def get_cash_balance(self, date_from=None, date_to=None):
        """Obtiene el balance de la cuenta de efectivo para un rango de fechas"""
        self.ensure_one()
        domain = [
            ('account_id', '=', self.id),
            ('parent_state', '=', 'posted'),
        ]
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        
        move_lines = self.env['account.move.line'].search(domain)
        balance = sum(move_lines.mapped('balance'))
        return balance
    
    def get_cash_balances_dual_currency(self, date):
        """
        Obtiene los saldos de la cuenta en múltiples monedas (Bs, USD, EUR).
        
        Para cuentas en USD: usa debit_usd/credit_usd del módulo account_dual_currency
        Para cuentas en EUR: usa debit_usd/credit_usd del módulo account_dual_currency (mismos campos que USD)
        Para cuentas en Bs: usa debit/credit estándar
        
        Returns:
            dict: Diccionario con todos los saldos:
                - initial_bs: Saldo inicial en Bs
                - income_bs: Ingresos del día en Bs
                - expense_bs: Egresos del día en Bs
                - balance_bs: Saldo final en Bs
                - initial_usd: Saldo inicial en USD
                - income_usd: Ingresos del día en USD
                - expense_usd: Egresos del día en USD
                - balance_usd: Saldo final en USD
                - initial_eur: Saldo inicial en EUR
                - income_eur: Ingresos del día en EUR
                - expense_eur: Egresos del día en EUR
                - balance_eur: Saldo final en EUR
        """
        self.ensure_one()
        
        # Detectar tipo de moneda de la cuenta
        currency_name = self.cash_close_currency_id.name if self.cash_close_currency_id else ''
        is_usd = currency_name == 'USD'
        is_eur = currency_name == 'EUR'
        
        date_before = date - timedelta(days=1)
        
        # Dominio para movimientos anteriores (saldo inicial)
        domain_initial = [
            ('account_id', '=', self.id),
            ('parent_state', '=', 'posted'),
            ('date', '<=', date_before),
        ]
        
        # Dominio para movimientos del día
        domain_day = [
            ('account_id', '=', self.id),
            ('parent_state', '=', 'posted'),
            ('date', '=', date),
        ]
        
        # Obtener movimientos
        initial_moves = self.env['account.move.line'].search(domain_initial)
        day_moves = self.env['account.move.line'].search(domain_day)
        
        result = {
            'initial_bs': 0,
            'income_bs': 0,
            'expense_bs': 0,
            'balance_bs': 0,
            'initial_usd': 0,
            'income_usd': 0,
            'expense_usd': 0,
            'balance_usd': 0,
            'initial_eur': 0,
            'income_eur': 0,
            'expense_eur': 0,
            'balance_eur': 0,
        }
        
        # Verificar si los campos USD existen (módulo account_dual_currency instalado)
        # Nota: EUR usa los mismos campos debit_usd/credit_usd
        has_usd_fields = hasattr(self.env['account.move.line'], 'debit_usd')
        
        if is_usd and has_usd_fields:
            # Cuenta en USD: usar campos debit_usd/credit_usd
            # Saldo inicial USD
            for move in initial_moves:
                result['initial_usd'] += getattr(move, 'debit_usd', 0) or 0
                result['initial_usd'] -= getattr(move, 'credit_usd', 0) or 0
            
            # Movimientos del día USD
            for move in day_moves:
                debit_usd = getattr(move, 'debit_usd', 0) or 0
                credit_usd = getattr(move, 'credit_usd', 0) or 0
                
                if debit_usd > 0:
                    result['income_usd'] += debit_usd
                if credit_usd > 0:
                    result['expense_usd'] += credit_usd
            
            # Balance USD
            result['balance_usd'] = result['initial_usd'] + result['income_usd'] - result['expense_usd']
            
            # También calculamos los valores en Bs para referencia
            result['initial_bs'] = sum(initial_moves.mapped('balance'))
            result['income_bs'] = sum(day_moves.filtered(lambda m: m.debit > 0).mapped('debit'))
            result['expense_bs'] = sum(day_moves.filtered(lambda m: m.credit > 0).mapped('credit'))
            result['balance_bs'] = result['initial_bs'] + result['income_bs'] - result['expense_bs']
        
        elif is_eur and has_usd_fields:
            # Cuenta en EUR: usar debit_usd/credit_usd igual que USD
            # Saldo inicial EUR
            for move in initial_moves:
                result['initial_eur'] += getattr(move, 'debit_usd', 0) or 0
                result['initial_eur'] -= getattr(move, 'credit_usd', 0) or 0
            
            # Movimientos del día EUR
            for move in day_moves:
                debit_usd = getattr(move, 'debit_usd', 0) or 0
                credit_usd = getattr(move, 'credit_usd', 0) or 0
                
                if debit_usd > 0:
                    result['income_eur'] += debit_usd
                if credit_usd > 0:
                    result['expense_eur'] += credit_usd
            
            # Balance EUR
            result['balance_eur'] = result['initial_eur'] + result['income_eur'] - result['expense_eur']
            
            # También calculamos los valores en Bs para referencia
            result['initial_bs'] = sum(initial_moves.mapped('balance'))
            result['income_bs'] = sum(day_moves.filtered(lambda m: m.debit > 0).mapped('debit'))
            result['expense_bs'] = sum(day_moves.filtered(lambda m: m.credit > 0).mapped('credit'))
            result['balance_bs'] = result['initial_bs'] + result['income_bs'] - result['expense_bs']
        
        else:
            # Cuenta en Bs: usar campos debit/credit estándar
            # Saldo inicial Bs
            result['initial_bs'] = sum(initial_moves.mapped('balance'))
            
            # Movimientos del día Bs
            for move in day_moves:
                if move.debit > 0:
                    result['income_bs'] += move.debit
                if move.credit > 0:
                    result['expense_bs'] += move.credit
            
            # Balance Bs
            result['balance_bs'] = result['initial_bs'] + result['income_bs'] - result['expense_bs']
            
            # Si hay campos USD, también obtener los valores USD para referencia
            if has_usd_fields:
                for move in initial_moves:
                    result['initial_usd'] += getattr(move, 'debit_usd', 0) or 0
                    result['initial_usd'] -= getattr(move, 'credit_usd', 0) or 0
                
                for move in day_moves:
                    debit_usd = getattr(move, 'debit_usd', 0) or 0
                    credit_usd = getattr(move, 'credit_usd', 0) or 0
                    
                    if debit_usd > 0:
                        result['income_usd'] += debit_usd
                    if credit_usd > 0:
                        result['expense_usd'] += credit_usd
                
                result['balance_usd'] = result['initial_usd'] + result['income_usd'] - result['expense_usd']
                
                # EUR usa los mismos campos que USD (debit_usd/credit_usd)
                # Los valores EUR son los mismos que USD para referencia
                result['initial_eur'] = result['initial_usd']
                result['income_eur'] = result['income_usd']
                result['expense_eur'] = result['expense_usd']
                result['balance_eur'] = result['balance_usd']
        
        return result
    
    def get_day_movements(self, date):
        """Obtiene los movimientos del día para esta cuenta"""
        self.ensure_one()
        domain = [
            ('account_id', '=', self.id),
            ('date', '=', date),
            ('parent_state', '=', 'posted'),
        ]
        return self.env['account.move.line'].search(domain, order='date, id')
    
    def get_initial_balance(self, date):
        """Obtiene el saldo inicial del día (balance hasta el día anterior)"""
        self.ensure_one()
        date_before = date - timedelta(days=1)
        return self.get_cash_balance(date_to=date_before)
    
    def get_day_income(self, date):
        """Obtiene el total de ingresos del día"""
        self.ensure_one()
        domain = [
            ('account_id', '=', self.id),
            ('date', '=', date),
            ('parent_state', '=', 'posted'),
            ('debit', '>', 0),
        ]
        move_lines = self.env['account.move.line'].search(domain)
        return sum(move_lines.mapped('debit'))
    
    def get_day_expense(self, date):
        """Obtiene el total de egresos del día"""
        self.ensure_one()
        domain = [
            ('account_id', '=', self.id),
            ('date', '=', date),
            ('parent_state', '=', 'posted'),
            ('credit', '>', 0),
        ]
        move_lines = self.env['account.move.line'].search(domain)
        return sum(move_lines.mapped('credit'))


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    def action_open_move(self):
        """Abre el asiento contable completo de esta línea"""
        self.ensure_one()
        return {
            'name': self.move_id.name or 'Asiento Contable',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
