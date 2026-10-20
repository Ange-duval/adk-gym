# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date
from odoo.exceptions import UserError, ValidationError

class GymMember(models.Model):
    _name = 'adk.gym.member'
    _description = 'Membre Gym'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _rec_name = 'name'
    _order = 'name asc'

    # ── Identité
    name = fields.Char(string="Nom complet", required=True, tracking=True, index=True)
    image_1920 = fields.Image("Photo", max_width=1920, max_height=1920)
    place_of_birth = fields.Char(string="Lieu de naissance")
    dob = fields.Date(string="Date de naissance")
    age = fields.Integer(string="Âge", compute="_compute_age", store=True, readonly=True)
    gender = fields.Selection([
        ('m', 'Homme'), 
        ('f', 'Femme'), 
        ('o', 'Autre')
    ], string="Genre", default='m', tracking=True)

    # ── Physique
    taille = fields.Float(string="Taille (cm)", tracking=True)
    poids = fields.Float(string="Poids (kg)", tracking=True)
    imc = fields.Float(string="IMC", compute="_compute_imc", store=True, digits=(5, 2))
    imc_category = fields.Char(string="Catégorie IMC", compute="_compute_imc", store=True)

    # ── Niveau & Objectif
    practice_level_id = fields.Many2one('adk.gym.practice.level', string="Niveau de pratique", tracking=True)
    # Un membre peut viser plusieurs objectifs sportifs à la fois (ex: "Perte de
    # poids" ET "Cardio / Endurance") : relation Many2many plutôt qu'un choix unique.
    objective_ids = fields.Many2many('adk.gym.objective', string="Objectifs Sportifs", tracking=True)

    # ── Contact
    localisation = fields.Char(string="Quartier / Localisation", tracking=True)
    phone = fields.Char(string="Téléphone", tracking=True)
    email = fields.Char(string="Email", tracking=True)
    partner_id = fields.Many2one('res.partner', string="Contact Client (Facturation)", tracking=True)

    # ── Santé
    has_medical_condition = fields.Selection([
        ('non', 'Non'), 
        ('oui', 'Oui')
    ], string="Contre-indication médicale", default='non', tracking=True)
    medical_details = fields.Text(string="Détails médicaux")

    # ── Liens
    salle_id = fields.Many2one('adk.gym.salle', string="Salle / Club", tracking=True)
    coach_id = fields.Many2one('adk.gym.coach', string="Coach personnel", tracking=True)
    subscription_ids = fields.One2many('adk.gym.subscription', 'member_id', string="Historique Abonnements")
    # Un membre peut désormais apparaître dans plusieurs programmes (et un programme
    # peut regrouper plusieurs membres) : relation inverse Many2many, alignée sur la
    # table 'adk_gym_program_member_rel' définie côté adk.gym.program.
    program_ids = fields.Many2many(
        'adk.gym.program', 'adk_gym_program_member_rel', 'member_id', 'program_id',
        string="Programmes d'entraînement")

    # ── Statistiques calculées
    subscription_count = fields.Integer(string="Nb Abonnements", compute="_compute_subscription_count")
    active_subscription_id = fields.Many2one(
        'adk.gym.subscription', string="Abonnement Actif",
        compute="_compute_active_subscription", store=False)
    is_active_member = fields.Boolean(string="Membre Actif", compute="_compute_active_subscription", store=True)
    membership_status = fields.Selection([
        ('active', 'Actif'), 
        ('expired', 'Expiré'), 
        ('none', 'Aucun abonnement')
    ], string="Statut", compute="_compute_active_subscription", store=True)

    # ── Champs techniques
    active = fields.Boolean(string="Actif", default=True)
    registration_date = fields.Date(string="Date d'inscription", default=fields.Date.today, readonly=True)
    color = fields.Integer(string="Couleur Kanban", default=0)

    @api.depends('dob')
    def _compute_age(self):
        today = date.today()
        for rec in self:
            if rec.dob:
                rec.age = today.year - rec.dob.year - ((today.month, today.day) < (rec.dob.month, rec.dob.day))
            else:
                rec.age = 0

    @api.depends('taille', 'poids')
    def _compute_imc(self):
        for rec in self:
            if rec.taille and rec.poids and rec.taille > 0:
                taille_m = rec.taille / 100.0
                imc = rec.poids / (taille_m ** 2)
                rec.imc = round(imc, 2)
                if imc < 18.5:
                    rec.imc_category = 'Insuffisance pondérale'
                elif imc < 25:
                    rec.imc_category = 'Poids normal'
                elif imc < 30:
                    rec.imc_category = 'Surpoids'
                else:
                    rec.imc_category = 'Obésité'
            else:
                rec.imc = 0.0
                rec.imc_category = ''

    @api.depends('subscription_ids')
    def _compute_subscription_count(self):
        for rec in self:
            rec.subscription_count = len(rec.subscription_ids)

    @api.depends('subscription_ids', 'subscription_ids.state')
    def _compute_active_subscription(self):
        for rec in self:
            active_sub = rec.subscription_ids.filtered(lambda s: s.state == 'active')
            if active_sub:
                rec.active_subscription_id = active_sub[0]
                rec.is_active_member = True
                rec.membership_status = 'active'
            else:
                expired_sub = rec.subscription_ids.filtered(lambda s: s.state == 'expired')
                rec.active_subscription_id = False
                rec.is_active_member = False
                rec.membership_status = 'expired' if expired_sub else 'none'

    @api.constrains('dob')
    def _check_dob(self):
        for rec in self:
            if rec.dob and rec.dob > date.today():
                raise ValidationError(_("La date de naissance ne peut pas être dans le futur."))
            if rec.dob and rec.age < 5:
                raise ValidationError(_("L'âge minimum pour s'inscrire est de 5 ans."))

    @api.constrains('taille', 'poids')
    def _check_morphology(self):
        for rec in self:
            if rec.taille and rec.taille < 0:
                raise ValidationError(_("La taille ne peut pas être négative."))
            if rec.poids and rec.poids < 0:
                raise ValidationError(_("Le poids ne peut pas être négatif."))

    def action_view_subscriptions(self):
        self.ensure_one()
        return {
            'name': _('Abonnements de %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'adk.gym.subscription',
            'view_mode': 'list,form',
            'domain': [('member_id', '=', self.id)],
            'context': {'default_member_id': self.id},
        }

    def action_create_subscription(self):
        self.ensure_one()
        return {
            'name': _('Nouvel Abonnement'),
            'type': 'ir.actions.act_window',
            'res_model': 'adk.gym.subscription',
            'view_mode': 'form',
            'context': {
                'default_member_id': self.id,
                'default_coach_id': self.coach_id.id,
                'default_salle_id': self.salle_id.id,
            },
        }

    def action_create_partner(self):
        self.ensure_one()
        if self.partner_id:
            raise UserError(_("Ce membre est déjà lié à un contact."))
        partner = self.env['res.partner'].create({
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'comment': _('Membre Gym ADK - Inscrit le %s') % str(self.registration_date),
        })
        self.partner_id = partner

    def action_archive(self):
        self.write({'active': False})

    def action_unarchive(self):
        self.write({'active': True})
