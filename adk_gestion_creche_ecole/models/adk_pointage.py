# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AdkPointage(models.Model):
    _name = 'adk.pointage'
    _description = "Pointage par badge QR Code (entrée / sortie)"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'heure_pointage desc'

    badge_id = fields.Many2one('adk.badge', string="Badge scanné", required=True)
    eleve_id = fields.Many2one('adk.eleve', string="Élève concerné")
    parent_id = fields.Many2one('res.partner', string="Parent accompagnant")
    employee_id = fields.Many2one('hr.employee', string="Membre du personnel scanné")

    intendant_id = fields.Many2one('hr.employee', string="Scanné par (intendant)",
                                    default=lambda self: self.env.user.employee_id.id
                                    if self.env.user.employee_id else False)

    heure_pointage = fields.Datetime(string="Heure de pointage", default=fields.Datetime.now, required=True, tracking=True)
    type_mouvement = fields.Selection([
        ('entree', 'Entrée'),
        ('sortie', 'Sortie'),
    ], string="Mouvement", default='entree', required=True, tracking=True)

    correspondance_validee = fields.Boolean(string="Correspondance familiale validée",
                                             compute='_compute_correspondance', store=True)

    @api.depends('eleve_id', 'parent_id')
    def _compute_correspondance(self):
        for rec in self:
            if rec.eleve_id and rec.parent_id:
                rec.correspondance_validee = rec.parent_id in rec.eleve_id.parent_ids
            else:
                rec.correspondance_validee = True

    @api.constrains('eleve_id', 'parent_id')
    def _check_correspondance(self):
        for rec in self:
            if rec.eleve_id and rec.parent_id and rec.parent_id not in rec.eleve_id.parent_ids:
                raise ValidationError(
                    "Le système n'a pas pu valider la correspondance familiale entre %s et %s. "
                    "Accès refusé." % (rec.parent_id.name, rec.eleve_id.name))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.eleve_id and rec.type_mouvement == 'entree':
                self.env['adk.presence'].create({
                    'eleve_id': rec.eleve_id.id,
                    'date': fields.Date.context_today(self),
                    'statut': 'present',
                    'mode_saisie': 'badge',
                })
        return records
