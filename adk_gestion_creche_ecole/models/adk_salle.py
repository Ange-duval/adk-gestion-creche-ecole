# -*- coding: utf-8 -*-
from odoo import fields, models


class AdkSalle(models.Model):
    _name = 'adk.salle'
    _description = "Salle de classe / Espace"
    _order = 'name'

    name = fields.Char(string="Nom de la salle", required=True)
    code = fields.Char(string="Code")
    active = fields.Boolean(default=True)

    batiment_id = fields.Many2one('adk.batiment', string="Bâtiment", required=True, ondelete='cascade')
    etage_id = fields.Many2one('adk.etage', string="Étage",
                                domain="[('batiment_id', '=', batiment_id)]")
    etablissement_id = fields.Many2one(related='batiment_id.etablissement_id', store=True,
                                        string="Établissement")

    capacite_max = fields.Integer(string="Capacité maximale d'accueil", required=True, default=20)

    statut = fields.Selection([
        ('operationnelle', 'Opérationnelle'),
        ('maintenance', 'En maintenance'),
        ('desinfection', 'Désinfectée'),
    ], string="Statut de disponibilité", default='operationnelle', required=True)

    type_salle = fields.Selection([
        ('classe', 'Salle de classe'),
        ('creche', 'Salle de crèche (sieste)'),
        ('sport', 'Salle de sport'),
        ('bibliotheque', 'Bibliothèque'),
        ('informatique', 'Salle informatique'),
        ('autre', 'Autre'),
    ], string="Type d'espace", default='classe')

    materiel_ids = fields.One2many('adk.salle.materiel', 'salle_id', string="Matériel fixe")
    session_cours_ids = fields.One2many('adk.session.cours', 'salle_id', string="Sessions de cours")
    emploi_temps_ids = fields.One2many('adk.emploi.temps', 'salle_id', string="Créneaux planifiés")


class AdkSalleMateriel(models.Model):
    _name = 'adk.salle.materiel'
    _description = "Matériel fixe de la salle"

    name = fields.Char(string="Désignation", required=True)
    salle_id = fields.Many2one('adk.salle', string="Salle", required=True, ondelete='cascade')
    quantite = fields.Integer(string="Quantité", default=1)
    etat = fields.Selection([
        ('bon', 'Bon état'),
        ('use', 'Usé'),
        ('hs', 'Hors service'),
    ], string="État", default='bon')
