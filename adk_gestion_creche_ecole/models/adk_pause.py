# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AdkPause(models.Model):
    _name = 'adk.pause'
    _description = "Pause / Repas / Sieste institutionnelle"
    _order = 'jour_semaine, heure_debut'

    name = fields.Char(string="Libellé", required=True)
    etablissement_id = fields.Many2one('adk.etablissement', string="Établissement",
                                        required=True, ondelete='cascade')
    type_pause = fields.Selection([
        ('recreation', 'Récréation'),
        ('repas', 'Pause déjeuner / Repas'),
        ('sieste', 'Sieste'),
        ('temps_mort', 'Temps mort'),
    ], string="Type", required=True, default='repas')

    jour_semaine = fields.Selection([
        ('0', 'Lundi'), ('1', 'Mardi'), ('2', 'Mercredi'),
        ('3', 'Jeudi'), ('4', 'Vendredi'), ('5', 'Samedi'), ('6', 'Dimanche'),
    ], string="Jour", required=True, default='0')

    heure_debut = fields.Float(string="Heure de début", required=True, default=12.0)
    heure_fin = fields.Float(string="Heure de fin", required=True, default=13.5)

    @api.constrains('heure_debut', 'heure_fin')
    def _check_heures(self):
        for rec in self:
            if rec.heure_debut >= rec.heure_fin:
                raise ValidationError("L'heure de début de la pause doit précéder l'heure de fin.")
