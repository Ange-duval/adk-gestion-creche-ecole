# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    adk_dossier_id = fields.Many2one('adk.dossier.scolarite', string="Dossier de scolarité",
                                     copy=False, index='btree_not_null', readonly=True)
    adk_eleve_id = fields.Many2one('adk.eleve', string="Élève", related='adk_dossier_id.eleve_id',
                                   store=True, readonly=True)
