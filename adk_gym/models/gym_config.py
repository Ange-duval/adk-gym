# -*- coding: utf-8 -*-
from odoo import models, fields, api

class GymActivity(models.Model):
    _name = 'adk.gym.activity'
    _description = 'Discipline / Activité'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _order = 'name asc'

    name = fields.Char(string="Nom", required=True, tracking=True)
    description = fields.Text(string="Description")
    duration_minutes = fields.Integer(string="Durée par séance (min)", default=60)
    max_participants = fields.Integer(string="Participants max")
    default_price = fields.Float(string="Prix par défaut")
    equipment_ids = fields.Many2many('adk.gym.equipment', string="Équipements requis")
    active = fields.Boolean(default=True)
    subscription_ids = fields.Many2many(
        'adk.gym.subscription', 'adk_gym_subscription_activity_rel', 'activity_id', 'subscription_id',
        string="Abonnements liés")
    subscription_count = fields.Integer(string="Nb Abonnements", compute="_compute_subscription_count", store=True)

    @api.depends('subscription_ids')
    def _compute_subscription_count(self):
        for rec in self:
            rec.subscription_count = len(rec.subscription_ids)


class GymEquipment(models.Model):
    """Article / type d'équipement (ex: 'Masse', 'Tapis de course', ...).

    IMPORTANT (correction demandée) : un article est désormais créé UNE SEULE FOIS,
    quel que soit le nombre de salles qui l'utilisent. On ne recrée plus une fiche
    'Masse' par salle : on crée l'article 'Masse' une fois, puis on renseigne, dans
    l'onglet 'Présence par salle', la liste des salles qui en disposent (avec, pour
    chacune, sa propre quantité, son propre état et éventuellement son propre
    identifiant/référence unique). Le détail par salle est porté par le modèle
    'adk.gym.equipment.stock' (voir plus bas).
    """
    _name = 'adk.gym.equipment'
    _description = 'Équipement'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _order = 'name asc'

    name = fields.Char(string="Désignation", required=True, tracking=True)
    brand = fields.Char(string="Marque")
    notes = fields.Text(string="Observations")
    active = fields.Boolean(default=True)

    # ── Présence dans les salles (une ligne = une salle qui possède cet article)
    stock_ids = fields.One2many('adk.gym.equipment.stock', 'equipment_id', string="Présence par salle")
    salle_ids = fields.Many2many(
        'adk.gym.salle', string="Salles utilisatrices",
        compute="_compute_salle_ids", store=True)
    salle_count = fields.Integer(string="Nb Salles", compute="_compute_stock_stats", store=True)
    total_quantity = fields.Integer(string="Quantité totale", compute="_compute_stock_stats", store=True)
    has_unusable_stock = fields.Boolean(string="Alerte état", compute="_compute_stock_stats", store=True)

    @api.depends('stock_ids.salle_id')
    def _compute_salle_ids(self):
        for rec in self:
            rec.salle_ids = rec.stock_ids.mapped('salle_id')

    def action_view_stock_movements(self):
        """Ouvre l'état de stock (mouvements) filtré sur cet article, toutes salles
        confondues : permet de voir en un coup d'œil les entrées/sorties enregistrées
        pour chacune des salles qui utilisent cet article."""
        self.ensure_one()
        return {
            'name': 'Mouvements - %s' % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'adk.gym.equipment.movement',
            'view_mode': 'list,pivot',
            'domain': [('equipment_id', '=', self.id)],
            'context': {'search_default_group_by_salle': 1},
        }

    @api.depends('stock_ids.salle_id', 'stock_ids.quantity', 'stock_ids.state')
    def _compute_stock_stats(self):
        for rec in self:
            rec.salle_count = len(rec.stock_ids.mapped('salle_id'))
            rec.total_quantity = sum(rec.stock_ids.mapped('quantity'))
            rec.has_unusable_stock = any(s.state in ('maintenance', 'damaged') for s in rec.stock_ids)


class GymEquipmentStock(models.Model):
    """Présence d'un article (adk.gym.equipment) dans une salle donnée.

    Une seule ligne par couple (article, salle) : on ne duplique jamais l'article,
    on renseigne simplement ici la quantité, l'état et - si besoin - un identifiant
    unique propre à cette salle (ex: étiquette d'inventaire). C'est cette ligne qui
    porte désormais la quantité, l'état et les mouvements de stock, puisque deux
    salles différentes peuvent avoir des quantités / états différents pour le même
    article (ex: 10 masses en bon état salle A, 15 masses dont 2 en maintenance
    salle B).
    """
    _name = 'adk.gym.equipment.stock'
    _description = 'Présence Équipement / Salle'
    _order = 'equipment_id asc, salle_id asc'
    _rec_name = 'equipment_id'

    equipment_id = fields.Many2one('adk.gym.equipment', string="Article", required=True,
                                    ondelete='cascade', index=True)
    salle_id = fields.Many2one('adk.gym.salle', string="Salle / Club", required=True,
                                ondelete='cascade', index=True)
    code = fields.Char(string="Identifiant / Référence (pour cette salle)",
                        help="Identifiant unique optionnel (étiquette, code inventaire...) "
                             "propre à la présence de cet article dans cette salle.")
    quantity = fields.Integer(string="Quantité en stock", default=1)
    purchase_date = fields.Date(string="Date d'achat")
    purchase_price = fields.Float(string="Prix d'achat")
    state = fields.Selection([
        ('good', 'Bon état'),
        ('maintenance', 'En Maintenance'),
        ('damaged', 'Endommagé'),
        ('retired', 'Retiré')
    ], string="État", default='good')
    is_unusable = fields.Boolean(string="Inutilisable", compute="_compute_is_unusable", store=True)
    movement_ids = fields.One2many('adk.gym.equipment.movement', 'stock_id', string="Mouvements de stock")
    movement_count = fields.Integer(string="Nb Mouvements", compute="_compute_movement_count")
    notes = fields.Text(string="Observations")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('equipment_salle_unique', 'UNIQUE(equipment_id, salle_id)',
         "Cet article est déjà présent dans cette salle : modifiez la ligne existante "
         "au lieu d'en créer une nouvelle (mettez simplement à jour sa quantité)."),
        ('code_unique', 'UNIQUE(code)',
         "Cet identifiant / cette référence est déjà utilisé(e) par une autre présence d'article."),
    ]

    @api.depends('state')
    def _compute_is_unusable(self):
        for rec in self:
            rec.is_unusable = rec.state in ('maintenance', 'damaged', 'retired')

    @api.depends('movement_ids')
    def _compute_movement_count(self):
        for rec in self:
            rec.movement_count = len(rec.movement_ids)

    def action_stock_in(self):
        """Ouvre une fenêtre rapide pour enregistrer une ENTRÉE de stock
        (réception, achat, retour d'un outil réparé, etc.) pour CETTE salle."""
        self.ensure_one()
        return {
            'name': 'Entrée de stock',
            'type': 'ir.actions.act_window',
            'res_model': 'adk.gym.equipment.movement',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_stock_id': self.id,
                'default_movement_type': 'in',
                'default_reason': 'purchase',
            },
        }

    def action_stock_out(self):
        """Ouvre une fenêtre rapide pour enregistrer une SORTIE de stock pour CETTE
        salle. Disponible dès que l'outil est en Maintenance / Endommagé / Retiré,
        c'est-à-dire inutilisable."""
        self.ensure_one()
        return {
            'name': 'Sortie de stock',
            'type': 'ir.actions.act_window',
            'res_model': 'adk.gym.equipment.movement',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_stock_id': self.id,
                'default_movement_type': 'out',
                'default_reason': 'damaged' if self.state == 'damaged' else (
                    'retired' if self.state == 'retired' else 'other'),
            },
        }


class GymEquipmentMovement(models.Model):
    _name = 'adk.gym.equipment.movement'
    _description = 'Mouvement de Stock Outils'
    _order = 'date desc, id desc'

    stock_id = fields.Many2one('adk.gym.equipment.stock', string="Présence Article / Salle",
                                required=True, ondelete='cascade')
    equipment_id = fields.Many2one(related='stock_id.equipment_id', string="Outil / Équipement", store=True)
    equipment_state = fields.Selection(related='stock_id.state', string="État de l'outil", store=True)
    salle_id = fields.Many2one(related='stock_id.salle_id', string="Salle / Club", store=True)
    date = fields.Date(string="Date", default=fields.Date.today, required=True)
    movement_type = fields.Selection([
        ('in', 'Entrée'),
        ('out', 'Sortie'),
    ], string="Type de mouvement", required=True, default='in')
    quantity = fields.Integer(string="Quantité", required=True, default=1)
    reason = fields.Selection([
        ('purchase', 'Achat / Réception'),
        ('return', 'Retour en stock'),
        ('damaged', 'Mise hors service (endommagé)'),
        ('lost', 'Perte / Vol'),
        ('retired', 'Retrait définitif'),
        ('other', 'Autre'),
    ], string="Motif", default='purchase')
    notes = fields.Char(string="Note")

    _sql_constraints = [
        ('quantity_positive', 'CHECK(quantity > 0)', 'La quantité du mouvement doit être supérieure à 0.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        movements = super().create(vals_list)
        for move in movements:
            delta = move.quantity if move.movement_type == 'in' else -move.quantity
            new_qty = max(move.stock_id.quantity + delta, 0)
            move.stock_id.quantity = new_qty
        return movements

    def unlink(self):
        for move in self:
            # On annule l'effet du mouvement supprimé pour garder le stock cohérent.
            delta = -move.quantity if move.movement_type == 'in' else move.quantity
            new_qty = max(move.stock_id.quantity + delta, 0)
            move.stock_id.quantity = new_qty
        return super().unlink()


class GymObjective(models.Model):
    _name = 'adk.gym.objective'
    _description = 'Objectif Sportif'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    name = fields.Char(string="Objectif", required=True, tracking=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(default=True)


class GymPracticeLevel(models.Model):
    _name = 'adk.gym.practice.level'
    _description = 'Niveau de pratique'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence asc, name asc'

    name = fields.Char(string="Niveau", required=True, tracking=True)
    sequence = fields.Integer(string="Ordre", default=10)
    description = fields.Text(string="Description")
    active = fields.Boolean(default=True)
