# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CashRegisterMassConfirmWizard(models.TransientModel):
    _name = 'cash.register.mass.confirm.wizard'
    _description = 'Wizard para Confirmación Masiva de Cierres'

    date_from = fields.Date(
        string='Desde',
        required=True,
        default=fields.Date.context_today
    )
    date_to = fields.Date(
        string='Hasta',
        required=True,
        default=fields.Date.context_today
    )
    company_ids = fields.Many2many(
        'res.company',
        string='Compañías',
        help='Dejar vacío para incluir todas las compañías'
    )
    
    # Contadores
    closes_to_confirm = fields.Integer(
        string='Cierres a Confirmar',
        compute='_compute_closes_count'
    )
    closes_already_confirmed = fields.Integer(
        string='Ya Confirmados',
        compute='_compute_closes_count'
    )
    
    close_ids = fields.Many2many(
        'cash.register.close',
        string='Cierres Seleccionados',
        compute='_compute_close_ids'
    )
    
    @api.depends('date_from', 'date_to', 'company_ids')
    def _compute_close_ids(self):
        for wizard in self:
            domain = [
                ('date', '>=', wizard.date_from),
                ('date', '<=', wizard.date_to),
                ('state', '=', 'closed'),
            ]
            if wizard.company_ids:
                domain.append(('company_id', 'in', wizard.company_ids.ids))
            
            wizard.close_ids = self.env['cash.register.close'].sudo().search(domain)
    
    @api.depends('date_from', 'date_to', 'company_ids')
    def _compute_closes_count(self):
        for wizard in self:
            domain_base = [
                ('date', '>=', wizard.date_from),
                ('date', '<=', wizard.date_to),
            ]
            if wizard.company_ids:
                domain_base.append(('company_id', 'in', wizard.company_ids.ids))
            
            # Cierres pendientes de confirmar (estado = closed)
            domain_to_confirm = domain_base + [('state', '=', 'closed')]
            wizard.closes_to_confirm = self.env['cash.register.close'].sudo().search_count(domain_to_confirm)
            
            # Cierres ya confirmados
            domain_confirmed = domain_base + [('state', '=', 'confirmed')]
            wizard.closes_already_confirmed = self.env['cash.register.close'].sudo().search_count(domain_confirmed)
    
    def action_confirm_all(self):
        """Confirma todos los cierres pendientes"""
        self.ensure_one()
        
        if not self.close_ids:
            raise UserError(_('No hay cierres pendientes de confirmar en el rango seleccionado.'))
        
        # Obtener la firma del usuario que confirma (el usuario actual)
        user_signature = self._get_user_signature()
        
        confirmed_count = 0
        for close in self.close_ids:
            if close.state == 'closed':
                close.sudo().write({
                    'state': 'confirmed',
                    'confirmed_by_id': self.env.user.id,
                    'confirmed_date': fields.Datetime.now(),
                    'confirmed_signature': user_signature,
                })
                confirmed_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Confirmación Masiva Completada'),
                'message': _('Se confirmaron %s cierres de caja correctamente.') % confirmed_count,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
    
    def _get_user_signature(self):
        """Obtiene la firma del usuario actual desde su configuración"""
        user = self.env.user
        signature = None
        # Campo de firma digital (módulo sign o hr)
        if hasattr(user, 'sign_signature') and user.sign_signature:
            signature = user.sign_signature
        # Campo de firma del empleado relacionado
        elif hasattr(user, 'employee_id') and user.employee_id:
            emp = user.employee_id
            if hasattr(emp, 'sign_signature') and emp.sign_signature:
                signature = emp.sign_signature
        return signature
    
    def action_view_closes(self):
        """Ver los cierres que se van a confirmar"""
        self.ensure_one()
        return {
            'name': _('Cierres a Confirmar'),
            'type': 'ir.actions.act_window',
            'res_model': 'cash.register.close',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.close_ids.ids)],
            'context': {'create': False},
        }
