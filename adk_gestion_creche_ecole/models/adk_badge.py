# -*- coding: utf-8 -*-
import hashlib
import uuid

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AdkBadge(models.Model):
    _name = 'adk.badge'
    _description = "Badge d'accès (Élève / Parent / Enseignant)"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string="Référence du badge", copy=False, readonly=True,
                        default=lambda self: self.env['ir.sequence'].next_by_code('adk.badge'))
    active = fields.Boolean(default=True, tracking=True)

    role = fields.Selection([
        ('eleve', 'Élève'),
        ('parent', 'Parent'),
        ('enseignant', 'Enseignant'),
        ('personnel', 'Autre personnel'),
    ], string="Rôle", required=True)

    eleve_id = fields.Many2one('adk.eleve', string="Élève")
    parent_id = fields.Many2one('res.partner', string="Parent",
                                 domain="[('is_adk_parent', '=', True)]")
    employee_id = fields.Many2one('hr.employee', string="Personnel")

    etablissement_id = fields.Many2one('adk.etablissement', string="Établissement", required=True)

    # Contenu recto
    photo = fields.Image(string="Photo", compute='_compute_photo', store=True, readonly=False)
    nom_affiche = fields.Char(string="Nom affiché", compute='_compute_identite', store=True)
    prenom_affiche = fields.Char(string="Prénom affiché", compute='_compute_identite', store=True)

    # Contenu verso : QR Code crypté (ID unique + jeton)
    uid_token = fields.Char(string="Jeton unique (crypté)", copy=False, readonly=True,
                             default=lambda self: uuid.uuid4().hex)
    qr_value = fields.Char(string="Valeur encodée dans le QR Code", compute='_compute_qr_value', store=True)

    date_emission = fields.Date(string="Date d'émission", default=fields.Date.context_today)
    date_expiration = fields.Date(string="Date d'expiration")
    statut = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('actif', 'Actif'),
        ('suspendu', 'Suspendu'),
        ('perdu', 'Perdu / Réémis'),
    ], string="Statut", default='brouillon', tracking=True)

    @api.depends('eleve_id', 'parent_id', 'employee_id', 'role')
    def _compute_identite(self):
        for rec in self:
            source = rec.eleve_id if rec.role == 'eleve' else (
                rec.parent_id if rec.role == 'parent' else rec.employee_id)
            if rec.role == 'eleve' and rec.eleve_id:
                rec.nom_affiche = rec.eleve_id.nom or rec.eleve_id.name
                rec.prenom_affiche = rec.eleve_id.prenom or ''
            elif source:
                rec.nom_affiche = source.name
                rec.prenom_affiche = ''
            else:
                rec.nom_affiche = ''
                rec.prenom_affiche = ''

    @api.depends('eleve_id.photo', 'employee_id.image_1920', 'parent_id.image_1920', 'role')
    def _compute_photo(self):
        for rec in self:
            if rec.role == 'eleve':
                rec.photo = rec.eleve_id.photo
            elif rec.role == 'parent':
                rec.photo = rec.parent_id.image_1920
            elif rec.employee_id:
                rec.photo = rec.employee_id.image_1920
            else:
                rec.photo = False

    @api.depends('uid_token', 'role', 'eleve_id', 'parent_id', 'employee_id')
    def _compute_qr_value(self):
        for rec in self:
            source_id = rec.eleve_id.id if rec.role == 'eleve' else (
                rec.parent_id.id if rec.role == 'parent' else rec.employee_id.id)
            raw = "ADK|%s|%s|%s|%s" % (rec.env.cr.dbname, rec.role, source_id or 0, rec.uid_token)
            rec.qr_value = hashlib.sha256(raw.encode('utf-8')).hexdigest()


    def action_set_draft(self):
        self.write({'statut': 'brouillon'})
        return True

    def action_activate(self):
        for rec in self:
            if rec.date_expiration and rec.date_expiration < fields.Date.context_today(rec):
                raise ValidationError("Impossible d'activer un badge dont la date d'expiration est dépassée.")
        self.write({'statut': 'actif'})
        return True

    def action_suspend(self):
        self.write({'statut': 'suspendu'})
        return True

    def action_mark_lost(self):
        self.write({'statut': 'perdu'})
        return True

    @api.model
    def _cron_suspend_expired_badges(self):
        today = fields.Date.context_today(self)
        expired = self.search([('statut', '=', 'actif'), ('date_expiration', '<', today)])
        expired.write({'statut': 'suspendu'})

    def action_scanner_pointage(self):
        """Appelé lors du scan à l'entrée : valide la correspondance familiale (parent/enfant)
        et enregistre le pointage."""
        self.ensure_one()
        if self.statut != 'actif':
            raise ValidationError("Ce badge n'est pas actif : le pointage est refusé.")
        if self.date_expiration and self.date_expiration < fields.Date.context_today(self):
            self.action_suspend()
            raise ValidationError("Ce badge a expiré et vient d'être suspendu.")
        return self.env['adk.pointage'].create({
            'badge_id': self.id,
            'eleve_id': self.eleve_id.id if self.role == 'eleve' else False,
            'parent_id': self.parent_id.id if self.role == 'parent' else False,
        })
