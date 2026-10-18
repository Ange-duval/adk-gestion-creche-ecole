# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_adk_fourniture = fields.Boolean(string="Article de librairie / fourniture scolaire")
    is_adk_facturable_parent = fields.Boolean(
        string="Facturable directement sur le compte des parents",
        help="Si coché, la vente de cet article pourra être ajoutée à la facturation "
             "mensuelle globale de l'élève (scolarité + repas + fournitures).")
    type_fourniture = fields.Selection([
        ('cahier', 'Cahiers / Papeterie'),
        ('stylo', 'Stylos / Écriture'),
        ('uniforme', 'Uniforme'),
        ('repas', 'Repas / Cantine'),
        ('autre', 'Autre'),
    ], string="Type de fourniture")
