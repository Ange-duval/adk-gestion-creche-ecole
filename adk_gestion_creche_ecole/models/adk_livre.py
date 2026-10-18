# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AdkLivre(models.Model):
    _name = 'adk.livre'
    _description = "Livre (Bibliothèque)"
    _order = 'name'

    name = fields.Char(string="Titre", required=True)
    auteur = fields.Char(string="Auteur")
    editeur = fields.Char(string="Éditeur")
    code_barre = fields.Char(string="Code-barres", copy=False)
    isbn = fields.Char(string="ISBN")
    categorie = fields.Selection([
        ('roman', 'Roman'),
        ('conte', 'Conte / Jeunesse'),
        ('scolaire', 'Manuel scolaire'),
        ('bd', 'Bande dessinée'),
        ('documentaire', 'Documentaire'),
    ], string="Catégorie")

    nb_exemplaires = fields.Integer(string="Nombre d'exemplaires", default=1)
    etablissement_id = fields.Many2one('adk.etablissement', string="Établissement")

    pret_ids = fields.One2many('adk.pret.livre', 'livre_id', string="Historique des prêts")
    nb_exemplaires_disponibles = fields.Integer(string="Exemplaires disponibles",
                                                 compute='_compute_disponibilite')
    statut_global = fields.Selection([
        ('disponible', 'Disponible'),
        ('emprunte', 'Tous exemplaires empruntés'),
    ], compute='_compute_disponibilite', string="Statut")

    @api.depends('pret_ids.statut', 'nb_exemplaires')
    def _compute_disponibilite(self):
        for rec in self:
            en_cours = len(rec.pret_ids.filtered(lambda p: p.statut in ('emprunte', 'retard')))
            rec.nb_exemplaires_disponibles = max(rec.nb_exemplaires - en_cours, 0)
            rec.statut_global = 'disponible' if rec.nb_exemplaires_disponibles > 0 else 'emprunte'


class AdkPretLivre(models.Model):
    _name = 'adk.pret.livre'
    _description = "Prêt de livre"
    _order = 'date_emprunt desc'

    livre_id = fields.Many2one('adk.livre', string="Livre", required=True, ondelete='cascade')
    eleve_id = fields.Many2one('adk.eleve', string="Élève emprunteur")
    employee_id = fields.Many2one('hr.employee', string="Membre du personnel emprunteur")

    date_emprunt = fields.Date(string="Date d'emprunt", default=fields.Date.context_today, required=True)
    date_retour_prevue = fields.Date(string="Date de retour prévue", required=True)
    date_retour_effective = fields.Date(string="Date de retour effective")

    statut = fields.Selection([
        ('disponible', 'Disponible'),
        ('emprunte', 'Emprunté'),
        ('retard', 'En retard'),
        ('perdu', 'Perdu'),
        ('retourne', 'Retourné'),
    ], string="Statut", default='emprunte', required=True)

    @api.constrains('eleve_id', 'employee_id')
    def _check_emprunteur(self):
        for rec in self:
            if not rec.eleve_id and not rec.employee_id:
                raise ValidationError("Veuillez indiquer un élève ou un membre du personnel emprunteur.")

    @api.model
    def _cron_marquer_retards(self):
        aujourdhui = fields.Date.context_today(self)
        retards = self.search([
            ('statut', '=', 'emprunte'),
            ('date_retour_prevue', '<', aujourdhui),
        ])
        retards.write({'statut': 'retard'})

    def action_marquer_retourne(self):
        self.write({'statut': 'retourne', 'date_retour_effective': fields.Date.context_today(self)})

    def action_marquer_perdu(self):
        self.write({'statut': 'perdu'})
