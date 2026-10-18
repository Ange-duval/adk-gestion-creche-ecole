# -*- coding: utf-8 -*-
from odoo import fields, models


class AdkMatiere(models.Model):
    _name = 'adk.matiere'
    _description = "Matière (Catalogue de cours)"
    _order = 'name'

    name = fields.Char(string="Nom de la matière", required=True)
    code = fields.Char(string="Code")
    active = fields.Boolean(default=True)
    coefficient = fields.Float(string="Coefficient (examens)", default=1.0)
    objectifs_pedagogiques = fields.Html(string="Objectifs pédagogiques")
    volume_horaire_annuel = fields.Float(string="Volume horaire total requis (h/an)")
    couleur = fields.Integer(string="Couleur (planning)")

    session_ids = fields.One2many('adk.session.cours', 'matiere_id', string="Sessions de cours")
    enseignant_ids = fields.Many2many(
        'hr.employee', 'adk_matiere_enseignant_rel', 'matiere_id', 'employee_id',
        string="Enseignants habilités",
        help="Enseignants ayant la compétence pour dispenser cette matière.")
