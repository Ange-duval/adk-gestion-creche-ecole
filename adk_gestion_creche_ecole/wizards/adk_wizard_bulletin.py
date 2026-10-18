# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class AdkWizardBulletin(models.TransientModel):
    _name = 'adk.wizard.bulletin'
    _description = "Assistant : Génération en masse des bulletins"

    etablissement_id = fields.Many2one('adk.etablissement', string="Établissement", required=True)
    classe_ids = fields.Many2many('adk.classe', string="Classes concernées",
                                   domain="[('etablissement_id', '=', etablissement_id)]")
    periode_id = fields.Many2one(
        'adk.periode', string="Période", required=True,
        default=lambda self: self.env['adk.periode'].search([], limit=1, order='sequence'))
    tout_etablissement = fields.Boolean(
        string="Générer pour tout l'établissement",
        help="Si coché, ignore la sélection de classes et génère pour tous les élèves de l'établissement.")
    valider_automatiquement = fields.Boolean(string="Valider automatiquement après génération")
    envoyer_parents = fields.Boolean(string="Envoyer directement aux parents après validation")

    def action_generer(self):
        self.ensure_one()
        Bulletin = self.env['adk.bulletin']
        Eleve = self.env['adk.eleve']

        if self.tout_etablissement:
            eleves = Eleve.search([('etablissement_id', '=', self.etablissement_id.id)])
        else:
            if not self.classe_ids:
                raise UserError("Veuillez sélectionner au moins une classe, ou cocher "
                                 "« Générer pour tout l'établissement ».")
            eleves = Eleve.search([('classe_id', 'in', self.classe_ids.ids)])

        if not eleves:
            raise UserError("Aucun élève trouvé pour les critères sélectionnés.")

        bulletins_crees = Bulletin
        for eleve in eleves:
            bulletin = Bulletin.search([
                ('eleve_id', '=', eleve.id), ('periode_id', '=', self.periode_id.id)
            ], limit=1)
            if not bulletin:
                bulletin = Bulletin.create({'eleve_id': eleve.id, 'periode_id': self.periode_id.id})
            bulletin.action_generer_lignes_depuis_notes()
            bulletins_crees |= bulletin

        if self.valider_automatiquement:
            bulletins_crees.action_valider()
            if self.envoyer_parents:
                bulletins_crees.action_envoyer_parents()

        return {
            'type': 'ir.actions.act_window',
            'name': "Bulletins générés",
            'res_model': 'adk.bulletin',
            'view_mode': 'list,form',
            'domain': [('id', 'in', bulletins_crees.ids)],
        }

    def action_generer_et_imprimer(self):
        self.ensure_one()
        action = self.action_generer()
        bulletin_ids = action['domain'][0][2]
        return self.env.ref('adk_gestion_creche_ecole.action_report_bulletin').report_action(
            self.env['adk.bulletin'].browse(bulletin_ids))
