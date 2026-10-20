# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class GymReportWizard(models.TransientModel):
    _name = 'adk.gym.report.wizard'
    _description = 'Assistant de Rapport'

    date_start = fields.Date(string="Date de début", required=True, default=fields.Date.today)
    date_end = fields.Date(string="Date de fin", required=True, default=fields.Date.today)
    state_filter = fields.Selection([
        ('all', 'Tous'), 
        ('active', 'Actifs'), 
        ('expired', 'Expirés')
    ], string="Filtrer par état", default='all')
    salle_id = fields.Many2one('adk.gym.salle', string="Salle")

    def action_print_report(self):
        domain = [('date_start', '>=', self.date_start), ('date_start', '<=', self.date_end)]
        if self.state_filter != 'all':
            domain.append(('state', '=', self.state_filter))
        if self.salle_id:
            domain.append(('salle_id', '=', self.salle_id.id))
        subs = self.env['adk.gym.subscription'].search(domain)
        if not subs:
            raise UserError(_("Aucun abonnement trouvé."))
        return self.env.ref('adk_gym.action_report_subscription_period').report_action(subs)
