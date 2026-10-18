# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AdkNote(models.Model):
    _name = 'adk.note'
    _description = "Note d'un élève dans une matière"
    _order = 'date_evaluation desc'

    eleve_id = fields.Many2one('adk.eleve', string="Élève", required=True, ondelete='cascade')
    classe_id = fields.Many2one('adk.classe', string="Classe", related='eleve_id.classe_id', store=True)
    matiere_id = fields.Many2one('adk.matiere', string="Matière", required=True)
    enseignant_id = fields.Many2one('hr.employee', string="Enseignant", required=True)

    periode_id = fields.Many2one(
        'adk.periode', string="Période", required=True,
        default=lambda self: self.env['adk.periode'].search([], limit=1, order='sequence'))

    type_evaluation_id = fields.Many2one(
        'adk.type.evaluation', string="Type d'évaluation",
        default=lambda self: self.env['adk.type.evaluation'].search([], limit=1, order='sequence'))

    date_evaluation = fields.Date(string="Date de l'évaluation", default=fields.Date.context_today)
    note_obtenue = fields.Float(string="Note obtenue", required=True)
    note_sur = fields.Float(string="Note sur", required=True, default=20.0)
    note_ponderee_20 = fields.Float(string="Note ramenée sur 20", compute='_compute_note_20', store=True)
    appreciation = fields.Char(string="Appréciation courte")

    annee_scolaire_id = fields.Many2one(
        'adk.annee.scolaire', related='eleve_id.annee_scolaire_id', store=True, readonly=False,
        string="Année académique",
        help="Pré-remplie depuis l'élève, mais modifiable pour rattraper une saisie "
             "concernant une année académique antérieure.")

    @api.depends('note_obtenue', 'note_sur')
    def _compute_note_20(self):
        for rec in self:
            rec.note_ponderee_20 = (rec.note_obtenue / rec.note_sur * 20.0) if rec.note_sur else 0.0

    @api.constrains('note_obtenue', 'note_sur')
    def _check_note(self):
        for rec in self:
            if rec.note_sur <= 0:
                raise ValidationError("Le barème de la note ('sur X') doit être strictement positif.")
            if rec.note_obtenue < 0 or rec.note_obtenue > rec.note_sur:
                raise ValidationError("La note obtenue doit être comprise entre 0 et %.2f." % rec.note_sur)
