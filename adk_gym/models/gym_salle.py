# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

WEEKDAYS = [
    ('0', 'Lundi'),
    ('1', 'Mardi'),
    ('2', 'Mercredi'),
    ('3', 'Jeudi'),
    ('4', 'Vendredi'),
    ('5', 'Samedi'),
    ('6', 'Dimanche'),
]

# Horaires par défaut proposés lors de la génération automatique de la semaine :
# (jour, fermé ?, heure d'ouverture, heure de fermeture)
DEFAULT_WEEK_HOURS = [
    ('0', False, 8.0, 21.0),
    ('1', False, 8.0, 21.0),
    ('2', False, 8.0, 21.0),
    ('3', False, 8.0, 21.0),
    ('4', False, 8.0, 21.0),
    ('5', False, 9.0, 18.0),
    ('6', True, 0.0, 0.0),
]


class GymSalleHours(models.Model):
    _name = 'adk.gym.salle.hours'
    _description = "Horaire d'ouverture d'une salle"
    _order = 'weekday asc'
    _rec_name = 'weekday'

    salle_id = fields.Many2one(
        'adk.gym.salle', string="Salle", required=True, ondelete='cascade', index=True)
    weekday = fields.Selection(WEEKDAYS, string="Jour", required=True)
    is_closed = fields.Boolean(string="Fermé", default=False)
    # Champs "Float" avec le widget float_time : Odoo affiche automatiquement
    # un sélecteur d'heure (HH:MM) au lieu d'une simple case de texte libre.
    opening_time = fields.Float(string="Ouverture", default=8.0)
    closing_time = fields.Float(string="Fermeture", default=20.0)

    _sql_constraints = [
        ('salle_weekday_uniq', 'unique(salle_id, weekday)',
         "Un seul horaire peut être défini par jour et par salle."),
    ]

    @api.constrains('opening_time', 'closing_time', 'is_closed')
    def _check_hours_range(self):
        for rec in self:
            if rec.is_closed:
                continue
            if not (0.0 <= rec.opening_time < 24.0) or not (0.0 < rec.closing_time <= 24.0):
                raise ValidationError(_("Les horaires doivent être compris entre 00:00 et 24:00."))
            if rec.closing_time <= rec.opening_time:
                raise ValidationError(_(
                    "L'heure de fermeture doit être postérieure à l'heure d'ouverture (%s).")
                    % dict(WEEKDAYS).get(rec.weekday))


class GymSalle(models.Model):
    _name = 'adk.gym.salle'
    _description = 'Salle de Gym'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _rec_name = 'name'
    _order = 'name asc'

    name = fields.Char(string="Nom de la salle", required=True, tracking=True, index=True)

    # ── Localisation structurée : pays sélectionnable dans la base Odoo,
    # ville et quartier saisis librement (aucune base de villes/quartiers
    # n'existe nativement dans Odoo pour tous les pays du monde).
    country_id = fields.Many2one(
        'res.country', string="Pays", tracking=True,
        default=lambda self: self.env.company.country_id)
    state_id = fields.Many2one(
        'res.country.state', string="Région / État", tracking=True,
        domain="[('country_id', '=', country_id)]")
    city = fields.Char(string="Ville", tracking=True)
    district = fields.Char(string="Quartier", tracking=True)

    phone = fields.Char(string="Téléphone", tracking=True)
    email = fields.Char(string="Email")
    website = fields.Char(string="Site Web")
    description = fields.Text(string="Description")
    capacity = fields.Integer(string="Capacité max (personnes)")

    # ── Horaires d'ouverture structurés : un sélecteur d'heure (widget
    # float_time) par jour de la semaine, au lieu d'un champ texte libre.
    hours_ids = fields.One2many('adk.gym.salle.hours', 'salle_id', string="Horaires d'ouverture")
    opening_hours_display = fields.Char(
        string="Horaires", compute="_compute_opening_hours_display", store=True)

    member_ids = fields.One2many('adk.gym.member', 'salle_id', string="Membres rattachés")
    # Inventaire de la salle : chaque ligne pointe vers un article partagé
    # (adk.gym.equipment) déjà existant, avec la quantité/état propres à CETTE
    # salle. Un même article (ex: 'Masse') peut ainsi apparaître dans plusieurs
    # salles sans jamais être dupliqué.
    equipment_ids = fields.One2many('adk.gym.equipment.stock', 'salle_id', string="Inventaire Équipements")
    coach_ids = fields.Many2many('adk.gym.coach', string="Coachs")

    member_count = fields.Integer(string="Nb Membres", compute="_compute_stats")
    equipment_count = fields.Integer(string="Nb Équipements", compute="_compute_stats")
    active = fields.Boolean(string="Active", default=True)

    # Champ technique utilisé uniquement côté vue pour rendre les champs de
    # localisation (pays/région/ville/quartier) en lecture seule pour tout le
    # monde sauf l'Administrateur Gym, une fois la salle déjà créée. La
    # création reste possible pour le Responsable (id vide -> non bloqué).
    is_gym_admin = fields.Boolean(
        string="Est administrateur Gym", compute="_compute_is_gym_admin")

    def _compute_is_gym_admin(self):
        is_admin = self.env.user.has_group('adk_gym.group_gym_admin')
        for rec in self:
            rec.is_gym_admin = is_admin

    _sql_constraints = [
        ('capacity_positive', 'CHECK(capacity IS NULL OR capacity >= 0)',
         "La capacité maximale ne peut pas être négative."),
    ]

    @api.depends('member_ids', 'equipment_ids')
    def _compute_stats(self):
        for rec in self:
            rec.member_count = len(rec.member_ids)
            rec.equipment_count = len(rec.equipment_ids)

    @api.depends('hours_ids.weekday', 'hours_ids.is_closed', 'hours_ids.opening_time', 'hours_ids.closing_time')
    def _compute_opening_hours_display(self):
        weekday_labels = dict(WEEKDAYS)
        for rec in self:
            if not rec.hours_ids:
                rec.opening_hours_display = _("Non défini")
                continue
            parts = []
            for line in rec.hours_ids.sorted('weekday'):
                label = weekday_labels.get(line.weekday, '')
                if line.is_closed:
                    parts.append(_("%s : Fermé") % label)
                else:
                    parts.append("%s : %s - %s" % (
                        label,
                        self._float_to_hhmm(line.opening_time),
                        self._float_to_hhmm(line.closing_time),
                    ))
            rec.opening_hours_display = " | ".join(parts)

    @staticmethod
    def _float_to_hhmm(value):
        hours = int(value)
        minutes = round((value - hours) * 60)
        if minutes == 60:
            hours += 1
            minutes = 0
        return "%02d:%02d" % (hours, minutes)

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.state_id and self.state_id.country_id != self.country_id:
            self.state_id = False

    def action_generate_default_hours(self):
        """Génère automatiquement les 7 jours de la semaine avec des horaires
        par défaut, uniquement pour les jours qui n'ont pas encore de ligne.
        Permet de démarrer vite, puis d'ajuster chaque jour via le sélecteur
        d'heure."""
        Hours = self.env['adk.gym.salle.hours']
        for rec in self:
            existing_days = set(rec.hours_ids.mapped('weekday'))
            to_create = []
            for weekday, is_closed, opening, closing in DEFAULT_WEEK_HOURS:
                if weekday in existing_days:
                    continue
                to_create.append({
                    'salle_id': rec.id,
                    'weekday': weekday,
                    'is_closed': is_closed,
                    'opening_time': opening,
                    'closing_time': closing,
                })
            if to_create:
                Hours.create(to_create)
        return True

    def action_view_members(self):
        self.ensure_one()
        return {
            'name': _('Membres - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'adk.gym.member',
            'view_mode': 'kanban,list,form',
            'domain': [('salle_id', '=', self.id)],
        }
