# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class GymSubscriptionRenewWizard(models.TransientModel):
    _name = 'adk.gym.subscription.renew.wizard'
    _description = 'Assistant Renouvellement'

    subscription_id = fields.Many2one('adk.gym.subscription', string="Abonnement source", readonly=True)
    member_id = fields.Many2one('adk.gym.member', string="Membre", readonly=True)
    type = fields.Selection([
        ('daily', 'Journalier'), 
        ('monthly', 'Mensuel'), 
        ('quarterly', 'Trimestriel'), 
        ('annual', 'Annuel')
    ], string="Type", required=True)
    date_start = fields.Date(string="Date de début", required=True, default=fields.Date.today)
    coach_id = fields.Many2one('adk.gym.coach', string="Coach")
    discipline_ids = fields.Many2many('adk.gym.activity', string="Disciplines")

    def action_renew(self):
        new_sub = self.env['adk.gym.subscription'].create({
            'member_id': self.member_id.id,
            'type': self.type,
            'date_start': self.date_start,
            'coach_id': self.coach_id.id,
            'discipline_ids': [(6, 0, self.discipline_ids.ids)],
        })
        return {
            'name': _('Nouvel Abonnement'),
            'type': 'ir.actions.act_window',
            'res_model': 'adk.gym.subscription',
            'res_id': new_sub.id,
            'view_mode': 'form',
        }
