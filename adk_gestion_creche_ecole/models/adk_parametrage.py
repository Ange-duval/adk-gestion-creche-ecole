# -*- coding: utf-8 -*-
from datetime import date

from odoo import api, fields, models


class AdkAnneeScolaire(models.Model):
    _name = 'adk.annee.scolaire'
    _description = "Année académique"
    _order = 'date_debut desc, name desc'

    name = fields.Char(string="Année académique", required=True, help="Ex : 2025-2026")
    date_debut = fields.Date(string="Date de début")
    date_fin = fields.Date(string="Date de fin")
    active = fields.Boolean(default=True)
    courante = fields.Boolean(
        string="Année en cours",
        help="Utilisée par défaut lors de la création de nouvelles fiches. "
             "Une seule année peut être marquée comme courante à la fois.")

    _sql_constraints = [
        ('name_uniq', 'unique(name)', "Cette année académique existe déjà."),
    ]

    def _demarquer_autres_courantes(self):
        for rec in self:
            if rec.courante:
                self.search([('id', '!=', rec.id), ('courante', '=', True)]).write({'courante': False})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._demarquer_autres_courantes()
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get('courante'):
            self._demarquer_autres_courantes()
        return res

    @api.model
    def _get_or_create_courante(self):
        """Retourne l'année académique marquée comme courante, ou la crée si elle n'existe pas
        encore (calcul basé sur la date du jour : bascule le 1er août)."""
        courante = self.search([('courante', '=', True)], limit=1)
        if courante:
            return courante
        today = date.today()
        y = today.year
        name = f"{y}-{y + 1}" if today.month >= 8 else f"{y - 1}-{y}"
        existing = self.search([('name', '=', name)], limit=1)
        if existing:
            existing.courante = True
            return existing
        return self.create({'name': name, 'courante': True})


class AdkPeriode(models.Model):
    _name = 'adk.periode'
    _description = "Période d'évaluation (trimestre, semestre, ...)"
    _order = 'sequence, id'

    name = fields.Char(string="Nom", required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', "Cette période existe déjà."),
    ]


class AdkTypeEvaluation(models.Model):
    _name = 'adk.type.evaluation'
    _description = "Type d'évaluation"
    _order = 'sequence, id'

    name = fields.Char(string="Nom", required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', "Ce type d'évaluation existe déjà."),
    ]


class AdkNiveau(models.Model):
    _name = 'adk.niveau'
    _description = "Niveau scolaire"
    _order = 'sequence, id'

    name = fields.Char(string="Nom", required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', "Ce niveau existe déjà."),
    ]
