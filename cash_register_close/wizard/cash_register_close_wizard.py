# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CashRegisterCloseWizard(models.TransientModel):
    _name = 'cash.register.close.wizard'
    _description = 'Wizard Cierre Masivo de Caja'

    date = fields.Date(
        string='Fecha de Cierre',
        required=True,
        default=fields.Date.context_today
    )
    company_ids = fields.Many2many(
        'res.company',
        string='Compañías',
        required=True,
        default=lambda self: self._default_companies()
    )
    close_all_companies = fields.Boolean(
        string='Cerrar Todas las Compañías',
        default=True
    )
    
    def _default_companies(self):
        """Retorna todas las compañías que el usuario puede ver"""
        return self.env['res.company'].search([])
    
    @api.onchange('close_all_companies')
    def _onchange_close_all_companies(self):
        if self.close_all_companies:
            self.company_ids = self._default_companies()
    
    def action_create_closes(self):
        """Crea cierres de caja para todas las compañías seleccionadas"""
        if not self.company_ids:
            raise UserError(_('Debe seleccionar al menos una compañía'))
        
        closes = self.env['cash.register.close']
        errors = []
        
        for company in self.company_ids:
            # Verificar si ya existe un cierre para esta fecha y compañía
            existing = self.env['cash.register.close'].sudo().search([
                ('date', '=', self.date),
                ('company_id', '=', company.id),
                ('state', '!=', 'cancelled')
            ], limit=1)
            
            if existing:
                closes |= existing
                continue
            
            # Verificar si hay cuentas de efectivo en esta compañía
            # Usar with_company para acceso cross-company correcto
            cash_accounts = self.env['account.account'].sudo().with_company(company).search([
                ('is_cash_account', '=', True),
                ('company_id', '=', company.id),
                ('deprecated', '=', False)
            ])
            
            if not cash_accounts:
                errors.append(_('No hay cuentas de efectivo configuradas para %s') % company.name)
                continue
            
            try:
                # Crear cierre con contexto de empresa correcto
                close = self.env['cash.register.close'].sudo().with_company(company).create({
                    'date': self.date,
                    'company_id': company.id,
                    'user_id': self.env.user.id,
                })
                # Generar líneas con contexto de empresa correcto
                close.with_company(company).action_generate_lines()
                closes |= close
            except Exception as e:
                errors.append(_('Error en %s: %s') % (company.name, str(e)))
        
        if errors and not closes:
            raise UserError('\n'.join(errors))
        
        message = _('Se crearon/actualizaron %s cierres de caja correctamente.') % len(closes)
        if errors:
            message += '\n\n' + _('Advertencias:\n') + '\n'.join(errors)
        
        if len(closes) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'cash.register.close',
                'res_id': closes.id,
                'view_mode': 'form',
                'target': 'current',
            }
        
        return {
            'name': _('Cierres de Caja Generados'),
            'type': 'ir.actions.act_window',
            'res_model': 'cash.register.close',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', closes.ids)],
            'target': 'current',
            'context': {
                'search_default_group_by_company': 1,
            }
        }
    
    def action_preview(self):
        """Previsualiza los cierres que se van a crear"""
        preview_data = []
        for company in self.company_ids:
            existing = self.env['cash.register.close'].sudo().search([
                ('date', '=', self.date),
                ('company_id', '=', company.id),
                ('state', '!=', 'cancelled')
            ], limit=1)
            
            cash_accounts = self.env['account.account'].sudo().search([
                ('is_cash_account', '=', True),
                ('company_id', '=', company.id),
                ('deprecated', '=', False)
            ])
            
            preview_data.append({
                'company': company.name,
                'accounts': len(cash_accounts),
                'existing': bool(existing),
                'status': 'Existente' if existing else ('Pendiente' if cash_accounts else 'Sin cuentas')
            })
        
        # Retornar mensaje informativo
        message = _('Vista previa de cierres para %s:\n\n') % self.date
        for data in preview_data:
            status_icon = '✅' if data['existing'] else ('⏳' if data['accounts'] else '❌')
            message += f"{status_icon} {data['company']}: {data['accounts']} cuentas - {data['status']}\n"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Vista Previa'),
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        }
