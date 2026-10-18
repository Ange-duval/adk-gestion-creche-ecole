# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AdkClasse(models.Model):
    _name = 'adk.classe'
    _description = "Classe / Groupe d'élèves"
    _order = 'name'

    name = fields.Char(string="Nom de la classe", required=True)
    code = fields.Char(string="Code")
    active = fields.Boolean(default=True)

    etablissement_id = fields.Many2one('adk.etablissement', string="Établissement",
                                        required=True, ondelete='cascade')
    annee_scolaire_id = fields.Many2one(
        'adk.annee.scolaire', string="Année académique", required=True,
        default=lambda self: self.env['adk.annee.scolaire']._get_or_create_courante())
    niveau_id = fields.Many2one('adk.niveau', string="Niveau", required=True)

    titulaire_id = fields.Many2one('hr.employee', string="Enseignant titulaire")
    salle_reference_id = fields.Many2one('adk.salle', string="Salle de référence")

    eleve_ids = fields.One2many('adk.eleve', 'classe_id', string="Élèves")
    session_cours_ids = fields.One2many('adk.session.cours', 'classe_id', string="Sessions de cours")

    effectif = fields.Integer(string="Effectif actuel", compute='_compute_effectif', store=True)
    effectif_max = fields.Integer(string="Effectif maximum", default=25)

    @api.depends('eleve_ids')
    def _compute_effectif(self):
        for rec in self:
            rec.effectif = len(rec.eleve_ids)

    @api.constrains('effectif', 'effectif_max')
    def _check_effectif_max(self):
        for rec in self:
            if rec.effectif_max and rec.effectif > rec.effectif_max:
                raise ValidationError(
                    "L'effectif de la classe %s (%s élèves) dépasse l'effectif maximum autorisé (%s) !"
                    % (rec.name, rec.effectif, rec.effectif_max))
