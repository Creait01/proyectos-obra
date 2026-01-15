# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


class CashRegisterConsolidated(models.Model):
    """Modelo para el Dashboard Consolidado Multi-Empresa - Por Cierre"""
    _name = 'cash.register.consolidated'
    _description = 'Dashboard Consolidado de Cierres de Caja'
    _auto = False  # Es una vista SQL, no crea tabla
    _order = 'date desc, company_id'

    # Campos de identificación
    date = fields.Date(string='Fecha', readonly=True)
    company_id = fields.Many2one('res.company', string='Empresa', readonly=True)
    close_id = fields.Many2one('cash.register.close', string='Cierre', readonly=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('in_progress', 'En Proceso'),
        ('closed', 'Cerrado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', readonly=True)
    
    # Totales Bolívares
    total_initial_balance_bs = fields.Float(string='Saldo Inicial Bs', readonly=True)
    total_income_bs = fields.Float(string='Ingresos Bs', readonly=True)
    total_expense_bs = fields.Float(string='Egresos Bs', readonly=True)
    total_final_balance_bs = fields.Float(string='Saldo Final Bs', readonly=True)
    total_counted_bs = fields.Float(string='Contado Bs', readonly=True)
    total_difference_bs = fields.Float(string='Diferencia Bs', readonly=True)
    
    # Totales USD
    total_initial_balance_usd = fields.Float(string='Saldo Inicial USD', readonly=True)
    total_income_usd = fields.Float(string='Ingresos USD', readonly=True)
    total_expense_usd = fields.Float(string='Egresos USD', readonly=True)
    total_final_balance_usd = fields.Float(string='Saldo Final USD', readonly=True)
    total_counted_usd = fields.Float(string='Contado USD', readonly=True)
    total_difference_usd = fields.Float(string='Diferencia USD', readonly=True)
    
    # Totales EUR
    total_initial_balance_eur = fields.Float(string='Saldo Inicial EUR', readonly=True)
    total_income_eur = fields.Float(string='Ingresos EUR', readonly=True)
    total_expense_eur = fields.Float(string='Egresos EUR', readonly=True)
    total_final_balance_eur = fields.Float(string='Saldo Final EUR', readonly=True)
    total_counted_eur = fields.Float(string='Contado EUR', readonly=True)
    total_difference_eur = fields.Float(string='Diferencia EUR', readonly=True)
    
    # Contadores
    accounts_count = fields.Integer(string='Total Cuentas', readonly=True)
    accounts_bs_count = fields.Integer(string='Cuentas Bs', readonly=True)
    accounts_usd_count = fields.Integer(string='Cuentas USD', readonly=True)
    accounts_eur_count = fields.Integer(string='Cuentas EUR', readonly=True)

    def init(self):
        """Crea la vista SQL para el dashboard consolidado"""
        self.env.cr.execute("""
            DROP VIEW IF EXISTS cash_register_consolidated;
            CREATE OR REPLACE VIEW cash_register_consolidated AS (
                SELECT
                    c.id as id,
                    c.id as close_id,
                    c.date,
                    c.company_id,
                    c.state,
                    COALESCE(c.total_initial_balance_bs, 0) as total_initial_balance_bs,
                    COALESCE(c.total_income_bs, 0) as total_income_bs,
                    COALESCE(c.total_expense_bs, 0) as total_expense_bs,
                    COALESCE(c.total_final_balance_bs, 0) as total_final_balance_bs,
                    COALESCE(c.total_counted_bs, 0) as total_counted_bs,
                    COALESCE(c.total_difference_bs, 0) as total_difference_bs,
                    COALESCE(c.total_initial_balance_usd, 0) as total_initial_balance_usd,
                    COALESCE(c.total_income_usd, 0) as total_income_usd,
                    COALESCE(c.total_expense_usd, 0) as total_expense_usd,
                    COALESCE(c.total_final_balance_usd, 0) as total_final_balance_usd,
                    COALESCE(c.total_counted_usd, 0) as total_counted_usd,
                    COALESCE(c.total_difference_usd, 0) as total_difference_usd,
                    COALESCE(c.total_initial_balance_eur, 0) as total_initial_balance_eur,
                    COALESCE(c.total_income_eur, 0) as total_income_eur,
                    COALESCE(c.total_expense_eur, 0) as total_expense_eur,
                    COALESCE(c.total_final_balance_eur, 0) as total_final_balance_eur,
                    COALESCE(c.total_counted_eur, 0) as total_counted_eur,
                    COALESCE(c.total_difference_eur, 0) as total_difference_eur,
                    (SELECT COUNT(*) FROM cash_register_close_line l WHERE l.close_id = c.id) as accounts_count,
                    (SELECT COUNT(*) FROM cash_register_close_line l WHERE l.close_id = c.id AND l.is_usd_account = false AND l.is_eur_account = false) as accounts_bs_count,
                    (SELECT COUNT(*) FROM cash_register_close_line l WHERE l.close_id = c.id AND l.is_usd_account = true) as accounts_usd_count,
                    (SELECT COUNT(*) FROM cash_register_close_line l WHERE l.close_id = c.id AND l.is_eur_account = true) as accounts_eur_count
                FROM cash_register_close c
                WHERE c.state != 'cancelled'
            )
        """)

    def action_open_close(self):
        """Abrir el cierre de caja relacionado"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cierre de Caja'),
            'res_model': 'cash.register.close',
            'res_id': self.close_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class CashRegisterConsolidatedLine(models.Model):
    """Vista consolidada de líneas de cierre - Detalle por cuenta y empresa"""
    _name = 'cash.register.consolidated.line'
    _description = 'Líneas Consolidadas de Cierre de Caja'
    _auto = False
    _order = 'date desc, company_id, account_code'

    # Identificación
    date = fields.Date(string='Fecha', readonly=True)
    company_id = fields.Many2one('res.company', string='Empresa', readonly=True)
    close_id = fields.Many2one('cash.register.close', string='Cierre', readonly=True)
    line_id = fields.Many2one('cash.register.close.line', string='Línea', readonly=True)
    account_id = fields.Many2one('account.account', string='Cuenta', readonly=True)
    account_code = fields.Char(string='Código', readonly=True)
    account_name = fields.Char(string='Nombre Cuenta', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', readonly=True)
    currency_name = fields.Char(string='Moneda', readonly=True)
    
    # Tipo de cuenta
    is_usd_account = fields.Boolean(string='Es USD', readonly=True)
    is_eur_account = fields.Boolean(string='Es EUR', readonly=True)
    
    # Montos
    initial_balance = fields.Float(string='Saldo Inicial', readonly=True)
    total_income = fields.Float(string='Ingresos', readonly=True)
    total_expense = fields.Float(string='Egresos', readonly=True)
    final_balance = fields.Float(string='Saldo Final', readonly=True)
    counted_amount = fields.Float(string='Contado', readonly=True)
    difference = fields.Float(string='Diferencia', readonly=True)
    
    # Estado
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('in_progress', 'En Proceso'),
        ('closed', 'Cerrado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', readonly=True)
    is_counted = fields.Boolean(string='Contado', readonly=True)

    def init(self):
        """Crea la vista SQL para las líneas consolidadas"""
        self.env.cr.execute("""
            DROP VIEW IF EXISTS cash_register_consolidated_line;
            CREATE OR REPLACE VIEW cash_register_consolidated_line AS (
                SELECT
                    l.id as id,
                    l.id as line_id,
                    c.date,
                    c.company_id,
                    c.id as close_id,
                    l.account_id,
                    a.code as account_code,
                    a.name as account_name,
                    l.currency_id,
                    cur.name as currency_name,
                    l.is_usd_account,
                    l.is_eur_account,
                    COALESCE(l.initial_balance, 0) as initial_balance,
                    COALESCE(l.total_income, 0) as total_income,
                    COALESCE(l.total_expense, 0) as total_expense,
                    COALESCE(l.final_balance, 0) as final_balance,
                    COALESCE(l.counted_amount, 0) as counted_amount,
                    COALESCE(l.difference, 0) as difference,
                    c.state,
                    l.is_counted
                FROM cash_register_close_line l
                JOIN cash_register_close c ON l.close_id = c.id
                JOIN account_account a ON l.account_id = a.id
                LEFT JOIN res_currency cur ON l.currency_id = cur.id
                WHERE c.state != 'cancelled'
            )
        """)

    def action_open_line(self):
        """Abrir la línea de cierre"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Línea de Cierre'),
            'res_model': 'cash.register.close.line',
            'res_id': self.line_id.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_open_close(self):
        """Abrir el cierre de caja"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cierre de Caja'),
            'res_model': 'cash.register.close',
            'res_id': self.close_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class CashRegisterExecutiveDashboard(models.TransientModel):
    """Dashboard Ejecutivo para Directivos - Vista consolidada visual"""
    _name = 'cash.register.executive.dashboard'
    _description = 'Dashboard Ejecutivo de Caja'

    # Filtros
    date_from = fields.Date(
        string='Desde',
        default=lambda self: fields.Date.today().replace(day=1)
    )
    date_to = fields.Date(
        string='Hasta',
        default=fields.Date.today
    )
    company_ids = fields.Many2many(
        'res.company',
        string='Empresas',
        default=lambda self: self.env['res.company'].search([])
    )

    # Totales Generales Bs
    total_income_bs = fields.Float(string='Total Ingresos Bs', compute='_compute_totals')
    total_expense_bs = fields.Float(string='Total Egresos Bs', compute='_compute_totals')
    total_balance_bs = fields.Float(string='Saldo Neto Bs', compute='_compute_totals')
    total_difference_bs = fields.Float(string='Diferencia Bs', compute='_compute_totals')
    
    # Totales Generales USD
    total_income_usd = fields.Float(string='Total Ingresos USD', compute='_compute_totals')
    total_expense_usd = fields.Float(string='Total Egresos USD', compute='_compute_totals')
    total_balance_usd = fields.Float(string='Saldo Neto USD', compute='_compute_totals')
    total_difference_usd = fields.Float(string='Diferencia USD', compute='_compute_totals')
    
    # Totales Generales EUR
    total_income_eur = fields.Float(string='Total Ingresos EUR', compute='_compute_totals')
    total_expense_eur = fields.Float(string='Total Egresos EUR', compute='_compute_totals')
    total_balance_eur = fields.Float(string='Saldo Neto EUR', compute='_compute_totals')
    total_difference_eur = fields.Float(string='Diferencia EUR', compute='_compute_totals')
    
    # Estadísticas
    total_closes = fields.Integer(string='Total Cierres', compute='_compute_totals')
    closed_count = fields.Integer(string='Cerrados', compute='_compute_totals')
    pending_count = fields.Integer(string='Pendientes', compute='_compute_totals')
    companies_count = fields.Integer(string='Empresas', compute='_compute_totals')
    
    # Indicadores
    income_vs_expense_bs = fields.Float(string='Ratio Ingreso/Egreso Bs', compute='_compute_totals')
    income_vs_expense_usd = fields.Float(string='Ratio Ingreso/Egreso USD', compute='_compute_totals')
    has_differences = fields.Boolean(string='Tiene Diferencias', compute='_compute_totals')
    
    # HTML para el resumen
    summary_html = fields.Html(string='Resumen', compute='_compute_summary_html', sanitize=False)
    companies_summary_html = fields.Html(string='Por Empresa', compute='_compute_companies_summary', sanitize=False)

    @api.depends('date_from', 'date_to', 'company_ids')
    def _compute_totals(self):
        for record in self:
            domain = [('state', '!=', 'cancelled')]
            if record.date_from:
                domain.append(('date', '>=', record.date_from))
            if record.date_to:
                domain.append(('date', '<=', record.date_to))
            if record.company_ids:
                domain.append(('company_id', 'in', record.company_ids.ids))
            
            closes = self.env['cash.register.close'].search(domain)
            
            # Totales Bs
            record.total_income_bs = sum(closes.mapped('total_income_bs'))
            record.total_expense_bs = sum(closes.mapped('total_expense_bs'))
            record.total_balance_bs = sum(closes.mapped('total_final_balance_bs'))
            record.total_difference_bs = sum(closes.mapped('total_difference_bs'))
            
            # Totales USD
            record.total_income_usd = sum(closes.mapped('total_income_usd'))
            record.total_expense_usd = sum(closes.mapped('total_expense_usd'))
            record.total_balance_usd = sum(closes.mapped('total_final_balance_usd'))
            record.total_difference_usd = sum(closes.mapped('total_difference_usd'))
            
            # Totales EUR
            record.total_income_eur = sum(closes.mapped('total_income_eur'))
            record.total_expense_eur = sum(closes.mapped('total_expense_eur'))
            record.total_balance_eur = sum(closes.mapped('total_final_balance_eur'))
            record.total_difference_eur = sum(closes.mapped('total_difference_eur'))
            
            # Estadísticas
            record.total_closes = len(closes)
            record.closed_count = len(closes.filtered(lambda c: c.state == 'closed'))
            record.pending_count = len(closes.filtered(lambda c: c.state in ('draft', 'in_progress')))
            record.companies_count = len(closes.mapped('company_id'))
            
            # Indicadores
            record.income_vs_expense_bs = (record.total_income_bs / record.total_expense_bs * 100) if record.total_expense_bs else 0
            record.income_vs_expense_usd = (record.total_income_usd / record.total_expense_usd * 100) if record.total_expense_usd else 0
            record.has_differences = record.total_difference_bs != 0 or record.total_difference_usd != 0

    @api.depends('date_from', 'date_to', 'company_ids')
    def _compute_summary_html(self):
        for record in self:
            html = """
            <div class="executive-dashboard">
                <!-- Resumen General -->
                <div class="row mb-4">
                    <div class="col-12">
                        <div class="d-flex justify-content-between align-items-center p-3" 
                             style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; color: white;">
                            <div>
                                <h4 class="mb-0">📊 Resumen Ejecutivo</h4>
                                <small>%s al %s</small>
                            </div>
                            <div class="text-end">
                                <h5 class="mb-0">%d Cierres</h5>
                                <small>%d empresas</small>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Tarjetas de Bolívares -->
                <div class="row mb-3">
                    <div class="col-12 mb-2">
                        <h5 style="color: #495057; border-bottom: 2px solid #667eea; padding-bottom: 5px;">
                            🇻🇪 BOLÍVARES (Bs)
                        </h5>
                    </div>
                    <div class="col-md-3 col-6 mb-3">
                        <div class="card h-100" style="border: none; border-radius: 15px; background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white;">
                            <div class="card-body text-center py-4">
                                <i class="fa fa-arrow-down fa-2x mb-2" style="opacity: 0.8;"></i>
                                <h3 class="mb-1">%s</h3>
                                <small style="opacity: 0.9;">INGRESOS</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 col-6 mb-3">
                        <div class="card h-100" style="border: none; border-radius: 15px; background: linear-gradient(135deg, #dc3545 0%, #e74c3c 100%); color: white;">
                            <div class="card-body text-center py-4">
                                <i class="fa fa-arrow-up fa-2x mb-2" style="opacity: 0.8;"></i>
                                <h3 class="mb-1">%s</h3>
                                <small style="opacity: 0.9;">EGRESOS</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 col-6 mb-3">
                        <div class="card h-100" style="border: none; border-radius: 15px; background: linear-gradient(135deg, #17a2b8 0%, #3498db 100%); color: white;">
                            <div class="card-body text-center py-4">
                                <i class="fa fa-balance-scale fa-2x mb-2" style="opacity: 0.8;"></i>
                                <h3 class="mb-1">%s</h3>
                                <small style="opacity: 0.9;">SALDO FINAL</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 col-6 mb-3">
                        <div class="card h-100" style="border: none; border-radius: 15px; background: %s; color: white;">
                            <div class="card-body text-center py-4">
                                <i class="fa fa-exclamation-triangle fa-2x mb-2" style="opacity: 0.8;"></i>
                                <h3 class="mb-1">%s</h3>
                                <small style="opacity: 0.9;">DIFERENCIA</small>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Tarjetas de USD -->
                <div class="row mb-3">
                    <div class="col-12 mb-2">
                        <h5 style="color: #495057; border-bottom: 2px solid #28a745; padding-bottom: 5px;">
                            💵 DÓLARES (USD)
                        </h5>
                    </div>
                    <div class="col-md-3 col-6 mb-3">
                        <div class="card h-100" style="border: none; border-radius: 15px; background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white;">
                            <div class="card-body text-center py-4">
                                <i class="fa fa-arrow-down fa-2x mb-2" style="opacity: 0.8;"></i>
                                <h3 class="mb-1">$ %s</h3>
                                <small style="opacity: 0.9;">INGRESOS</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 col-6 mb-3">
                        <div class="card h-100" style="border: none; border-radius: 15px; background: linear-gradient(135deg, #dc3545 0%, #e74c3c 100%); color: white;">
                            <div class="card-body text-center py-4">
                                <i class="fa fa-arrow-up fa-2x mb-2" style="opacity: 0.8;"></i>
                                <h3 class="mb-1">$ %s</h3>
                                <small style="opacity: 0.9;">EGRESOS</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 col-6 mb-3">
                        <div class="card h-100" style="border: none; border-radius: 15px; background: linear-gradient(135deg, #17a2b8 0%, #3498db 100%); color: white;">
                            <div class="card-body text-center py-4">
                                <i class="fa fa-balance-scale fa-2x mb-2" style="opacity: 0.8;"></i>
                                <h3 class="mb-1">$ %s</h3>
                                <small style="opacity: 0.9;">SALDO FINAL</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 col-6 mb-3">
                        <div class="card h-100" style="border: none; border-radius: 15px; background: %s; color: white;">
                            <div class="card-body text-center py-4">
                                <i class="fa fa-exclamation-triangle fa-2x mb-2" style="opacity: 0.8;"></i>
                                <h3 class="mb-1">$ %s</h3>
                                <small style="opacity: 0.9;">DIFERENCIA</small>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Indicadores de Estado -->
                <div class="row">
                    <div class="col-12 mb-2">
                        <h5 style="color: #495057; border-bottom: 2px solid #ffc107; padding-bottom: 5px;">
                            📈 INDICADORES
                        </h5>
                    </div>
                    <div class="col-md-4 col-6 mb-3">
                        <div class="card h-100" style="border: 2px solid #28a745; border-radius: 15px;">
                            <div class="card-body text-center py-3">
                                <i class="fa fa-check-circle fa-2x text-success mb-2"></i>
                                <h2 class="text-success mb-0">%d</h2>
                                <small class="text-muted">CERRADOS</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4 col-6 mb-3">
                        <div class="card h-100" style="border: 2px solid #ffc107; border-radius: 15px;">
                            <div class="card-body text-center py-3">
                                <i class="fa fa-clock-o fa-2x text-warning mb-2"></i>
                                <h2 class="text-warning mb-0">%d</h2>
                                <small class="text-muted">PENDIENTES</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4 col-12 mb-3">
                        <div class="card h-100" style="border: 2px solid %s; border-radius: 15px;">
                            <div class="card-body text-center py-3">
                                <i class="fa fa-%s fa-2x mb-2" style="color: %s;"></i>
                                <h2 class="mb-0" style="color: %s;">%s</h2>
                                <small class="text-muted">ESTADO GENERAL</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """ % (
                record.date_from.strftime('%d/%m/%Y') if record.date_from else '-',
                record.date_to.strftime('%d/%m/%Y') if record.date_to else '-',
                record.total_closes,
                record.companies_count,
                # Bs
                '{:,.2f}'.format(record.total_income_bs),
                '{:,.2f}'.format(record.total_expense_bs),
                '{:,.2f}'.format(record.total_balance_bs),
                'linear-gradient(135deg, #ffc107 0%, #ffca2c 100%)' if record.total_difference_bs != 0 else 'linear-gradient(135deg, #6c757d 0%, #495057 100%)',
                '{:,.2f}'.format(record.total_difference_bs),
                # USD
                '{:,.2f}'.format(record.total_income_usd),
                '{:,.2f}'.format(record.total_expense_usd),
                '{:,.2f}'.format(record.total_balance_usd),
                'linear-gradient(135deg, #ffc107 0%, #ffca2c 100%)' if record.total_difference_usd != 0 else 'linear-gradient(135deg, #6c757d 0%, #495057 100%)',
                '{:,.2f}'.format(record.total_difference_usd),
                # Indicadores
                record.closed_count,
                record.pending_count,
                '#28a745' if not record.has_differences else '#dc3545',
                'check' if not record.has_differences else 'warning',
                '#28a745' if not record.has_differences else '#dc3545',
                '#28a745' if not record.has_differences else '#dc3545',
                'OK' if not record.has_differences else 'REVISAR',
            )
            record.summary_html = html

    @api.depends('date_from', 'date_to', 'company_ids')
    def _compute_companies_summary(self):
        for record in self:
            domain = [('state', '!=', 'cancelled')]
            if record.date_from:
                domain.append(('date', '>=', record.date_from))
            if record.date_to:
                domain.append(('date', '<=', record.date_to))
            if record.company_ids:
                domain.append(('company_id', 'in', record.company_ids.ids))
            
            closes = self.env['cash.register.close'].search(domain)
            companies = closes.mapped('company_id')
            
            html = '<div class="companies-summary">'
            for company in companies:
                company_closes = closes.filtered(lambda c: c.company_id == company)
                income_bs = sum(company_closes.mapped('total_income_bs'))
                expense_bs = sum(company_closes.mapped('total_expense_bs'))
                income_usd = sum(company_closes.mapped('total_income_usd'))
                expense_usd = sum(company_closes.mapped('total_expense_usd'))
                diff_bs = sum(company_closes.mapped('total_difference_bs'))
                diff_usd = sum(company_closes.mapped('total_difference_usd'))
                
                status_color = '#28a745' if (diff_bs == 0 and diff_usd == 0) else '#dc3545'
                status_icon = 'check' if (diff_bs == 0 and diff_usd == 0) else 'exclamation'
                
                html += """
                <div class="card mb-2" style="border-radius: 12px; border-left: 4px solid %s;">
                    <div class="card-body py-2 px-3">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h6 class="mb-0">
                                    <i class="fa fa-%s-circle me-1" style="color: %s;"></i>
                                    %s
                                </h6>
                                <small class="text-muted">%d cierres</small>
                            </div>
                            <div class="text-end">
                                <div><small class="text-success">+Bs %s</small> / <small class="text-danger">-Bs %s</small></div>
                                <div><small class="text-success">+$ %s</small> / <small class="text-danger">-$ %s</small></div>
                            </div>
                        </div>
                    </div>
                </div>
                """ % (
                    status_color,
                    status_icon,
                    status_color,
                    company.name,
                    len(company_closes),
                    '{:,.2f}'.format(income_bs),
                    '{:,.2f}'.format(expense_bs),
                    '{:,.2f}'.format(income_usd),
                    '{:,.2f}'.format(expense_usd),
                )
            
            html += '</div>'
            record.companies_summary_html = html

    def action_refresh(self):
        """Refrescar el dashboard"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Dashboard Ejecutivo'),
            'res_model': 'cash.register.executive.dashboard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    def action_view_details(self):
        """Ver detalle en tabla"""
        domain = [('state', '!=', 'cancelled')]
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        if self.company_ids:
            domain.append(('company_id', 'in', self.company_ids.ids))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Detalle de Cierres'),
            'res_model': 'cash.register.consolidated',
            'view_mode': 'tree,pivot,graph',
            'domain': domain,
            'target': 'current',
        }

    def action_view_closes(self):
        """Ver cierres originales"""
        domain = [('state', '!=', 'cancelled')]
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        if self.company_ids:
            domain.append(('company_id', 'in', self.company_ids.ids))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cierres de Caja'),
            'res_model': 'cash.register.close',
            'view_mode': 'tree,form',
            'domain': domain,
            'target': 'current',
        }

    @api.model
    def action_open_dashboard(self):
        """Abrir el dashboard creando un nuevo registro"""
        dashboard = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'name': _('Dashboard Ejecutivo'),
            'res_model': 'cash.register.executive.dashboard',
            'view_mode': 'form',
            'res_id': dashboard.id,
            'target': 'current',
            'flags': {'mode': 'readonly'},
        }

    @api.model
    def get_dashboard_data(self, period='month', month=None, year=None):
        """
        Obtener datos para el dashboard ejecutivo con Chart.js
        Retorna un diccionario con todos los KPIs y datos para gráficos
        Incluye saldos en tiempo real de las cuentas de efectivo
        """
        today = date.today()
        if month is None:
            month = today.month - 1  # JavaScript months are 0-indexed
        if year is None:
            year = today.year
        
        # Adjust month (JavaScript sends 0-11, Python uses 1-12)
        month = month + 1
        
        # Calculate date range based on period
        if period == 'month':
            date_from = date(year, month, 1)
            if month == 12:
                date_to = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                date_to = date(year, month + 1, 1) - timedelta(days=1)
        elif period == 'quarter':
            quarter = (month - 1) // 3
            date_from = date(year, quarter * 3 + 1, 1)
            end_month = quarter * 3 + 3
            if end_month == 12:
                date_to = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                date_to = date(year, end_month + 1, 1) - timedelta(days=1)
        else:  # year
            date_from = date(year, 1, 1)
            date_to = date(year, 12, 31)
        
        # =====================================================
        # CALCULAR KPIs DIRECTAMENTE DE APUNTES CONTABLES
        # =====================================================
        period_data = self._get_period_movements(date_from, date_to)
        
        company_id = self.env.company.id
        
        # Get closes count for stats (filtered by current company)
        CloseModel = self.env['cash.register.close']
        closes = CloseModel.search([
            ('state', '!=', 'cancelled'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', company_id),
        ])
        
        total_closes = len(closes)
        closed_count = len(closes.filtered(lambda c: c.state in ['closed', 'confirmed']))
        confirmed_count = len(closes.filtered(lambda c: c.state == 'confirmed'))
        pending_count = len(closes.filtered(lambda c: c.state in ['draft', 'in_progress']))
        companies_count = 1  # Current company only
        
        # =====================================================
        # SALDOS EN TIEMPO REAL - Directamente de las cuentas
        # =====================================================
        realtime_data = self._get_realtime_cash_balances()
        
        # Movimientos de HOY
        today_data = self._get_today_movements()
        
        # Monthly data for bar chart (last 12 months) - DESDE MOVIMIENTOS CONTABLES
        monthly_data = self._get_monthly_cash_movements()
        
        # Company data for pie charts - DESDE MOVIMIENTOS CONTABLES EN TIEMPO REAL
        company_data = self._get_company_cash_distribution()
        
        # Billetes en mal estado
        bad_bills_data = self._get_bad_bills_summary()
        
        # Denominaciones actuales
        denominations_data = self._get_current_denominations()
        
        return {
            # KPIs del período (DESDE APUNTES CONTABLES)
            'totalIncomeBs': period_data.get('income_bs', 0),
            'totalExpenseBs': period_data.get('expense_bs', 0),
            'totalBalanceBs': period_data.get('balance_bs', 0),
            'totalIncomeUsd': period_data.get('income_usd', 0),
            'totalExpenseUsd': period_data.get('expense_usd', 0),
            'totalBalanceUsd': period_data.get('balance_usd', 0),
            'totalIncomeEur': period_data.get('income_eur', 0),
            'totalExpenseEur': period_data.get('expense_eur', 0),
            'totalBalanceEur': period_data.get('balance_eur', 0),
            'totalCloses': total_closes,
            'closedCount': closed_count,
            'confirmedCount': confirmed_count,
            'pendingCount': pending_count,
            'companiesCount': companies_count,
            'monthlyData': monthly_data,
            'companyData': company_data,
            # TIEMPO REAL - Saldos actuales
            'realtimeBalanceUsd': realtime_data.get('balance_usd', 0),
            'realtimeBalanceEur': realtime_data.get('balance_eur', 0),
            'realtimeBalanceBs': realtime_data.get('balance_bs', 0),
            'realtimeAccountsUsd': realtime_data.get('accounts_usd', []),
            'realtimeAccountsEur': realtime_data.get('accounts_eur', []),
            'realtimeAccountsBs': realtime_data.get('accounts_bs', []),
            # HOY - Movimientos del día
            'todayIncomeUsd': today_data.get('income_usd', 0),
            'todayExpenseUsd': today_data.get('expense_usd', 0),
            'todayIncomeEur': today_data.get('income_eur', 0),
            'todayExpenseEur': today_data.get('expense_eur', 0),
            'todayIncomeBs': today_data.get('income_bs', 0),
            'todayExpenseBs': today_data.get('expense_bs', 0),
            'todayMovementsCount': today_data.get('movements_count', 0),
            # Datos del flujo por defecto (año)
            'flowData': monthly_data,
            # Billetes en mal estado
            'badBillsData': bad_bills_data,
            # Denominaciones actuales
            'denominationsData': denominations_data,
        }
    
    @api.model
    def get_diagnostic_info(self):
        """
        Método de diagnóstico para verificar la configuración del dashboard.
        Ejecutar desde Shell de Odoo:
        >>> self.env['cash.register.executive.dashboard'].get_diagnostic_info()
        """
        import logging
        _logger = logging.getLogger(__name__)
        
        result = {
            'cash_accounts_marked': [],
            'cash_accounts_from_closes': [],
            'cash_accounts_by_type': [],
            'total_cash_accounts': 0,
            'has_debit_usd_field': False,
            'has_debit_eur_field': False,
            'sample_movements': [],
            'closes_count': 0,
            'issues': [],
        }
        
        # 1. Verificar cuentas marcadas como efectivo
        marked_accounts = self.env['account.account'].sudo().search([
            ('is_cash_account', '=', True),
            ('deprecated', '=', False),
        ])
        result['cash_accounts_marked'] = [
            {'code': a.code, 'name': a.name, 'currency': self._get_account_currency(a)}
            for a in marked_accounts
        ]
        
        # 2. Verificar cuentas desde líneas de cierre
        close_lines = self.env['cash.register.close.line'].sudo().search([])
        accounts_from_closes = close_lines.mapped('account_id')
        result['cash_accounts_from_closes'] = [
            {'code': a.code, 'name': a.name, 'currency': self._get_account_currency(a)}
            for a in accounts_from_closes
        ]
        
        # 3. Verificar cuentas por tipo contable
        type_accounts = self.env['account.account'].sudo().search([
            ('account_type', '=', 'asset_cash'),
            ('deprecated', '=', False),
        ])
        result['cash_accounts_by_type'] = [
            {'code': a.code, 'name': a.name, 'currency': self._get_account_currency(a)}
            for a in type_accounts
        ]
        
        # 4. Total de cuentas encontradas con el helper
        all_accounts = self._get_cash_accounts()
        result['total_cash_accounts'] = len(all_accounts)
        
        # 5. Verificar campos dual currency
        result['has_debit_usd_field'] = hasattr(self.env['account.move.line'], 'debit_usd')
        result['has_debit_eur_field'] = hasattr(self.env['account.move.line'], 'debit_eur')
        
        # 6. Muestra de movimientos
        if all_accounts:
            sample_moves = self.env['account.move.line'].sudo().search([
                ('account_id', 'in', all_accounts.ids),
                ('parent_state', '=', 'posted'),
            ], limit=5, order='date desc')
            for m in sample_moves:
                move_data = {
                    'date': str(m.date),
                    'account': m.account_id.code,
                    'debit': m.debit,
                    'credit': m.credit,
                }
                if result['has_debit_usd_field']:
                    move_data['debit_usd'] = getattr(m, 'debit_usd', 0)
                    move_data['credit_usd'] = getattr(m, 'credit_usd', 0)
                result['sample_movements'].append(move_data)
        
        # 7. Contar cierres
        result['closes_count'] = self.env['cash.register.close'].sudo().search_count([
            ('state', '!=', 'cancelled')
        ])
        
        # 8. Detectar problemas
        if not result['cash_accounts_marked'] and not result['cash_accounts_from_closes'] and not result['cash_accounts_by_type']:
            result['issues'].append("No se encontraron cuentas de efectivo. Configure el campo 'is_cash_account' en las cuentas de efectivo o cree un cierre de caja.")
        
        if not result['has_debit_usd_field']:
            result['issues'].append("No se encontró el campo 'debit_usd'. El módulo account_dual_currency puede no estar instalado.")
        
        if all_accounts:
            usd_accounts = all_accounts.filtered(lambda a: self._get_account_currency(a) == 'USD')
            if not usd_accounts:
                result['issues'].append("No se detectaron cuentas en USD. Verifique que las cuentas tengan configurado 'cash_close_currency_id' o 'currency_id' en USD.")
        
        _logger.info("Dashboard Diagnostic: %s", result)
        return result

    @api.model
    def get_flow_data(self, period='year', currency='USD'):
        """
        Obtiene los datos del flujo de caja según el período y moneda seleccionados.
        - period: 'day' (por hora), 'month' (por día), 'year' (por mes)
        - currency: 'USD' o 'EUR'
        """
        today = date.today()
        company_id = self.env.company.id
        
        # Buscar cuentas de efectivo usando el helper
        cash_accounts = self._get_cash_accounts(company_id=company_id)
        
        account_ids = cash_accounts.filtered(
            lambda a: self._get_account_currency(a) == currency
        ).ids
        
        # Tanto USD como EUR usan los mismos campos debit_usd/credit_usd
        debit_field = 'debit_usd'
        credit_field = 'credit_usd'
        
        has_fields = hasattr(self.env['account.move.line'], debit_field)
        
        if period == 'day':
            return self._get_hourly_flow_data(account_ids, has_fields, debit_field, credit_field, company_id)
        elif period == 'month':
            return self._get_daily_flow_data(account_ids, has_fields, debit_field, credit_field, company_id)
        else:  # year
            return self._get_monthly_flow_data(account_ids, has_fields, debit_field, credit_field, company_id)
    
    @api.model
    def _get_hourly_flow_data(self, account_ids, has_fields, debit_field, credit_field, company_id=None):
        """Obtiene datos de flujo por hora del día actual"""
        from datetime import datetime
        today = date.today()
        if company_id is None:
            company_id = self.env.company.id
        result = []
        
        for hour in range(24):
            hour_label = f"{hour:02d}:00"
            income = 0
            expense = 0
            
            if account_ids and has_fields:
                # Buscar movimientos de esa hora
                domain = [
                    ('account_id', 'in', account_ids),
                    ('parent_state', '=', 'posted'),
                    ('date', '=', today),
                    ('company_id', '=', company_id),
                ]
                moves = self.env['account.move.line'].sudo().search(domain)
                
                for m in moves:
                    # Verificar la hora del movimiento
                    if m.create_date and m.create_date.hour == hour:
                        debit = getattr(m, debit_field, 0) or 0
                        credit = getattr(m, credit_field, 0) or 0
                        if debit > 0:
                            income += debit
                        if credit > 0:
                            expense += credit
            
            result.append({
                'label': hour_label,
                'income': round(income, 2),
                'expense': round(expense, 2),
            })
        
        return result
    
    @api.model
    def _get_daily_flow_data(self, account_ids, has_fields, debit_field, credit_field, company_id=None):
        """Obtiene datos de flujo por día del mes actual"""
        import calendar
        today = date.today()
        if company_id is None:
            company_id = self.env.company.id
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        result = []
        
        for day in range(1, days_in_month + 1):
            day_date = date(today.year, today.month, day)
            day_label = f"{day}"
            income = 0
            expense = 0
            
            if account_ids and has_fields:
                domain = [
                    ('account_id', 'in', account_ids),
                    ('parent_state', '=', 'posted'),
                    ('date', '=', day_date),
                    ('company_id', '=', company_id),
                ]
                moves = self.env['account.move.line'].sudo().search(domain)
                
                for m in moves:
                    debit = getattr(m, debit_field, 0) or 0
                    credit = getattr(m, credit_field, 0) or 0
                    if debit > 0:
                        income += debit
                    if credit > 0:
                        expense += credit
            
            result.append({
                'label': day_label,
                'income': round(income, 2),
                'expense': round(expense, 2),
            })
        
        return result
    
    @api.model
    def _get_monthly_flow_data(self, account_ids, has_fields, debit_field, credit_field, company_id=None):
        """Obtiene datos de flujo por mes de los últimos 12 meses"""
        today = date.today()
        if company_id is None:
            company_id = self.env.company.id
        months_es = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                     'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        result = []
        
        for i in range(11, -1, -1):
            m_date = today - relativedelta(months=i)
            m_start = date(m_date.year, m_date.month, 1)
            if m_date.month == 12:
                m_end = date(m_date.year + 1, 1, 1) - timedelta(days=1)
            else:
                m_end = date(m_date.year, m_date.month + 1, 1) - timedelta(days=1)
            
            income = 0
            expense = 0
            
            if account_ids and has_fields:
                domain = [
                    ('account_id', 'in', account_ids),
                    ('parent_state', '=', 'posted'),
                    ('date', '>=', m_start),
                    ('date', '<=', m_end),
                    ('company_id', '=', company_id),
                ]
                moves = self.env['account.move.line'].sudo().search(domain)
                
                for m in moves:
                    debit = getattr(m, debit_field, 0) or 0
                    credit = getattr(m, credit_field, 0) or 0
                    if debit > 0:
                        income += debit
                    if credit > 0:
                        expense += credit
            
            result.append({
                'label': months_es[m_date.month - 1],
                'income': round(income, 2),
                'expense': round(expense, 2),
            })
        
        return result
    
    @api.model
    def _get_cash_accounts(self, company_id=None):
        """
        Obtiene las cuentas de efectivo de la empresa actual.
        Busca en orden:
        1. Cuentas marcadas con is_cash_account=True
        2. Cuentas usadas en líneas de cierre existentes
        3. Cuentas de tipo 'asset_cash' (tipo contable de caja/efectivo)
        
        Args:
            company_id: ID de la empresa. Si es None, usa la empresa actual del usuario.
        """
        if company_id is None:
            company_id = self.env.company.id
        
        # Primero buscar cuentas marcadas como efectivo de la empresa actual
        cash_accounts = self.env['account.account'].sudo().search([
            ('is_cash_account', '=', True),
            ('deprecated', '=', False),
            ('company_id', '=', company_id),
        ])
        
        # Si no hay cuentas marcadas, buscar desde las líneas de cierre existentes
        if not cash_accounts:
            close_lines = self.env['cash.register.close.line'].sudo().search([
                ('close_id.company_id', '=', company_id)
            ])
            account_ids = close_lines.mapped('account_id').ids
            if account_ids:
                cash_accounts = self.env['account.account'].sudo().browse(account_ids)
        
        # Si aún no hay cuentas, buscar por tipo contable de efectivo (asset_cash)
        if not cash_accounts:
            cash_accounts = self.env['account.account'].sudo().search([
                ('account_type', '=', 'asset_cash'),
                ('deprecated', '=', False),
                ('company_id', '=', company_id),
            ])
        
        return cash_accounts
    
    @api.model
    def _get_account_currency(self, account):
        """
        Determina la moneda de una cuenta de efectivo.
        Busca en orden:
        1. cash_close_currency_id (moneda específica de cierre)
        2. currency_id (moneda de la cuenta)
        3. Detecta por código de cuenta si contiene 'USD' o 'EUR'
        """
        currency = account.cash_close_currency_id or account.currency_id
        if currency:
            return currency.name
        
        # Fallback: detectar por código o nombre de cuenta
        account_code = (account.code or '').upper()
        account_name = (account.name or '').upper()
        
        if 'USD' in account_code or 'USD' in account_name or 'DOLAR' in account_name:
            return 'USD'
        elif 'EUR' in account_code or 'EUR' in account_name or 'EURO' in account_name:
            return 'EUR'
        
        # Si no se detecta, asumir moneda local (Bs)
        return ''
    
    @api.model
    def _get_period_movements(self, date_from, date_to):
        """
        Obtiene los movimientos (ingresos/egresos) de un período específico
        de la empresa actual, directamente desde account.move.line
        """
        result = {
            'income_usd': 0,
            'expense_usd': 0,
            'balance_usd': 0,
            'income_eur': 0,
            'expense_eur': 0,
            'balance_eur': 0,
            'income_bs': 0,
            'expense_bs': 0,
            'balance_bs': 0,
        }
        
        company_id = self.env.company.id
        
        # Buscar cuentas de efectivo de la empresa actual
        cash_accounts = self._get_cash_accounts(company_id)
        
        if not cash_accounts:
            return result
        
        # Separar por moneda usando el helper
        usd_accounts = cash_accounts.filtered(
            lambda a: self._get_account_currency(a) == 'USD'
        )
        eur_accounts = cash_accounts.filtered(
            lambda a: self._get_account_currency(a) == 'EUR'
        )
        bs_accounts = cash_accounts.filtered(
            lambda a: self._get_account_currency(a) not in ('USD', 'EUR')
        )
        
        # Verificar campos disponibles
        has_usd_fields = hasattr(self.env['account.move.line'], 'debit_usd')
        
        # USD
        if usd_accounts and has_usd_fields:
            moves = self.env['account.move.line'].sudo().search([
                ('account_id', 'in', usd_accounts.ids),
                ('parent_state', '=', 'posted'),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('company_id', '=', company_id),
            ])
            for m in moves:
                debit = getattr(m, 'debit_usd', 0) or 0
                credit = getattr(m, 'credit_usd', 0) or 0
                if debit > 0:
                    result['income_usd'] += debit
                if credit > 0:
                    result['expense_usd'] += credit
            result['balance_usd'] = result['income_usd'] - result['expense_usd']
        
        # EUR - Usa los mismos campos debit_usd/credit_usd que USD
        if eur_accounts and has_usd_fields:
            moves = self.env['account.move.line'].sudo().search([
                ('account_id', 'in', eur_accounts.ids),
                ('parent_state', '=', 'posted'),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('company_id', '=', company_id),
            ])
            for m in moves:
                debit = getattr(m, 'debit_usd', 0) or 0
                credit = getattr(m, 'credit_usd', 0) or 0
                if debit > 0:
                    result['income_eur'] += debit
                if credit > 0:
                    result['expense_eur'] += credit
            result['balance_eur'] = result['income_eur'] - result['expense_eur']
        
        # Bs (moneda local)
        if bs_accounts:
            moves = self.env['account.move.line'].sudo().search([
                ('account_id', 'in', bs_accounts.ids),
                ('parent_state', '=', 'posted'),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('company_id', '=', company_id),
            ])
            for m in moves:
                if m.debit > 0:
                    result['income_bs'] += m.debit
                if m.credit > 0:
                    result['expense_bs'] += m.credit
            result['balance_bs'] = result['income_bs'] - result['expense_bs']
        
        # Redondear
        for key in result:
            result[key] = round(result[key], 2)
        
        return result
    
    @api.model
    def _get_realtime_cash_balances(self):
        """
        Obtiene los saldos actuales en TIEMPO REAL de las cuentas de efectivo
        de la empresa actual, directamente de los movimientos contables publicados
        """
        result = {
            'balance_usd': 0,
            'balance_eur': 0,
            'balance_bs': 0,
            'accounts_usd': [],
            'accounts_eur': [],
            'accounts_bs': [],
        }
        
        company_id = self.env.company.id
        
        # Usar el helper centralizado para obtener cuentas de efectivo de la empresa
        cash_accounts = self._get_cash_accounts(company_id)
        
        if not cash_accounts:
            return result
        
        has_usd_fields = hasattr(self.env['account.move.line'], 'debit_usd')
        
        for account in cash_accounts:
            # Usar el helper centralizado para determinar la moneda
            currency_name = self._get_account_currency(account)
            
            # Obtener todos los movimientos publicados de esta cuenta y empresa
            domain = [
                ('account_id', '=', account.id),
                ('parent_state', '=', 'posted'),
                ('company_id', '=', company_id),
            ]
            moves = self.env['account.move.line'].sudo().search(domain)
            
            if currency_name == 'USD' and has_usd_fields:
                # Calcular balance USD
                balance = sum(getattr(m, 'debit_usd', 0) or 0 for m in moves) - \
                          sum(getattr(m, 'credit_usd', 0) or 0 for m in moves)
                result['balance_usd'] += balance
                result['accounts_usd'].append({
                    'code': account.code,
                    'name': account.name,
                    'company': account.company_id.name,
                    'balance': round(balance, 2),
                })
            elif currency_name == 'EUR' and has_usd_fields:
                # Calcular balance EUR usando debit_usd/credit_usd (igual que USD)
                balance = sum(getattr(m, 'debit_usd', 0) or 0 for m in moves) - \
                          sum(getattr(m, 'credit_usd', 0) or 0 for m in moves)
                result['balance_eur'] += balance
                result['accounts_eur'].append({
                    'code': account.code,
                    'name': account.name,
                    'company': account.company_id.name,
                    'balance': round(balance, 2),
                })
            else:
                # Calcular balance Bs
                balance = sum(m.balance for m in moves)
                result['balance_bs'] += balance
                result['accounts_bs'].append({
                    'code': account.code,
                    'name': account.name,
                    'company': account.company_id.name,
                    'balance': balance,
                })
        
        return result
    
    @api.model
    def _get_today_movements(self):
        """
        Obtiene los movimientos de HOY de las cuentas de efectivo de la empresa actual
        """
        today = date.today()
        result = {
            'income_usd': 0,
            'expense_usd': 0,
            'income_eur': 0,
            'expense_eur': 0,
            'income_bs': 0,
            'expense_bs': 0,
            'movements_count': 0,
        }
        
        company_id = self.env.company.id
        
        # Buscar cuentas de efectivo de la empresa actual
        cash_accounts = self._get_cash_accounts(company_id)
        
        if not cash_accounts:
            return result
        
        has_usd_fields = hasattr(self.env['account.move.line'], 'debit_usd')
        
        for account in cash_accounts:
            currency_name = self._get_account_currency(account)
            
            # Movimientos de hoy de la empresa actual
            domain = [
                ('account_id', '=', account.id),
                ('parent_state', '=', 'posted'),
                ('date', '=', today),
                ('company_id', '=', company_id),
            ]
            moves = self.env['account.move.line'].sudo().search(domain)
            result['movements_count'] += len(moves)
            
            if currency_name == 'USD' and has_usd_fields:
                for m in moves:
                    debit = getattr(m, 'debit_usd', 0) or 0
                    credit = getattr(m, 'credit_usd', 0) or 0
                    if debit > 0:
                        result['income_usd'] += debit
                    if credit > 0:
                        result['expense_usd'] += credit
            elif currency_name == 'EUR' and has_usd_fields:
                # EUR usa los mismos campos debit_usd/credit_usd
                for m in moves:
                    debit = getattr(m, 'debit_usd', 0) or 0
                    credit = getattr(m, 'credit_usd', 0) or 0
                    if debit > 0:
                        result['income_eur'] += debit
                    if credit > 0:
                        result['expense_eur'] += credit
            else:
                for m in moves:
                    if m.debit > 0:
                        result['income_bs'] += m.debit
                    if m.credit > 0:
                        result['expense_bs'] += m.credit
        
        return result

    @api.model
    def _get_monthly_cash_movements(self):
        """
        Obtiene los movimientos de efectivo de los últimos 12 meses
        de la empresa actual, directamente de account.move.line (TIEMPO REAL)
        """
        today = date.today()
        months_es = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                     'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        monthly_data = []
        
        company_id = self.env.company.id
        
        # Buscar cuentas de efectivo de la empresa actual
        cash_accounts = self._get_cash_accounts(company_id)
        
        usd_account_ids = cash_accounts.filtered(
            lambda a: self._get_account_currency(a) == 'USD'
        ).ids
        
        has_usd_fields = hasattr(self.env['account.move.line'], 'debit_usd')
        
        for i in range(11, -1, -1):
            m_date = today - relativedelta(months=i)
            m_start = date(m_date.year, m_date.month, 1)
            if m_date.month == 12:
                m_end = date(m_date.year + 1, 1, 1) - timedelta(days=1)
            else:
                m_end = date(m_date.year, m_date.month + 1, 1) - timedelta(days=1)
            
            income = 0
            expense = 0
            
            if usd_account_ids and has_usd_fields:
                # Obtener movimientos del mes para cuentas USD de la empresa actual
                domain = [
                    ('account_id', 'in', usd_account_ids),
                    ('parent_state', '=', 'posted'),
                    ('date', '>=', m_start),
                    ('date', '<=', m_end),
                    ('company_id', '=', company_id),
                ]
                moves = self.env['account.move.line'].sudo().search(domain)
                
                for m in moves:
                    debit = getattr(m, 'debit_usd', 0) or 0
                    credit = getattr(m, 'credit_usd', 0) or 0
                    if debit > 0:
                        income += debit
                    if credit > 0:
                        expense += credit
            
            monthly_data.append({
                'month': months_es[m_date.month - 1],
                'income': income,
                'expense': expense,
            })
        
        return monthly_data

    @api.model
    def _get_company_cash_distribution(self):
        """
        Obtiene la distribución de ingresos/egresos de la empresa actual
        directamente de account.move.line (TIEMPO REAL)
        Considera el año actual completo
        """
        today = date.today()
        year_start = date(today.year, 1, 1)
        
        company_id = self.env.company.id
        
        # Buscar cuentas de efectivo de la empresa actual
        cash_accounts = self._get_cash_accounts(company_id)
        
        usd_accounts = cash_accounts.filtered(
            lambda a: self._get_account_currency(a) == 'USD'
        )
        
        has_usd_fields = hasattr(self.env['account.move.line'], 'debit_usd')
        company_data = {}
        
        if usd_accounts and has_usd_fields:
            for account in usd_accounts:
                company = account.company_id
                company_name = company.name[:20] if company else 'Sin Empresa'
                
                if company_name not in company_data:
                    company_data[company_name] = {'income': 0, 'expense': 0}
                
                # Movimientos del año para esta cuenta de la empresa actual
                domain = [
                    ('account_id', '=', account.id),
                    ('parent_state', '=', 'posted'),
                    ('date', '>=', year_start),
                    ('date', '<=', today),
                    ('company_id', '=', company_id),
                ]
                moves = self.env['account.move.line'].sudo().search(domain)
                
                for m in moves:
                    debit = getattr(m, 'debit_usd', 0) or 0
                    credit = getattr(m, 'credit_usd', 0) or 0
                    if debit > 0:
                        company_data[company_name]['income'] += debit
                    if credit > 0:
                        company_data[company_name]['expense'] += credit
        
        # Convertir a lista
        result = [
            {'name': name, 'income': data['income'], 'expense': data['expense']}
            for name, data in company_data.items()
            if data['income'] > 0 or data['expense'] > 0
        ]
        
        # Si no hay datos, agregar placeholder
        if not result:
            result = [{'name': 'Sin movimientos', 'income': 0, 'expense': 0}]
        
        return result

    @api.model
    def _get_bad_bills_summary(self):
        """
        Obtiene resumen de billetes en mal estado del mes actual
        Agrupa por condición y moneda
        """
        today = date.today()
        month_start = date(today.year, today.month, 1)
        company_id = self.env.company.id
        
        result = {
            'total_count': 0,
            'total_value_usd': 0,
            'total_value_eur': 0,
            'by_condition': [],
            'by_denomination': [],
        }
        
        # Buscar billetes malos del mes actual para la empresa actual
        bad_bills = self.env['cash.register.bad.bills'].sudo().search([
            ('close_line_id.close_id.date', '>=', month_start),
            ('close_line_id.close_id.date', '<=', today),
            ('close_line_id.close_id.company_id', '=', company_id),
            ('quantity', '>', 0),
        ])
        
        if not bad_bills:
            return result
        
        result['total_count'] = sum(bad_bills.mapped('quantity'))
        
        # Por condición
        condition_data = {}
        condition_labels = {
            'damaged': 'Dañado',
            'torn': 'Roto',
            'worn': 'Desgastado',
            'counterfeit': 'Sospecha Falsificación',
            'other': 'Otro',
        }
        
        for bill in bad_bills:
            cond = bill.condition or 'other'
            cond_label = condition_labels.get(cond, cond)
            
            if cond_label not in condition_data:
                condition_data[cond_label] = {'quantity': 0, 'value': 0}
            
            condition_data[cond_label]['quantity'] += bill.quantity
            condition_data[cond_label]['value'] += bill.total or 0
            
            # Sumar por moneda
            if bill.currency_id and bill.currency_id.name == 'USD':
                result['total_value_usd'] += bill.total or 0
            elif bill.currency_id and bill.currency_id.name == 'EUR':
                result['total_value_eur'] += bill.total or 0
        
        result['by_condition'] = [
            {'name': name, 'quantity': data['quantity'], 'value': round(data['value'], 2)}
            for name, data in condition_data.items()
        ]
        
        # Por denominación
        denom_data = {}
        for bill in bad_bills:
            denom_name = bill.denomination_id.name if bill.denomination_id else 'Desconocido'
            
            if denom_name not in denom_data:
                denom_data[denom_name] = 0
            denom_data[denom_name] += bill.quantity
        
        result['by_denomination'] = [
            {'name': name, 'quantity': qty}
            for name, qty in sorted(denom_data.items(), key=lambda x: x[1], reverse=True)
        ][:10]  # Top 10
        
        return result

    @api.model
    def _get_current_denominations(self):
        """
        Obtiene las denominaciones del ÚLTIMO cierre cerrado/confirmado
        Agrupa por moneda y tipo (billete/moneda)
        """
        company_id = self.env.company.id
        result = {
            'usd': [],
            'eur': [],
            'bs': [],
            'total_usd': 0,
            'total_eur': 0,
            'total_bs': 0,
            'close_date': '',
            'close_name': '',
        }
        
        # Buscar el último cierre cerrado o confirmado de la empresa actual
        last_close = self.env['cash.register.close'].sudo().search([
            ('state', 'in', ['closed', 'confirmed']),
            ('company_id', '=', company_id),
        ], order='date desc, id desc', limit=1)
        
        if not last_close:
            return result
        
        result['close_date'] = last_close.date.strftime('%d/%m/%Y') if last_close.date else ''
        result['close_name'] = last_close.name or ''
        
        # Agrupar denominaciones por valor y moneda para consolidar
        denom_usd = {}
        denom_eur = {}
        denom_bs = {}
        
        # Obtener líneas de denominación del último cierre
        for line in last_close.line_ids:
            for denom_line in line.denomination_line_ids:
                if denom_line.quantity <= 0:
                    continue
                
                currency_name = denom_line.currency_id.name if denom_line.currency_id else 'USD'
                denom_type = denom_line.denomination_id.denomination_type if denom_line.denomination_id else 'bill'
                denom_value = denom_line.denomination_id.value if denom_line.denomination_id else 0
                denom_name = denom_line.denomination_id.name if denom_line.denomination_id else 'Desconocido'
                
                # Agrupar por denominación
                if currency_name == 'USD':
                    if denom_name not in denom_usd:
                        denom_usd[denom_name] = {'value': denom_value, 'quantity': 0, 'total': 0, 'type': 'Billete' if denom_type == 'bill' else 'Moneda'}
                    denom_usd[denom_name]['quantity'] += denom_line.quantity
                    denom_usd[denom_name]['total'] += denom_line.total or 0
                    result['total_usd'] += denom_line.total or 0
                elif currency_name == 'EUR':
                    if denom_name not in denom_eur:
                        denom_eur[denom_name] = {'value': denom_value, 'quantity': 0, 'total': 0, 'type': 'Billete' if denom_type == 'bill' else 'Moneda'}
                    denom_eur[denom_name]['quantity'] += denom_line.quantity
                    denom_eur[denom_name]['total'] += denom_line.total or 0
                    result['total_eur'] += denom_line.total or 0
                else:
                    if denom_name not in denom_bs:
                        denom_bs[denom_name] = {'value': denom_value, 'quantity': 0, 'total': 0, 'type': 'Billete' if denom_type == 'bill' else 'Moneda'}
                    denom_bs[denom_name]['quantity'] += denom_line.quantity
                    denom_bs[denom_name]['total'] += denom_line.total or 0
                    result['total_bs'] += denom_line.total or 0
        
        # Convertir a lista y ordenar por valor
        result['usd'] = [{'name': k, **v} for k, v in sorted(denom_usd.items(), key=lambda x: x[1]['value'], reverse=True)]
        result['eur'] = [{'name': k, **v} for k, v in sorted(denom_eur.items(), key=lambda x: x[1]['value'], reverse=True)]
        result['bs'] = [{'name': k, **v} for k, v in sorted(denom_bs.items(), key=lambda x: x[1]['value'], reverse=True)]
        
        return result
        
        # Ordenar por valor descendente
        for currency in ['usd', 'eur', 'bs']:
            result[currency] = sorted(result[currency], key=lambda x: x['value'], reverse=True)
        
        return result


class CashRegisterConsolidatedReport(models.TransientModel):
    """Wizard para generar reportes consolidados"""
    _name = 'cash.register.consolidated.report.wizard'
    _description = 'Wizard Reporte Consolidado'

    date_from = fields.Date(
        string='Desde',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1)
    )
    date_to = fields.Date(
        string='Hasta',
        required=True,
        default=fields.Date.today
    )
    company_ids = fields.Many2many(
        'res.company',
        string='Empresas',
        default=lambda self: self.env['res.company'].search([])
    )
    state_filter = fields.Selection([
        ('all', 'Todos'),
        ('closed', 'Solo Cerrados'),
        ('in_progress', 'Solo En Proceso'),
    ], string='Estado', default='all')

    def action_view_consolidated(self):
        """Mostrar el dashboard consolidado con los filtros seleccionados"""
        self.ensure_one()
        
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        
        if self.company_ids:
            domain.append(('company_id', 'in', self.company_ids.ids))
        
        if self.state_filter == 'closed':
            domain.append(('state', '=', 'closed'))
        elif self.state_filter == 'in_progress':
            domain.append(('state', '=', 'in_progress'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Dashboard Consolidado: %s - %s') % (self.date_from, self.date_to),
            'res_model': 'cash.register.consolidated',
            'view_mode': 'tree,pivot,graph',
            'domain': domain,
            'context': {
                'search_default_group_by_date': 1,
                'search_default_group_by_company': 1,
            },
            'target': 'current',
        }

    def action_view_lines(self):
        """Mostrar las líneas consolidadas"""
        self.ensure_one()
        
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        
        if self.company_ids:
            domain.append(('company_id', 'in', self.company_ids.ids))
        
        if self.state_filter == 'closed':
            domain.append(('state', '=', 'closed'))
        elif self.state_filter == 'in_progress':
            domain.append(('state', '=', 'in_progress'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Detalle por Cuenta: %s - %s') % (self.date_from, self.date_to),
            'res_model': 'cash.register.consolidated.line',
            'view_mode': 'tree,pivot,graph',
            'domain': domain,
            'context': {
                'search_default_group_by_company': 1,
            },
            'target': 'current',
        }
