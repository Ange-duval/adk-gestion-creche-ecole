# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_adk_parent = fields.Boolean(string="Est un parent d'élève")
    eleve_ids = fields.Many2many('adk.eleve', 'adk_eleve_parent_rel', 'parent_id', 'eleve_id',
                                  string="Enfants inscrits")
    nb_enfants = fields.Integer(string="Nombre d'enfants", compute='_compute_nb_enfants')
    badge_ids = fields.One2many('adk.badge', 'parent_id', string="Badges")

    @api.depends('eleve_ids')
    def _compute_nb_enfants(self):
        for rec in self:
            rec.nb_enfants = len(rec.eleve_ids)

    def action_voir_fiches_enfants(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': "Fiches de mes enfants",
            'res_model': 'adk.eleve',
            'view_mode': 'kanban,list,form',
            'domain': [('id', 'in', self.eleve_ids.ids)],
        }
