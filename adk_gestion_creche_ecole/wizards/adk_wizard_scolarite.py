# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError


class AdkWizardScolarite(models.TransientModel):
    _name = 'adk.wizard.scolarite'
    _description = "Assistant : génération en masse des dossiers et factures de scolarité"

    etablissement_id = fields.Many2one('adk.etablissement', string="Établissement", required=True)
    annee_scolaire_id = fields.Many2one(
        'adk.annee.scolaire', string="Année académique", required=True,
        default=lambda self: self.env['adk.annee.scolaire']._get_or_create_courante())
    classe_ids = fields.Many2many('adk.classe', string="Classes concernées",
                                  help="Laisser vide pour toutes les classes de l'établissement.")
    grille_id = fields.Many2one('adk.grille.tarifaire', string="Grille tarifaire", required=True,
                                domain="[('annee_scolaire_id', '=', annee_scolaire_id)]")
    date_facture = fields.Date(string="Date de facturation", required=True,
                               default=fields.Date.context_today)
    valider_factures = fields.Boolean(string="Créer et valider les factures", default=True,
                                      help="Sinon, seuls les dossiers sont créés (brouillon).")

    def action_generer(self):
        self.ensure_one()
        domain = [('etablissement_id', '=', self.etablissement_id.id),
                  ('annee_scolaire_id', '=', self.annee_scolaire_id.id)]
        if self.classe_ids:
            domain.append(('classe_id', 'in', self.classe_ids.ids))
        eleves = self.env['adk.eleve'].search(domain)
        if not eleves:
            raise UserError("Aucun élève trouvé pour ces critères.")

        Dossier = self.env['adk.dossier.scolarite']
        existants = Dossier.search([
            ('eleve_id', 'in', eleves.ids), ('grille_id', '=', self.grille_id.id),
            ('annee_scolaire_id', '=', self.annee_scolaire_id.id), ('etat', '!=', 'annule')]).eleve_id
        dossiers = Dossier
        sans_parent = deja = erreurs = 0
        for eleve in eleves:
            if eleve in existants:
                deja += 1
                continue
            if self.valider_factures and not eleve.parent_ids:
                sans_parent += 1
                continue
            try:
                with self.env.cr.savepoint():
                    dossier = Dossier.create({
                        'eleve_id': eleve.id,
                        'annee_scolaire_id': self.annee_scolaire_id.id,
                        'grille_id': self.grille_id.id,
                        'date_facture': self.date_facture,
                    })
                    if self.valider_factures:
                        dossier.action_creer_facture()
                    dossiers |= dossier
            except UserError:
                erreurs += 1
        if not dossiers:
            raise UserError(
                "Aucun dossier créé : %s déjà facturé(s), %s sans parent, %s en erreur."
                % (deja, sans_parent, erreurs))
        return {
            'type': 'ir.actions.act_window',
            'name': "Dossiers générés (%s) — ignorés : %s déjà facturés, %s sans parent, %s en erreur"
                    % (len(dossiers), deja, sans_parent, erreurs),
            'res_model': 'adk.dossier.scolarite',
            'view_mode': 'list,form',
            'domain': [('id', 'in', dossiers.ids)],
        }
