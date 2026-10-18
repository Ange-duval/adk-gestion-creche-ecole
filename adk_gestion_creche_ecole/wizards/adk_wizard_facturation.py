# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class AdkWizardFacturation(models.TransientModel):
    _name = 'adk.wizard.facturation'
    _description = "Assistant : Facturation mensuelle globale (Scolarité + Repas + Fournitures)"

    etablissement_id = fields.Many2one('adk.etablissement', string="Établissement", required=True)
    classe_ids = fields.Many2many('adk.classe', string="Classes concernées",
                                   domain="[('etablissement_id', '=', etablissement_id)]")
    mois = fields.Date(string="Mois à facturer", required=True, default=fields.Date.context_today)
    inclure_scolarite = fields.Boolean(string="Inclure les frais de scolarité", default=True)
    inclure_repas = fields.Boolean(string="Inclure les repas consommés", default=True)
    inclure_fournitures = fields.Boolean(string="Inclure les fournitures achetées à la librairie",
                                          default=True)
    montant_scolarite_mensuel = fields.Monetary(string="Montant mensuel de scolarité", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    def action_generer_factures(self):
        self.ensure_one()
        if not self.etablissement_id.journal_id:
            raise UserError(
                "Veuillez configurer un journal de facturation sur la fiche de l'établissement %s."
                % self.etablissement_id.name)

        domain = [('etablissement_id', '=', self.etablissement_id.id)]
        if self.classe_ids:
            domain.append(('classe_id', 'in', self.classe_ids.ids))
        eleves = self.env['adk.eleve'].search(domain)
        if not eleves:
            raise UserError("Aucun élève trouvé pour les critères sélectionnés.")

        Move = self.env['account.move']
        factures = Move
        for eleve in eleves:
            if not eleve.parent_ids:
                continue
            lignes = []
            if self.inclure_scolarite and self.montant_scolarite_mensuel:
                lignes.append((0, 0, {
                    'name': "Frais de scolarité - %s - %s" % (eleve.name, self.mois.strftime('%B %Y')),
                    'quantity': 1,
                    'price_unit': self.montant_scolarite_mensuel,
                }))
            # Les repas et fournitures sont intégrés via les articles product.template
            # marqués is_adk_facturable_parent, rattachés aux ventes du mois pour l'élève.
            if not lignes:
                continue
            facture = Move.create({
                'move_type': 'out_invoice',
                'partner_id': eleve.parent_ids[0].id,
                'invoice_date': self.mois,
                'journal_id': self.etablissement_id.journal_id.id,
                'invoice_line_ids': lignes,
                'ref': "Facturation mensuelle - %s" % eleve.name,
            })
            factures |= facture

        return {
            'type': 'ir.actions.act_window',
            'name': "Factures générées",
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', factures.ids)],
        }
