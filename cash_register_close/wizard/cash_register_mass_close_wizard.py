# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date


class CashRegisterMassCloseWizard(models.TransientModel):
    """Wizard para crear cierres de caja masivos en múltiples empresas"""
    _name = 'cash.register.mass.close.wizard'
    _description = 'Wizard Cierre Masivo Multi-Empresa'

    @api.model
    def default_get(self, fields_list):
        """Calcular valores por defecto incluyendo contadores"""
        res = super().default_get(fields_list)
        
        # Obtener todas las empresas
        all_companies = self.env['res.company'].search([])
        today = fields.Date.context_today(self)
        
        # Buscar cierres existentes para hoy (excluyendo cancelados)
        CashClose = self.env['cash.register.close']
        existing_closes = CashClose.sudo().search([
            ('date', '=', today),
            ('company_id', 'in', all_companies.ids),
            ('state', '!=', 'cancelled')
        ])
        
        companies_with_close = existing_closes.mapped('company_id')
        companies_without_close = all_companies - companies_with_close
        
        res.update({
            'company_ids': [(6, 0, all_companies.ids)],
            'companies_count': len(all_companies),
            'existing_closes_count': len(companies_with_close),
            'new_closes_count': len(companies_without_close),
            'companies_with_close_ids': [(6, 0, companies_with_close.ids)],
            'companies_without_close_ids': [(6, 0, companies_without_close.ids)],
        })
        
        return res

    date = fields.Date(
        string='Fecha de Cierre',
        required=True,
        default=fields.Date.context_today,
        help='Fecha para la cual se generarán los cierres de caja'
    )
    
    company_ids = fields.Many2many(
        'res.company',
        string='Empresas',
        default=lambda self: self.env['res.company'].search([]),
        help='Seleccione las empresas para las cuales generar cierres de caja. Deje vacío para todas.'
    )
    
    select_all_companies = fields.Boolean(
        string='Todas las Empresas',
        default=True,
        help='Marque para seleccionar todas las empresas disponibles'
    )
    
    skip_existing = fields.Boolean(
        string='Omitir Existentes',
        default=True,
        help='Si está marcado, no se creará cierre para empresas que ya tengan uno en esa fecha'
    )
    
    auto_generate_lines = fields.Boolean(
        string='Generar Líneas Automáticamente',
        default=True,
        help='Generar automáticamente las líneas de cierre con los saldos del día'
    )
    
    # Campos informativos - Ahora son campos regulares actualizados por onchange
    companies_count = fields.Integer(
        string='Cantidad de Empresas',
        default=0
    )
    
    existing_closes_count = fields.Integer(
        string='Cierres Existentes',
        default=0
    )
    
    new_closes_count = fields.Integer(
        string='Cierres a Crear',
        default=0
    )
    
    companies_with_close_ids = fields.Many2many(
        'res.company',
        'mass_close_wizard_existing_company_rel',
        string='Empresas con Cierre'
    )
    
    companies_without_close_ids = fields.Many2many(
        'res.company',
        'mass_close_wizard_new_company_rel',
        string='Empresas sin Cierre'
    )
    
    # Lista de empresas disponibles para mostrar en el wizard
    available_company_ids = fields.Many2many(
        'res.company',
        'mass_close_wizard_available_company_rel',
        string='Empresas Disponibles',
        compute='_compute_available_companies'
    )
    
    # Campo para mostrar resumen de empresas seleccionadas
    companies_summary = fields.Html(
        string='Resumen',
        default='<div></div>'
    )

    @api.onchange('select_all_companies')
    def _onchange_select_all_companies(self):
        """Cuando se marca 'Todas las empresas', seleccionar todas"""
        if self.select_all_companies:
            self.company_ids = self.env['res.company'].search([])
        else:
            # No borrar, solo dejar que el usuario modifique manualmente
            pass
        # Forzar actualización de contadores
        self._onchange_company_ids()

    @api.onchange('company_ids', 'date', 'skip_existing')
    def _onchange_company_ids(self):
        """Actualizar contadores cuando cambian las empresas seleccionadas"""
        CashClose = self.env['cash.register.close']
        
        # Contar empresas seleccionadas
        self.companies_count = len(self.company_ids) if self.company_ids else 0
        
        if self.company_ids and self.date:
            # Buscar cierres existentes para la fecha seleccionada (excluyendo cancelados)
            existing_closes = CashClose.sudo().search([
                ('date', '=', self.date),
                ('company_id', 'in', self.company_ids.ids),
                ('state', '!=', 'cancelled')
            ])
            
            companies_with_close = existing_closes.mapped('company_id')
            companies_without_close = self.company_ids - companies_with_close
            
            self.existing_closes_count = len(companies_with_close)
            self.companies_with_close_ids = companies_with_close
            self.companies_without_close_ids = companies_without_close
            
            if self.skip_existing:
                self.new_closes_count = len(companies_without_close)
            else:
                self.new_closes_count = len(self.company_ids)
        else:
            self.existing_closes_count = 0
            self.new_closes_count = 0
            self.companies_with_close_ids = False
            self.companies_without_close_ids = False
        
        # Actualizar resumen HTML
        self._update_companies_summary()

    def _update_companies_summary(self):
        """Actualiza el campo HTML de resumen"""
        html = '<div class="companies_summary">'
        
        if self.companies_without_close_ids:
            html += '<div class="mb-2"><strong class="text-success">✓ Se crearán cierres para:</strong><br/>'
            for company in self.companies_without_close_ids[:10]:
                html += f'<span class="badge bg-success me-1 mb-1">{company.name}</span>'
            if len(self.companies_without_close_ids) > 10:
                html += f'<span class="badge bg-secondary">+{len(self.companies_without_close_ids) - 10} más</span>'
            html += '</div>'
        
        if self.companies_with_close_ids and self.skip_existing:
            html += '<div><strong class="text-warning">⏭ Ya tienen cierre (se omitirán):</strong><br/>'
            for company in self.companies_with_close_ids[:5]:
                html += f'<span class="badge bg-warning text-dark me-1 mb-1">{company.name}</span>'
            if len(self.companies_with_close_ids) > 5:
                html += f'<span class="badge bg-secondary">+{len(self.companies_with_close_ids) - 5} más</span>'
            html += '</div>'
        
        html += '</div>'
        self.companies_summary = html

    @api.depends('select_all_companies')
    def _compute_available_companies(self):
        """Obtiene todas las empresas disponibles"""
        all_companies = self.env['res.company'].search([])
        for wizard in self:
            wizard.available_company_ids = all_companies

    def action_select_all(self):
        """Seleccionar todas las empresas"""
        self.company_ids = self.env['res.company'].search([])
        self.select_all_companies = True
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_deselect_all(self):
        """Deseleccionar todas las empresas"""
        self.company_ids = False
        self.select_all_companies = False
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_create_mass_close(self):
        """Crear cierres de caja para todas las empresas seleccionadas"""
        self.ensure_one()
        
        if not self.company_ids:
            raise UserError(_('Debe seleccionar al menos una empresa.'))
        
        CashClose = self.env['cash.register.close']
        created_closes = self.env['cash.register.close']
        skipped_companies = []
        error_companies = []
        
        companies_to_process = self.company_ids
        
        if self.skip_existing:
            companies_to_process = self.companies_without_close_ids
            skipped_companies = self.companies_with_close_ids.mapped('name')
        
        for company in companies_to_process:
            try:
                # Verificar si ya existe un cierre NO cancelado (doble check)
                existing = CashClose.sudo().search([
                    ('date', '=', self.date),
                    ('company_id', '=', company.id),
                    ('state', '!=', 'cancelled')
                ], limit=1)
                
                if existing and self.skip_existing:
                    skipped_companies.append(company.name)
                    continue
                
                # Crear el cierre de caja para esta empresa
                # Usamos with_company para cambiar el contexto de empresa
                close = CashClose.with_company(company).sudo().create({
                    'date': self.date,
                    'company_id': company.id,
                    'user_id': self.env.user.id,
                })
                
                # Generar líneas automáticamente si está habilitado
                # IMPORTANTE: También debemos usar with_company para que busque las cuentas correctas
                if self.auto_generate_lines:
                    close.with_company(company).action_generate_lines()
                
                created_closes += close
                
            except Exception as e:
                error_companies.append(f"{company.name}: {str(e)}")
        
        # Preparar mensaje de resultado
        message_parts = []
        
        if created_closes:
            message_parts.append(_('✅ Se crearon %d cierres de caja exitosamente.') % len(created_closes))
        
        if skipped_companies:
            message_parts.append(_('⏭️ Se omitieron %d empresas (ya tienen cierre): %s') % (
                len(skipped_companies), ', '.join(skipped_companies[:5]) + ('...' if len(skipped_companies) > 5 else '')
            ))
        
        if error_companies:
            message_parts.append(_('❌ Errores en %d empresas: %s') % (
                len(error_companies), ', '.join(error_companies[:3]) + ('...' if len(error_companies) > 3 else '')
            ))
        
        # Si se crearon cierres, mostrar la vista consolidada
        if created_closes:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Cierres Creados - %s') % self.date,
                'res_model': 'cash.register.close',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', created_closes.ids)],
                'context': {
                    'default_date': self.date,
                    'search_default_group_by_company': 1,
                    'create': False,
                },
                'target': 'current',
            }
        else:
            raise UserError('\n'.join(message_parts) if message_parts else _('No se creó ningún cierre.'))

    def action_view_preview(self):
        """Ver preview de qué cierres se crearán - con detalles de debug"""
        self.ensure_one()
        
        CashClose = self.env['cash.register.close']
        
        message = []
        message.append(_('📅 Fecha seleccionada: %s') % self.date)
        message.append(_('🏢 Empresas seleccionadas: %d') % self.companies_count)
        message.append('')
        
        # Buscar TODOS los cierres para esta fecha (para debug)
        all_closes_for_date = CashClose.sudo().search([
            ('date', '=', self.date),
            ('company_id', 'in', self.company_ids.ids)
        ])
        
        if all_closes_for_date:
            message.append(_('⚠️ CIERRES ENCONTRADOS EN BD PARA ESTA FECHA (%d):') % len(all_closes_for_date))
            for close in all_closes_for_date[:15]:
                message.append(f'   • {close.company_id.name} - Estado: {close.state} - Ref: {close.name} - ID: {close.id}')
            if len(all_closes_for_date) > 15:
                message.append(f'   ... y {len(all_closes_for_date) - 15} más')
            message.append('')
        else:
            message.append(_('✅ No hay cierres en la base de datos para esta fecha'))
            message.append('')
        
        if self.companies_without_close_ids:
            message.append(_('✅ Se crearán cierres para (%d):') % len(self.companies_without_close_ids))
            for company in self.companies_without_close_ids[:10]:
                message.append(f'   • {company.name}')
            if len(self.companies_without_close_ids) > 10:
                message.append(f'   ... y {len(self.companies_without_close_ids) - 10} más')
        
        if self.companies_with_close_ids and self.skip_existing:
            message.append('')
            message.append(_('⏭️ Se omitirán (ya tienen cierre NO cancelado) (%d):') % len(self.companies_with_close_ids))
            for company in self.companies_with_close_ids[:10]:
                message.append(f'   • {company.name}')
            if len(self.companies_with_close_ids) > 10:
                message.append(f'   ... y {len(self.companies_with_close_ids) - 10} más')
        
        raise UserError('\n'.join(message))
