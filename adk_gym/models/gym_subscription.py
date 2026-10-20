# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date
from odoo.exceptions import UserError, ValidationError

class GymSubscription(models.Model):
    _name = 'adk.gym.subscription'
    _description = 'Abonnement Gym'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date_start desc'

    # ── Référence
    name = fields.Char(string="Référence", required=True, copy=False, readonly=True,
                       default=lambda self: _('Nouveau'), tracking=True)
    
    # ── Liens principaux
    member_id = fields.Many2one('adk.gym.member', string="Membre", required=True, tracking=True, ondelete='restrict')
    coach_id = fields.Many2one('adk.gym.coach', string="Coach Responsable", tracking=True)
    discipline_ids = fields.Many2many(
        'adk.gym.activity', 'adk_gym_subscription_activity_rel', 'subscription_id', 'activity_id',
        string="Disciplines", tracking=True)
    salle_id = fields.Many2one('adk.gym.salle', string="Salle", tracking=True)

    # ── Type & Dates
    type = fields.Selection([
        ('daily', 'Journalier'),
        ('monthly', 'Mensuel'),
        ('quarterly', 'Trimestriel'),
        ('annual', 'Annuel'),
        ('special', 'Spécial')
    ], string="Type", default='monthly', required=True, tracking=True)
    date_start = fields.Date(string="Date Début", default=fields.Date.today, required=True, tracking=True)
    date_end = fields.Date(string="Date Fin", compute="_compute_date_end", store=True, readonly=False, tracking=True)

    # ── Tarification
    price = fields.Float(string="Prix Abonnement", compute="_compute_price", store=True, readonly=False, tracking=True)
    discount = fields.Float(string="Remise (%)", default=0.0, tracking=True)
    price_after_discount = fields.Float(string="Prix après remise", compute="_compute_price_after_discount", store=True)
    product_line_ids = fields.One2many('adk.gym.subscription.line', 'subscription_id', string="Produits Additionnels")
    total_amount = fields.Float(string="Total à Payer", compute="_compute_total_amount", store=True, tracking=True)

    # ── État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('active', 'Actif'),
        ('expired', 'Expiré'),
        ('cancelled', 'Annulé')
    ], string="État", default='draft', required=True, tracking=True, index=True)

    # ── Facturation
    invoice_id = fields.Many2one('account.move', string="Facture liée", readonly=True, copy=False)
    invoice_state = fields.Selection(related='invoice_id.payment_state', string="Statut Paiement", readonly=True)

    # ── Champs techniques
    notes = fields.Text(string="Notes / Remarques")
    days_remaining = fields.Integer(string="Jours restants", compute="_compute_days_remaining")
    is_expired = fields.Boolean(string="Expiré", compute="_compute_days_remaining", store=True)
    color = fields.Integer(string="Couleur Kanban", compute="_compute_color")

    # Champ technique (vue uniquement) : le prix et la remise ne doivent pouvoir
    # être modifiés à la main que par un Responsable ou un Administrateur Gym.
    # Un Utilisateur Gym (accueil) voit le tarif standard mais ne peut pas
    # accorder de remise ni surcharger le prix calculé automatiquement.
    is_gym_manager = fields.Boolean(string="Est responsable Gym", compute="_compute_is_gym_manager")

    def _compute_is_gym_manager(self):
        is_manager = self.env.user.has_group('adk_gym.group_gym_manager')
        for rec in self:
            rec.is_gym_manager = is_manager

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('adk.gym.subscription') or _('Nouveau')
        return super().create(vals_list)

    @api.depends('type', 'date_start')
    def _compute_date_end(self):
        from datetime import timedelta
        DURATIONS = {'daily': 1, 'monthly': 30, 'quarterly': 90, 'annual': 365, 'special': 0}
        for rec in self:
            if rec.date_start and rec.type:
                days = DURATIONS.get(rec.type, 30)
                if days > 0:
                    rec.date_end = rec.date_start + timedelta(days=days)
                else:
                    rec.date_end = rec.date_start
            else:
                rec.date_end = False

    @api.depends('type')
    def _compute_price(self):
        PRICES = {'daily': 10000.0, 'monthly': 60000.0, 'quarterly': 150000.0, 'annual': 500000.0, 'special': 0.0}
        for rec in self:
            rec.price = PRICES.get(rec.type, 0.0)

    @api.depends('price', 'discount')
    def _compute_price_after_discount(self):
        for rec in self:
            disc = max(0.0, min(100.0, rec.discount))
            rec.price_after_discount = rec.price * (1 - disc / 100.0)

    @api.depends('price_after_discount', 'product_line_ids.subtotal')
    def _compute_total_amount(self):
        for rec in self:
            lines_total = sum(rec.product_line_ids.mapped('subtotal'))
            rec.total_amount = rec.price_after_discount + lines_total

    @api.depends('date_end', 'state')
    def _compute_days_remaining(self):
        today = date.today()
        for rec in self:
            if rec.date_end and rec.state == 'active':
                delta = (rec.date_end - today).days
                rec.days_remaining = max(0, delta)
                rec.is_expired = delta < 0
            else:
                rec.days_remaining = 0
                rec.is_expired = rec.state == 'expired'

    @api.depends('state', 'days_remaining')
    def _compute_color(self):
        for rec in self:
            if rec.state == 'active':
                rec.color = 10 if rec.days_remaining > 7 else 3
            elif rec.state == 'expired':
                rec.color = 1
            elif rec.state == 'cancelled':
                rec.color = 8
            else:
                rec.color = 0

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end < rec.date_start:
                raise ValidationError(_("La date de fin doit être après la date de début."))

    @api.constrains('discount')
    def _check_discount(self):
        for rec in self:
            if rec.discount < 0 or rec.discount > 100:
                raise ValidationError(_("La remise doit être entre 0 et 100%."))

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Seul un abonnement en brouillon peut être confirmé."))
            rec.write({'state': 'active'})
            rec.message_post(body=_("Abonnement confirmé et activé."), message_type='notification')

    def action_expire(self):
        for rec in self:
            rec.write({'state': 'expired'})

    def action_cancel(self):
        for rec in self:
            if rec.state == 'active':
                raise UserError(_("Veuillez d'abord expirer l'abonnement avant d'annuler."))
            rec.write({'state': 'cancelled'})

    def action_reset_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})

    def action_renew(self):
        self.ensure_one()
        return {
            'name': _("Renouveler l'abonnement"),
            'type': 'ir.actions.act_window',
            'res_model': 'adk.gym.subscription.renew.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_subscription_id': self.id,
                'default_member_id': self.member_id.id,
                'default_type': self.type,
                'default_coach_id': self.coach_id.id,
                'default_discipline_ids': [(6, 0, self.discipline_ids.ids)],
            },
        }

    def action_create_invoice(self):
        for rec in self:
            if not rec.member_id.partner_id:
                raise UserError(_("Veuillez lier le membre '%s' à un contact client avant de facturer.") % rec.member_id.name)
            if rec.invoice_id:
                raise UserError(_("Une facture existe déjà pour cet abonnement : %s") % rec.invoice_id.name)
            
            invoice_lines = [(0, 0, {
                'name': _("Abonnement %s - %s") % (
                    rec.get_type_label(),
                    ', '.join(rec.discipline_ids.mapped('name')) if rec.discipline_ids else _("Général")),
                'price_unit': rec.price_after_discount,
                'quantity': 1,
            })]
            for line in rec.product_line_ids:
                invoice_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.product_id.name,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                }))
                
            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': rec.member_id.partner_id.id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': invoice_lines,
                'narration': _('Abonnement Gym ADK - Réf: %s') % rec.name,
            })
            rec.invoice_id = invoice
            return {
                'name': _('Facture'),
                'view_mode': 'form',
                'res_model': 'account.move',
                'res_id': invoice.id,
                'type': 'ir.actions.act_window',
            }

    def action_view_invoice(self):
        self.ensure_one()
        return {
            'name': _('Facture'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'type': 'ir.actions.act_window',
        }

    def get_type_label(self):
        self.ensure_one()
        labels = {'daily': 'Journalier', 'monthly': 'Mensuel', 'quarterly': 'Trimestriel', 'annual': 'Annuel', 'special': 'Spécial'}
        return labels.get(self.type, self.type)

    @api.model
    def _cron_check_expiry(self):
        today = date.today()
        expired = self.search([('state', '=', 'active'), ('date_end', '<', today)])
        if expired:
            expired.write({'state': 'expired'})
            for sub in expired:
                sub.message_post(body=_("Abonnement expiré automatiquement."), message_type='notification')
        return True

class GymSubscriptionLine(models.Model):
    _name = 'adk.gym.subscription.line'
    _description = 'Ligne de produit abonnement'

    subscription_id = fields.Many2one('adk.gym.subscription', ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', string="Produit", required=True)
    quantity = fields.Float(string="Quantité", default=1.0)
    price_unit = fields.Float(string="Prix Unitaire", related='product_id.lst_price', readonly=False, store=True)
    subtotal = fields.Float(string="Sous-total", compute="_compute_subtotal", store=True)

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.quantity * rec.price_unit
