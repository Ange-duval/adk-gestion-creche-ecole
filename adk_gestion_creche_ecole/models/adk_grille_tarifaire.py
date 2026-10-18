# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AdkGrilleTarifaire(models.Model):
    _name = 'adk.grille.tarifaire'
    _description = "Grille tarifaire de scolarité"
    _order = 'annee_scolaire_id desc, name'

    name = fields.Char(string="Nom de la grille", required=True)
    code = fields.Char(string="Code")
    active = fields.Boolean(default=True)
    annee_scolaire_id = fields.Many2one(
        'adk.annee.scolaire', string="Année académique", required=True,
        default=lambda self: self.env['adk.annee.scolaire']._get_or_create_courante())
    niveau_id = fields.Many2one('adk.niveau', string="Niveau concerné",
                                help="Facultatif : informatif, pour retrouver la grille par niveau.")
    periodicite = fields.Selection([
        ('annuelle', 'Annuelle'),
        ('semestrielle', 'Semestrielle'),
        ('trimestrielle', 'Trimestrielle'),
        ('bimensuelle', 'Bimensuelle'),
        ('mensuelle', 'Mensuelle'),
        ('hebdomadaire', 'Hebdomadaire'),
        ('journaliere', 'Journalière'),
        ('autre', 'Autre'),
    ], string="Périodicité", default='annuelle', required=True,
        help="Utilisée par les rapports : la périodicité vient de cette configuration, "
             "jamais déduite du nom de la grille.")
    company_id = fields.Many2one('res.company', string="Société", default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    ligne_ids = fields.One2many('adk.grille.tarifaire.ligne', 'grille_id', string="Rubriques facturées", copy=True)
    tranche_ids = fields.One2many('adk.grille.tarifaire.tranche', 'grille_id', string="Échéancier (tranches)", copy=True)
    montant_total = fields.Monetary(string="Total de la grille", compute='_compute_total',
                                    store=True, currency_field='currency_id')
    nb_dossiers = fields.Integer(string="Dossiers", compute='_compute_nb_dossiers')

    @api.depends('ligne_ids.montant')
    def _compute_total(self):
        for rec in self:
            rec.montant_total = sum(rec.ligne_ids.mapped('montant'))

    def _compute_nb_dossiers(self):
        data = self.env['adk.dossier.scolarite']._read_group(
            [('grille_id', 'in', self.ids)], ['grille_id'], ['__count'])
        counts = {g.id: c for g, c in data}
        for rec in self:
            rec.nb_dossiers = counts.get(rec.id, 0)

    @api.constrains('tranche_ids')
    def _check_tranches(self):
        for rec in self:
            if rec.tranche_ids and abs(sum(rec.tranche_ids.mapped('pourcentage')) - 100.0) > 0.01:
                raise ValidationError(
                    "Le total des tranches de la grille « %s » doit faire 100 %%." % rec.name)

    def action_voir_dossiers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': "Dossiers - %s" % self.name,
            'res_model': 'adk.dossier.scolarite',
            'view_mode': 'list,form',
            'domain': [('grille_id', '=', self.id)],
        }


class AdkGrilleTarifaireLigne(models.Model):
    _name = 'adk.grille.tarifaire.ligne'
    _description = "Rubrique d'une grille tarifaire"
    _order = 'sequence, id'

    grille_id = fields.Many2one('adk.grille.tarifaire', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Libellé", required=True)
    product_id = fields.Many2one('product.product', string="Article (optionnel)",
                                 help="Si renseigné, le compte de produit et les taxes de l'article sont utilisés sur la facture.")
    montant = fields.Monetary(string="Montant", required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='grille_id.currency_id', readonly=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if not self.name:
                self.name = self.product_id.display_name
            if not self.montant:
                self.montant = self.product_id.lst_price


class AdkGrilleTarifaireTranche(models.Model):
    _name = 'adk.grille.tarifaire.tranche'
    _description = "Tranche de paiement d'une grille tarifaire"
    _order = 'sequence, id'

    grille_id = fields.Many2one('adk.grille.tarifaire', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Intitulé", required=True, help="Ex : 1re tranche, Inscription, Septembre...")
    pourcentage = fields.Float(string="Part (%)", required=True)
    delai_jours = fields.Integer(string="Échéance (jours après la facture)", default=0)
    montant = fields.Monetary(string="Montant", compute='_compute_montant', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='grille_id.currency_id', readonly=True)

    @api.depends('pourcentage', 'grille_id.montant_total')
    def _compute_montant(self):
        for rec in self:
            rec.montant = rec.grille_id.montant_total * rec.pourcentage / 100.0
