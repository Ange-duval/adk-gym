# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo import models, fields, api


class GymDashboard(models.TransientModel):
    _name = 'adk.gym.dashboard'
    _description = 'Tableau de Bord Gym'

    name = fields.Char(string="Nom", default="Mon Dashboard")

    # ── Membres
    count_members = fields.Integer(string="Total Membres", compute="_compute_stats")
    count_active_members = fields.Integer(string="Membres Actifs", compute="_compute_stats")
    count_expired_members = fields.Integer(string="Membres Expirés", compute="_compute_stats")
    count_new_members_month = fields.Integer(string="Nouveaux ce mois", compute="_compute_stats")

    # ── Structure
    count_coaches = fields.Integer(string="Coachs", compute="_compute_stats")
    count_salles = fields.Integer(string="Salles", compute="_compute_stats")
    count_activities = fields.Integer(string="Disciplines", compute="_compute_stats")

    # ── Abonnements & Finance
    count_subscriptions_active = fields.Integer(string="Abonnements Actifs", compute="_compute_stats")
    count_subscriptions_expiring_soon = fields.Integer(string="Expirent sous 7 jours", compute="_compute_stats")
    count_products_sold = fields.Integer(string="Produits vendus (qté)", compute="_compute_stats")
    total_revenue = fields.Float(string="Revenu (abonnements actifs)", compute="_compute_stats")
    total_revenue_month = fields.Float(string="Revenu du mois", compute="_compute_stats")

    # ── Équipement
    count_equipment_damaged = fields.Integer(string="Équipements HS/Maintenance", compute="_compute_stats")

    # NB : @api.depends() (sans argument) est nécessaire même si les KPI ne dépendent
    # d'aucun champ stocké du dashboard lui-même. Sans ce décorateur, Odoo ne peut pas
    # calculer ces champs via 'onchange' (utilisé pour un enregistrement pas encore
    # enregistré) : c'est ce qui provoquait l'affichage à 0 tant qu'on ne cliquait pas
    # manuellement sur "Actualiser".
    @api.depends()
    def _compute_stats(self):
        today = date.today()
        month_start = today.replace(day=1)
        Member = self.env['adk.gym.member']
        Subscription = self.env['adk.gym.subscription']
        for rec in self:
            rec.count_members = Member.search_count([])
            rec.count_active_members = Member.search_count([('membership_status', '=', 'active')])
            rec.count_expired_members = Member.search_count([('membership_status', '=', 'expired')])
            rec.count_new_members_month = Member.search_count([('registration_date', '>=', month_start)])

            rec.count_coaches = self.env['adk.gym.coach'].search_count([('active', '=', True)])
            rec.count_salles = self.env['adk.gym.salle'].search_count([('active', '=', True)])
            rec.count_activities = self.env['adk.gym.activity'].search_count([('active', '=', True)])

            active_subs = Subscription.search([('state', '=', 'active')])
            rec.count_subscriptions_active = len(active_subs)
            rec.count_subscriptions_expiring_soon = len(active_subs.filtered(
                lambda s: s.date_end and 0 <= (s.date_end - today).days <= 7))
            rec.total_revenue = sum(active_subs.mapped('total_amount'))

            month_subs = Subscription.search([('date_start', '>=', month_start), ('state', '!=', 'cancelled')])
            rec.total_revenue_month = sum(month_subs.mapped('total_amount'))

            sub_lines = self.env['adk.gym.subscription.line'].search([])
            rec.count_products_sold = int(sum(sub_lines.mapped('quantity')))

            rec.count_equipment_damaged = self.env['adk.gym.equipment.stock'].search_count(
                [('state', 'in', ['maintenance', 'damaged'])])

    def action_view_active_members(self):
        return {
            'name': 'Membres Actifs',
            'type': 'ir.actions.act_window',
            'res_model': 'adk.gym.member',
            'view_mode': 'kanban,list,form',
            'domain': [('membership_status', '=', 'active')],
        }

    def action_view_expiring_subscriptions(self):
        today = date.today()
        return {
            'name': 'Abonnements expirant bientôt',
            'type': 'ir.actions.act_window',
            'res_model': 'adk.gym.subscription',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'active'), ('date_end', '<=', today + timedelta(days=7)),
                       ('date_end', '>=', today)],
        }

    def action_refresh(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'adk.gym.dashboard',
            'view_mode': 'form',
            'target': 'main',
            'res_id': self.id,
        }

    @api.model
    def action_open_dashboard(self):
        """Point d'entrée du menu 'Tableau de Bord'.

        Auparavant, le menu ouvrait directement une action fenêtre sans `res_id` :
        Odoo affichait alors un enregistrement "brouillon" (jamais sauvegardé) et
        calculait les champs via `onchange`, qui ignore les champs calculés sans
        `@api.depends` -> tous les KPI restaient à 0 tant qu'on ne cliquait pas sur
        "Actualiser". On crée maintenant systématiquement un enregistrement réel en
        base, ce qui force un `read()` classique (toujours à jour) dès l'ouverture,
        sans aucune action manuelle.
        """
        dashboard = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tableau de Bord',
            'res_model': 'adk.gym.dashboard',
            'view_mode': 'form',
            'target': 'main',
            'res_id': dashboard.id,
        }
