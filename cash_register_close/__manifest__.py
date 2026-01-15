# -*- coding: utf-8 -*-
{
    'name': 'Cierre de Caja Diario',
    'version': '16.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Gestión automatizada de cierre de caja diario con múltiples empresas y dual currency',
    'description': """
        Módulo de Cierre de Caja Diario Automatizado
        =============================================
        
        Este módulo permite:
        - Cierre de caja diario automatizado para múltiples empresas
        - Soporte dual currency: Bolívares (Bs/VES) y USD
        - Integración automática con account_dual_currency (si está instalado)
        - Usa debit_usd/credit_usd para cuentas en USD
        - Usa debit/credit para cuentas en Bs
        - Control de denominaciones de billetes
        - Control de billetes en mal estado
        - Resumen visual de movimientos por moneda
        - Reportes PDF estilizados con ambas monedas
        - Vista de saldos históricos
        - Balance por cuenta de efectivo
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'account_accountant',
        'base',
        'web',
    ],
    'data': [
        # Security
        'security/cash_register_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/sequence_data.xml',
        'data/denomination_data.xml',
        # Views (acciones primero)
        'views/account_account_views.xml',
        'views/cash_register_close_views.xml',
        'views/cash_register_consolidated_views.xml',
        'views/cash_denomination_views.xml',
        # Wizards (acciones de wizards)
        'wizard/cash_register_mass_close_wizard_views.xml',
        'wizard/cash_register_mass_confirm_wizard_views.xml',
        'wizard/cash_register_copy_previous_wizard_views.xml',
        # Menús (al final, después de todas las acciones)
        'views/menu_views.xml',
        # Reports
        'reports/cash_register_report.xml',
        'reports/cash_register_report_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cash_register_close/static/src/scss/cash_register.scss',
            'cash_register_close/static/src/scss/executive_dashboard.scss',
            'cash_register_close/static/src/js/cash_register_dashboard.js',
            'cash_register_close/static/src/js/executive_dashboard.js',
            'cash_register_close/static/src/xml/cash_register_templates.xml',
            'cash_register_close/static/src/xml/executive_dashboard_template.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
