# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AdkBatiment(models.Model):
    _name = 'adk.batiment'
    _description = "Bâtiment"
    _order = 'name'

    name = fields.Char(string="Nom du bâtiment", required=True)
    code = fields.Char(string="Code")
    active = fields.Boolean(default=True)

    etablissement_id = fields.Many2one('adk.etablissement', string="Établissement",
                                        required=True, ondelete='cascade')
    company_id = fields.Many2one(related='etablissement_id.company_id', store=True)

    # Coordonnées géographiques internes
    latitude = fields.Float(string="Latitude", digits=(10, 6))
    longitude = fields.Float(string="Longitude", digits=(10, 6))

    # Normes de sécurité
    issue_secours = fields.Boolean(string="Issue de secours conforme")
    conformite_pmr = fields.Boolean(string="Conforme PMR (Accès handicapés)")
    date_derniere_inspection = fields.Date(string="Date dernière inspection sécurité")
    notes_securite = fields.Text(string="Notes sur les normes de sécurité")

    etage_ids = fields.One2many('adk.etage', 'batiment_id', string="Étages")
    salle_ids = fields.One2many('adk.salle', 'batiment_id', string="Salles")
    nb_salles = fields.Integer(string="Nb salles", compute='_compute_nb_salles')

    @api.depends('salle_ids')
    def _compute_nb_salles(self):
        for rec in self:
            rec.nb_salles = len(rec.salle_ids)
