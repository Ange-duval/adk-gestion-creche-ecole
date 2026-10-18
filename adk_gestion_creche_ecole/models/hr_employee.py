# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_adk_enseignant = fields.Boolean(string="Est enseignant / nounou")
    is_adk_intendant = fields.Boolean(string="Est intendant (économe / magasinier)")
    is_adk_bibliothecaire = fields.Boolean(string="Est bibliothécaire")

    matiere_competence_ids = fields.Many2many(
        'adk.matiere', 'adk_matiere_enseignant_rel', 'employee_id', 'matiere_id',
        string="Matières habilitées à enseigner")

    etablissement_ids = fields.Many2many('adk.etablissement', string="Établissements de rattachement")
    session_cours_ids = fields.One2many('adk.session.cours', 'enseignant_id', string="Cours dispensés")
    classe_titulaire_ids = fields.One2many('adk.classe', 'titulaire_id', string="Classes en titulariat")

    def action_enseignants_disponibles_remplacement(self, matiere_id, jour_semaine, heure_debut, heure_fin):
        """Retourne la liste des enseignants disponibles et compétents pour un remplacement,
        utilisée lorsqu'un congé est validé (hr_holidays) sur un enseignant planifié."""
        Employee = self.env['hr.employee']
        candidats = Employee.search([
            ('is_adk_enseignant', '=', True),
            ('matiere_competence_ids', '=', matiere_id),
        ])
        EmploiTemps = self.env['adk.emploi.temps']
        disponibles = Employee
        for c in candidats:
            conflit = EmploiTemps.search([
                ('enseignant_id', '=', c.id),
                ('jour_semaine', '=', jour_semaine),
                ('heure_debut', '<', heure_fin),
                ('heure_fin', '>', heure_debut),
            ], limit=1)
            if not conflit:
                disponibles |= c
        return disponibles
