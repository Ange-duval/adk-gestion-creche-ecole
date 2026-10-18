# -*- coding: utf-8 -*-
from odoo import fields, models


class AdkEtage(models.Model):
    _name = 'adk.etage'
    _description = "Étage"
    _order = 'niveau'

    name = fields.Char(string="Nom de l'étage", required=True)
    niveau = fields.Integer(string="Niveau (0 = Rez-de-chaussée)", default=0)
    batiment_id = fields.Many2one('adk.batiment', string="Bâtiment", required=True, ondelete='cascade')
    etablissement_id = fields.Many2one(related='batiment_id.etablissement_id', store=True,
                                        string="Établissement")
    salle_ids = fields.One2many('adk.salle', 'etage_id', string="Salles")
