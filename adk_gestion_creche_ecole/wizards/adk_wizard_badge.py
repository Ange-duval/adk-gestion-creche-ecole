# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class AdkWizardBadge(models.TransientModel):
    _name = 'adk.wizard.badge'
    _description = "Assistant : Génération en masse des badges d'accès"

    etablissement_id = fields.Many2one('adk.etablissement', string="Établissement", required=True)
    population = fields.Selection([
        ('eleves', 'Élèves'),
        ('parents', 'Parents'),
        ('personnel', 'Personnel'),
    ], string="Population cible", required=True, default='eleves')
    classe_ids = fields.Many2many('adk.classe', string="Classes (optionnel, sinon tout l'établissement)",
                                   domain="[('etablissement_id', '=', etablissement_id)]")
    format_carte = fields.Selection([
        ('cr80', "Format carte de crédit (CR80)"),
        ('etiquette', "Format étiquette"),
    ], string="Format d'impression", default='cr80', required=True)
    regenerer_existants = fields.Boolean(
        string="Régénérer les badges déjà existants",
        help="Si décoché, seuls les élèves/parents/personnels sans badge actif recevront un nouveau badge.")

    def action_generer(self):
        self.ensure_one()
        Badge = self.env['adk.badge']
        badges = Badge

        if self.population == 'eleves':
            domain = [('etablissement_id', '=', self.etablissement_id.id)]
            if self.classe_ids:
                domain.append(('classe_id', 'in', self.classe_ids.ids))
            eleves = self.env['adk.eleve'].search(domain)
            if not eleves:
                raise UserError("Aucun élève trouvé pour les critères sélectionnés.")
            for eleve in eleves:
                existant = Badge.search([('eleve_id', '=', eleve.id), ('role', '=', 'eleve'),
                                          ('statut', '=', 'actif')], limit=1)
                if existant and not self.regenerer_existants:
                    badges |= existant
                    continue
                badges |= Badge.create({
                    'role': 'eleve',
                    'eleve_id': eleve.id,
                    'etablissement_id': self.etablissement_id.id,
                })

        elif self.population == 'parents':
            eleves = self.env['adk.eleve'].search([('etablissement_id', '=', self.etablissement_id.id)])
            parents = eleves.mapped('parent_ids')
            if not parents:
                raise UserError("Aucun parent trouvé pour les critères sélectionnés.")
            for parent in parents:
                existant = Badge.search([('parent_id', '=', parent.id), ('role', '=', 'parent'),
                                          ('statut', '=', 'actif')], limit=1)
                if existant and not self.regenerer_existants:
                    badges |= existant
                    continue
                badges |= Badge.create({
                    'role': 'parent',
                    'parent_id': parent.id,
                    'etablissement_id': self.etablissement_id.id,
                })

        else:  # personnel
            employees = self.env['hr.employee'].search(
                [('etablissement_ids', 'in', self.etablissement_id.id)])
            if not employees:
                raise UserError("Aucun membre du personnel rattaché à cet établissement.")
            for emp in employees:
                existant = Badge.search([('employee_id', '=', emp.id), ('role', '=', 'enseignant'),
                                          ('statut', '=', 'actif')], limit=1)
                if existant and not self.regenerer_existants:
                    badges |= existant
                    continue
                badges |= Badge.create({
                    'role': 'enseignant' if emp.is_adk_enseignant else 'personnel',
                    'employee_id': emp.id,
                    'etablissement_id': self.etablissement_id.id,
                })

        return {
            'type': 'ir.actions.act_window',
            'name': "Badges générés",
            'res_model': 'adk.badge',
            'view_mode': 'list,form',
            'domain': [('id', 'in', badges.ids)],
        }

    def action_generer_et_imprimer(self):
        self.ensure_one()
        action = self.action_generer()
        badge_ids = action['domain'][0][2]
        report_xmlid = 'adk_gestion_creche_ecole.action_report_badge_cr80' \
            if self.format_carte == 'cr80' else 'adk_gestion_creche_ecole.action_report_badge_etiquette'
        return self.env.ref(report_xmlid).report_action(self.env['adk.badge'].browse(badge_ids))
