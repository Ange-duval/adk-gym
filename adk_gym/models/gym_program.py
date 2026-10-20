# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class GymProgram(models.Model):
    _name = 'adk.gym.program'
    _description = "Programme d'Entraînement"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    name = fields.Char(string="Nom du Programme", required=True, tracking=True)

    # Un programme peut désormais concerner plusieurs membres à la fois
    # (relation Many2many, table dédiée pour ne pas interférer avec d'autres liens membre/programme).
    member_ids = fields.Many2many(
        'adk.gym.member', 'adk_gym_program_member_rel', 'program_id', 'member_id',
        string="Membres", required=True, tracking=True)

    # Un programme peut être encadré par plusieurs coachs à la fois
    coach_ids = fields.Many2many(
        'adk.gym.coach', 'adk_gym_program_coach_rel', 'program_id', 'coach_id',
        string="Coachs / Instructeurs", tracking=True)

    date_start = fields.Date(string="Date de début", default=fields.Date.today, tracking=True)
    date_end = fields.Date(string="Date de fin", tracking=True)

    # L'objectif n'est plus une simple liste figée (Selection) mais pointe vers la
    # configuration "Objectif Sportif" (adk.gym.objective) déjà utilisée sur la fiche Membre.
    # Cela permet de réutiliser les objectifs existants ET d'en créer de nouveaux à la volée
    # si le choix recherché n'existe pas encore dans la configuration.
    # Un programme peut viser plusieurs objectifs à la fois : relation Many2many.
    goal_ids = fields.Many2many(
        'adk.gym.objective', 'adk_gym_program_goal_rel', 'program_id', 'objective_id',
        string="Objectifs ciblés", tracking=True)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('in_progress', 'En cours'),
        ('done', 'Terminé'),
    ], string="État", default='draft', tracking=True)

    line_ids = fields.One2many('adk.gym.program.line', 'program_id', string="Liste des Exercices")
    line_count = fields.Integer(string="Nb Exercices", compute="_compute_line_count")

    notes = fields.Text(string="Observations du Coach")
    active = fields.Boolean(string="Actif", default=True)
    color = fields.Integer(string="Couleur Kanban", default=0)

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class GymProgramLine(models.Model):
    _name = 'adk.gym.program.line'
    _description = "Ligne d'Exercice"
    _order = 'sequence, id'

    program_id = fields.Many2one('adk.gym.program', ondelete='cascade', string="Programme", required=True)
    sequence = fields.Integer(string="Séquence", default=10)
    exercise_name = fields.Char(string="Exercice", required=True)
    sets = fields.Integer(string="Séries", default=3)
    reps = fields.Char(string="Répétitions", default="10-12")
    weight = fields.Char(string="Charge (kg)", help="Poids à utiliser")
    rest_time = fields.Char(string="Repos", default="1min", help="Temps de repos entre les séries")
