# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date
from odoo.exceptions import ValidationError

class GymCoach(models.Model):
    _name = 'adk.gym.coach'
    _description = 'Coach Sportif'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _rec_name = 'name'
    _order = 'name asc'

    name = fields.Char(string="Nom complet", required=True, tracking=True, index=True)
    image_1920 = fields.Image("Photo", max_width=1920, max_height=1920)

    # AJOUT REQUIS POUR CORRIGER L'ERREUR DE VUE
    place_of_birth = fields.Char(string="Lieu de naissance")

    # ── Expertise
    specialty = fields.Char(string="Spécialité", tracking=True)
    qualification = fields.Char(string="Diplôme / Certification")
    experience_years = fields.Integer(string="Années d'expérience")
    bio = fields.Text(string="Biographie / Présentation")

    # ── Contact
    phone = fields.Char(string="Téléphone", tracking=True)
    email = fields.Char(string="Email")
    localisation = fields.Char(string="Quartier de Résidence", tracking=True)
    dob = fields.Date(string="Date de naissance")
    age = fields.Integer(string="Âge", compute="_compute_age", store=True, readonly=True)
    gender = fields.Selection([
        ('m', 'Homme'),
        ('f', 'Femme'),
        ('o', 'Autre')
    ], string="Genre", default='m')

    # AJOUTS REQUIS POUR CORRIGER LA NOUVELLE ERREUR DE VUE (Ligne 322)
    taille = fields.Float(string="Taille (cm)", tracking=True)
    poids = fields.Float(string="Poids (kg)", tracking=True)

    # ── Disponibilité
    availability = fields.Selection([
        ('available', 'Disponible'),
        ('busy', 'Occupé'),
        ('leave', 'En congé')
    ], string="Disponibilité", default='available', tracking=True)
    salle_ids = fields.Many2many('adk.gym.salle', string="Salles d'intervention")

    # ── Membres suivis
    member_ids = fields.One2many('adk.gym.member', 'coach_id', string="Membres suivis")
    member_count = fields.Integer(string="Nb Membres", compute="_compute_member_count")

    # ── Programmes encadrés (un coach peut encadrer plusieurs programmes,
    # et un programme peut être encadré par plusieurs coachs à la fois)
    program_ids = fields.Many2many(
        'adk.gym.program', 'adk_gym_program_coach_rel', 'coach_id', 'program_id',
        string="Programmes encadrés")
    program_count = fields.Integer(string="Nb Programmes", compute="_compute_program_count")

    # ── Champs techniques
    active = fields.Boolean(string="Actif", default=True)
    color = fields.Integer(string="Couleur Kanban", default=0)

    @api.depends('dob')
    def _compute_age(self):
        today = date.today()
        for rec in self:
            if rec.dob:
                rec.age = today.year - rec.dob.year - ((today.month, today.day) < (rec.dob.month, rec.dob.day))
            else:
                rec.age = 0

    @api.depends('member_ids')
    def _compute_member_count(self):
        for rec in self:
            rec.member_count = len(rec.member_ids)

    @api.depends('program_ids')
    def _compute_program_count(self):
        for rec in self:
            rec.program_count = len(rec.program_ids)

    @api.constrains('dob')
    def _check_dob(self):
        for rec in self:
            if rec.dob and rec.dob > date.today():
                raise ValidationError(_("La date de naissance ne peut pas être dans le futur."))

    def action_view_members(self):
        self.ensure_one()
        return {
            'name': _('Membres de %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'adk.gym.member',
            'view_mode': 'kanban,list,form',
            'domain': [('coach_id', '=', self.id)],
            'context': {'default_coach_id': self.id},
        }

    def action_view_programs(self):
        self.ensure_one()
        return {
            'name': _('Programmes de %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'adk.gym.program',
            'view_mode': 'kanban,list,form',
            'domain': [('coach_ids', 'in', self.id)],
            'context': {'default_coach_ids': [(4, self.id)]},
        }
