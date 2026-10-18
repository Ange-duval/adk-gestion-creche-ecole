# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class AdkWizardSaisieNotes(models.TransientModel):
    _name = 'adk.wizard.saisie.notes'
    _description = "Assistant : Saisie rapide des notes en grille"

    classe_id = fields.Many2one('adk.classe', string="Classe", required=True)
    matiere_id = fields.Many2one('adk.matiere', string="Matière", required=True)
    enseignant_id = fields.Many2one('hr.employee', string="Enseignant", required=True)
    periode_id = fields.Many2one(
        'adk.periode', string="Période", required=True,
        default=lambda self: self.env['adk.periode'].search([], limit=1, order='sequence'))
    type_evaluation_id = fields.Many2one(
        'adk.type.evaluation', string="Type d'évaluation",
        default=lambda self: self.env['adk.type.evaluation'].search([], limit=1, order='sequence'))
    date_evaluation = fields.Date(string="Date de l'évaluation", default=fields.Date.context_today)
    note_sur = fields.Float(string="Note sur", default=20.0)

    ligne_ids = fields.One2many('adk.wizard.saisie.notes.ligne', 'wizard_id', string="Grille de saisie")

    @api.onchange('classe_id')
    def _onchange_classe_id(self):
        lignes = []
        for eleve in self.classe_id.eleve_ids:
            lignes.append((0, 0, {'eleve_id': eleve.id}))
        self.ligne_ids = lignes

    def action_enregistrer(self):
        self.ensure_one()
        if not self.ligne_ids:
            raise UserError("La grille de saisie est vide. Sélectionnez d'abord une classe.")
        Note = self.env['adk.note']
        notes = Note
        for ligne in self.ligne_ids.filtered(lambda l: l.note_obtenue is not False):
            notes |= Note.create({
                'eleve_id': ligne.eleve_id.id,
                'matiere_id': self.matiere_id.id,
                'enseignant_id': self.enseignant_id.id,
                'periode_id': self.periode_id.id,
                'type_evaluation_id': self.type_evaluation_id.id,
                'date_evaluation': self.date_evaluation,
                'note_obtenue': ligne.note_obtenue,
                'note_sur': self.note_sur,
                'appreciation': ligne.appreciation,
            })
        return {
            'type': 'ir.actions.act_window',
            'name': "Notes saisies",
            'res_model': 'adk.note',
            'view_mode': 'list,form',
            'domain': [('id', 'in', notes.ids)],
        }


class AdkWizardSaisieNotesLigne(models.TransientModel):
    _name = 'adk.wizard.saisie.notes.ligne'
    _description = "Ligne de saisie rapide des notes"

    wizard_id = fields.Many2one('adk.wizard.saisie.notes', string="Assistant", ondelete='cascade')
    eleve_id = fields.Many2one('adk.eleve', string="Élève", required=True)
    note_obtenue = fields.Float(string="Note obtenue")
    appreciation = fields.Char(string="Appréciation")
