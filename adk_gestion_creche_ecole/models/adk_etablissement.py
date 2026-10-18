# -*- coding: utf-8 -*-
import pytz

from odoo import api, fields, models


def _adk_tz_get():
    """Liste des fuseaux horaires disponibles (indépendante de l'API interne d'Odoo,
    qui ne fournit pas fields._tz_get)."""
    return [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]


class AdkEtablissement(models.Model):
    _name = 'adk.etablissement'
    _description = "Établissement / Campus"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string="Nom de l'établissement", required=True, tracking=True)
    code = fields.Char(string="Code", required=True, copy=False)
    active = fields.Boolean(default=True)
    logo = fields.Image(string="Logo")
    company_id = fields.Many2one('res.company', string="Société", required=True,
                                  default=lambda self: self.env.company)
    directeur_id = fields.Many2one('hr.employee', string="Directeur responsable")

    # Localisation
    street = fields.Char(string="Adresse")
    street2 = fields.Char(string="Adresse (suite)")
    city = fields.Char(string="Ville")
    zip = fields.Char(string="Code postal")
    country_id = fields.Many2one('res.country', string="Pays")

    # Paramétrage général
    tz = fields.Selection(lambda self: _adk_tz_get(), string="Fuseau horaire",
                           default=lambda self: self.env.user.tz or 'UTC')
    currency_id = fields.Many2one('res.currency', string="Devise",
                                   default=lambda self: self.env.company.currency_id)
    journal_id = fields.Many2one('account.journal', string="Journal de facturation scolarité")

    batiment_ids = fields.One2many('adk.batiment', 'etablissement_id', string="Bâtiments")
    classe_ids = fields.One2many('adk.classe', 'etablissement_id', string="Classes")
    eleve_ids = fields.One2many('adk.eleve', 'etablissement_id', string="Élèves")
    pause_ids = fields.One2many('adk.pause', 'etablissement_id', string="Pauses institutionnelles")

    nb_batiments = fields.Integer(string="Nb bâtiments", compute='_compute_stats')
    nb_salles = fields.Integer(string="Nb salles", compute='_compute_stats')
    nb_classes = fields.Integer(string="Nb classes", compute='_compute_stats')
    nb_eleves = fields.Integer(string="Nb élèves", compute='_compute_stats')

    _sql_constraints = [
        ('code_uniq', 'unique(code, company_id)', "Le code de l'établissement doit être unique par société !"),
    ]

    @api.depends('batiment_ids', 'classe_ids', 'eleve_ids')
    def _compute_stats(self):
        for rec in self:
            rec.nb_batiments = len(rec.batiment_ids)
            rec.nb_salles = len(rec.batiment_ids.mapped('salle_ids'))
            rec.nb_classes = len(rec.classe_ids)
            rec.nb_eleves = len(rec.eleve_ids)
