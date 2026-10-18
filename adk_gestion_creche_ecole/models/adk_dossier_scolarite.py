# -*- coding: utf-8 -*-
from datetime import date, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AdkDossierScolarite(models.Model):
    _name = 'adk.dossier.scolarite'
    _description = "Dossier de scolarité (facture et paiements d'un élève)"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_facture desc, id desc'

    name = fields.Char(string="Référence", required=True, copy=False, readonly=True,
                       default=lambda self: _('Nouveau'))
    eleve_id = fields.Many2one('adk.eleve', string="Élève", required=True, ondelete='restrict',
                               tracking=True, index=True)
    classe_id = fields.Many2one('adk.classe', related='eleve_id.classe_id', store=True, string="Classe")
    etablissement_id = fields.Many2one('adk.etablissement', related='eleve_id.etablissement_id',
                                       store=True, string="Établissement")
    company_id = fields.Many2one('res.company', related='etablissement_id.company_id', store=True,
                                 string="Société")
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Devise")
    annee_scolaire_id = fields.Many2one(
        'adk.annee.scolaire', string="Année académique", required=True, tracking=True,
        default=lambda self: self.env['adk.annee.scolaire']._get_or_create_courante())
    grille_id = fields.Many2one('adk.grille.tarifaire', string="Grille tarifaire", tracking=True,
                                domain="[('annee_scolaire_id', '=', annee_scolaire_id)]")
    partenaire_id = fields.Many2one('res.partner', string="Client à facturer (parent / tuteur)", tracking=True)
    date_facture = fields.Date(string="Date de facturation", required=True, default=fields.Date.context_today)

    ligne_ids = fields.One2many('adk.dossier.scolarite.ligne', 'dossier_id', string="Rubriques", copy=True)
    tranche_ids = fields.One2many('adk.dossier.scolarite.tranche', 'dossier_id', string="Échéancier", copy=True)

    remise_montant = fields.Monetary(string="Remise (montant fixe)", currency_field='currency_id')
    bourse_pct = fields.Float(string="Bourse / réduction (%)")
    montant_brut = fields.Monetary(string="Frais bruts", compute='_compute_montants', store=True,
                                   currency_field='currency_id')
    montant_net = fields.Monetary(string="Net à payer", compute='_compute_montants', store=True,
                                  currency_field='currency_id')

    invoice_id = fields.Many2one('account.move', string="Facture", readonly=True, copy=False, tracking=True)
    invoice_state = fields.Selection(related='invoice_id.state', string="Statut facture")
    etat = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('facture', 'Facturé'),
        ('partiel', 'Partiellement payé'),
        ('paye', 'Payé'),
        ('annule', 'Annulé'),
    ], string="État", compute='_compute_paiement', store=True, tracking=True, index=True)
    montant_paye = fields.Monetary(string="Déjà payé", compute='_compute_paiement', store=True,
                                   currency_field='currency_id')
    solde = fields.Monetary(string="Montant dû", compute='_compute_paiement', store=True,
                            currency_field='currency_id')
    paiement_ids = fields.Many2many('account.payment', string="Paiements", compute='_compute_paiement_ids')
    nb_paiements = fields.Integer(string="Nb paiements", compute='_compute_paiement_ids')
    note = fields.Text(string="Notes")

    # ------------------------------------------------------------------ calculs
    @api.depends('ligne_ids.montant', 'bourse_pct', 'remise_montant', 'currency_id')
    def _compute_montants(self):
        for rec in self:
            brut = sum(rec.ligne_ids.mapped('montant'))
            net = brut - brut * (rec.bourse_pct or 0.0) / 100.0 - (rec.remise_montant or 0.0)
            if rec.currency_id:
                brut = rec.currency_id.round(brut)
                net = rec.currency_id.round(net)
            rec.montant_brut = brut
            rec.montant_net = max(net, 0.0)

    @api.depends('invoice_id.state', 'invoice_id.payment_state', 'invoice_id.amount_residual',
                 'invoice_id.amount_total', 'montant_net')
    def _compute_paiement(self):
        for rec in self:
            inv = rec.invoice_id
            if not inv or inv.state == 'draft':
                rec.etat, rec.montant_paye, rec.solde = 'brouillon', 0.0, rec.montant_net
            elif inv.state == 'cancel':
                rec.etat, rec.montant_paye, rec.solde = 'annule', 0.0, 0.0
            else:
                paye = inv.amount_total - inv.amount_residual
                rec.montant_paye = paye
                rec.solde = inv.amount_residual
                if inv.currency_id.is_zero(inv.amount_residual):
                    rec.etat = 'paye'
                elif paye > 0:
                    rec.etat = 'partiel'
                else:
                    rec.etat = 'facture'

    @api.depends('invoice_id.state', 'invoice_id.amount_residual')
    def _compute_paiement_ids(self):
        for rec in self:
            payments = self.env['account.payment']
            for det in rec._get_paiements_detail():
                payments |= det['payment']
            rec.paiement_ids = payments
            rec.nb_paiements = len(rec._get_paiements_detail())

    def _get_paiements_detail(self):
        """Liste chronologique des règlements réellement lettrés à la facture.

        Chaque élément : date, montant, paiement (account.payment ou vide), journal, référence,
        utilisateur. Source unique de vérité pour l'onglet Paiements et pour tous les rapports,
        que le paiement ait été saisi depuis le dossier ou depuis la comptabilité.
        """
        self.ensure_one()
        res = []
        inv = self.invoice_id
        if not inv or inv.state != 'posted':
            return res
        rec_lines = inv.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
        for partial in rec_lines.matched_credit_ids | rec_lines.matched_debit_ids:
            counter = partial.credit_move_id if partial.debit_move_id in rec_lines else partial.debit_move_id
            move = counter.move_id
            payment = move.origin_payment_id if 'origin_payment_id' in move._fields else move.payment_id
            res.append({
                'date': counter.date,
                'amount': partial.amount,
                'payment': payment or self.env['account.payment'],
                'journal': move.journal_id,
                'ref': (payment.name if payment else move.name) or move.name,
                'user': (payment.create_uid if payment else move.create_uid),
                'create_date': (payment.create_date if payment else move.create_date),
            })
        res.sort(key=lambda r: (r['date'], r['ref'] or ''))
        return res

    def _paye_a_date(self, date_limite):
        """Cumul des règlements datés au plus tard de `date_limite`."""
        self.ensure_one()
        return sum(d['amount'] for d in self._get_paiements_detail()
                   if not date_limite or d['date'] <= date_limite)

    def _retard_jours(self, date_arret):
        """Nombre de jours de retard de la plus ancienne échéance non soldée à `date_arret`."""
        self.ensure_one()
        restant = self._paye_a_date(date_arret)
        due = False
        tranches = self.tranche_ids.sorted(lambda t: (t.date_echeance or date.max, t.sequence, t.id))
        if tranches:
            for t in tranches:
                if restant >= t.montant - 0.0001:
                    restant -= t.montant
                    continue
                due = t.date_echeance
                break
        else:
            due = self.invoice_id.invoice_date_due or self.date_facture
        if due and due < date_arret:
            return (date_arret - due).days
        return 0

    # ------------------------------------------------------------------ grille
    def _appliquer_grille(self):
        for rec in self:
            if not rec.grille_id:
                continue
            rec.ligne_ids = [(5, 0, 0)] + [(0, 0, {
                'sequence': l.sequence, 'name': l.name, 'montant': l.montant,
                'product_id': l.product_id.id,
            }) for l in rec.grille_id.ligne_ids]
            rec.tranche_ids = [(5, 0, 0)] + [(0, 0, {
                'sequence': t.sequence, 'name': t.name, 'pourcentage': t.pourcentage,
                'delai_jours': t.delai_jours,
            }) for t in rec.grille_id.tranche_ids]

    @api.onchange('eleve_id')
    def _onchange_eleve_id(self):
        if self.eleve_id:
            if self.eleve_id.annee_scolaire_id:
                self.annee_scolaire_id = self.eleve_id.annee_scolaire_id
            if not self.partenaire_id and self.eleve_id.parent_ids:
                self.partenaire_id = self.eleve_id.parent_ids[0]

    @api.onchange('grille_id')
    def _onchange_grille_id(self):
        if self.grille_id and self.etat in (False, 'brouillon'):
            self._appliquer_grille()

    @api.onchange('annee_scolaire_id')
    def _onchange_annee(self):
        if self.grille_id and self.grille_id.annee_scolaire_id != self.annee_scolaire_id:
            self.grille_id = False

    @api.constrains('eleve_id', 'grille_id', 'annee_scolaire_id', 'etat')
    def _check_doublon(self):
        for rec in self:
            if rec.grille_id and rec.etat != 'annule':
                autre = self.search_count([
                    ('id', '!=', rec.id), ('eleve_id', '=', rec.eleve_id.id),
                    ('grille_id', '=', rec.grille_id.id),
                    ('annee_scolaire_id', '=', rec.annee_scolaire_id.id),
                    ('etat', '!=', 'annule')])
                if autre:
                    raise ValidationError(
                        "%s possède déjà un dossier « %s » pour l'année %s."
                        % (rec.eleve_id.name, rec.grille_id.name, rec.annee_scolaire_id.name))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('adk.dossier.scolarite') or _('Nouveau')
            if not vals.get('partenaire_id') and vals.get('eleve_id'):
                parents = self.env['adk.eleve'].browse(vals['eleve_id']).parent_ids
                if parents:
                    vals['partenaire_id'] = parents[0].id
        records = super().create(vals_list)
        for rec in records:
            if rec.grille_id and not rec.ligne_ids:
                rec._appliquer_grille()
        return records

    @api.ondelete(at_uninstall=False)
    def _unlink_except_facture(self):
        for rec in self:
            if rec.invoice_id:
                raise UserError("Le dossier %s est lié à une facture : annulez-le au lieu de le supprimer."
                                % rec.name)

    # ------------------------------------------------------------------ facture
    def _preparer_facture(self):
        self.ensure_one()
        company = self.company_id
        journal = self.etablissement_id.journal_id or self.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', company.id)], limit=1)
        if not journal:
            raise UserError("Aucun journal de vente trouvé pour la société %s." % company.name)
        lignes = []
        for l in self.ligne_ids:
            vals = {'name': l.name, 'quantity': 1, 'price_unit': l.montant,
                    'discount': self.bourse_pct or 0.0}
            if l.product_id:
                vals['product_id'] = l.product_id.id
            lignes.append((0, 0, vals))
        if self.remise_montant:
            lignes.append((0, 0, {'name': _("Remise"), 'quantity': 1, 'price_unit': -self.remise_montant}))
        echeances = [t.date_echeance for t in self.tranche_ids if t.date_echeance]
        return {
            'move_type': 'out_invoice',
            'partner_id': self.partenaire_id.id,
            'invoice_date': self.date_facture,
            'invoice_date_due': max(echeances) if echeances else self.date_facture,
            'journal_id': journal.id,
            'company_id': company.id,
            'invoice_origin': self.name,
            'ref': _("Scolarité %(eleve)s - %(annee)s", eleve=self.eleve_id.name,
                     annee=self.annee_scolaire_id.name),
            'invoice_line_ids': lignes,
            'adk_dossier_id': self.id,
        }

    def action_creer_facture(self):
        for rec in self:
            if rec.invoice_id and rec.invoice_id.state != 'cancel':
                raise UserError("Le dossier %s est déjà facturé." % rec.name)
            if not rec.partenaire_id:
                raise UserError("Renseignez le parent / tuteur à facturer pour %s." % rec.eleve_id.name)
            if not rec.ligne_ids or rec.montant_net <= 0:
                raise UserError("Le dossier %s n'a aucune rubrique à facturer." % rec.name)
            move = self.env['account.move'].with_company(rec.company_id).create(rec._preparer_facture())
            move.action_post()
            rec.invoice_id = move
            rec.message_post(body=_("Facture %s créée et validée.", move.name))
        return True

    def action_enregistrer_paiement(self):
        self.ensure_one()
        inv = self.invoice_id
        if not inv or inv.state != 'posted':
            raise UserError("Créez d'abord la facture avant d'enregistrer un paiement.")
        if inv.currency_id.is_zero(inv.amount_residual):
            raise UserError("Cette facture est déjà entièrement payée.")
        return inv.action_register_payment()

    def action_voir_facture(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': self.invoice_id.name,
            'res_model': 'account.move', 'res_id': self.invoice_id.id, 'view_mode': 'form',
        }

    def action_voir_paiements(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _("Paiements - %s", self.name),
            'res_model': 'account.payment', 'view_mode': 'list,form',
            'domain': [('id', 'in', self.paiement_ids.ids)],
        }

    def action_annuler(self):
        for rec in self:
            if not rec.invoice_id:
                rec.write({'invoice_id': False})
                continue
            if rec._get_paiements_detail():
                raise UserError("Des paiements sont rattachés à la facture de %s : annulez ou dé-lettrez "
                                "d'abord ces paiements." % rec.eleve_id.name)
            if rec.invoice_id.state == 'posted':
                rec.invoice_id.button_draft()
            if rec.invoice_id.state == 'draft':
                rec.invoice_id.button_cancel()
        return True

    def action_remettre_brouillon(self):
        for rec in self:
            if rec.etat != 'annule':
                raise UserError("Seul un dossier annulé peut être remis en brouillon.")
            rec.invoice_id = False
        return True


class AdkDossierScolariteLigne(models.Model):
    _name = 'adk.dossier.scolarite.ligne'
    _description = "Rubrique d'un dossier de scolarité"
    _order = 'sequence, id'

    dossier_id = fields.Many2one('adk.dossier.scolarite', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Libellé", required=True)
    product_id = fields.Many2one('product.product', string="Article")
    montant = fields.Monetary(string="Montant", required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='dossier_id.currency_id', readonly=True)


class AdkDossierScolariteTranche(models.Model):
    _name = 'adk.dossier.scolarite.tranche'
    _description = "Tranche d'un dossier de scolarité"
    _order = 'sequence, id'

    dossier_id = fields.Many2one('adk.dossier.scolarite', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Intitulé", required=True)
    pourcentage = fields.Float(string="Part (%)")
    delai_jours = fields.Integer(string="Délai (jours)")
    date_echeance = fields.Date(string="Échéance", compute='_compute_echeance', store=True, readonly=False)
    montant = fields.Monetary(string="Montant", compute='_compute_montant', store=True, readonly=False,
                              currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='dossier_id.currency_id', readonly=True)
    montant_paye = fields.Monetary(string="Réglé", compute='_compute_statut', currency_field='currency_id')
    statut = fields.Selection([
        ('attente', 'À venir'), ('partiel', 'Partiel'), ('paye', 'Payée'), ('retard', 'En retard'),
    ], string="Statut", compute='_compute_statut')

    @api.depends('dossier_id.date_facture', 'delai_jours')
    def _compute_echeance(self):
        for rec in self:
            base = rec.dossier_id.date_facture or fields.Date.context_today(rec)
            rec.date_echeance = base + timedelta(days=rec.delai_jours or 0)

    @api.depends('pourcentage', 'dossier_id.montant_net')
    def _compute_montant(self):
        for rec in self:
            net = rec.dossier_id.montant_net
            val = net * (rec.pourcentage or 0.0) / 100.0
            rec.montant = rec.dossier_id.currency_id.round(val) if rec.dossier_id.currency_id else val

    @api.depends('dossier_id.montant_paye', 'dossier_id.tranche_ids.montant',
                 'dossier_id.tranche_ids.date_echeance')
    def _compute_statut(self):
        today = fields.Date.context_today(self)
        for rec in self:
            restant = rec.dossier_id.montant_paye
            rec.montant_paye = 0.0
            rec.statut = 'attente'
            ordonnees = rec.dossier_id.tranche_ids.sorted(
                lambda t: (t.date_echeance or date.max, t.sequence, t.id or 0))
            for t in ordonnees:
                alloue = min(max(restant, 0.0), t.montant)
                restant -= alloue
                if t.id == rec.id or (not rec.id and t == rec):
                    rec.montant_paye = alloue
                    if t.montant and alloue >= t.montant - 0.0001:
                        rec.statut = 'paye'
                    elif alloue > 0:
                        rec.statut = 'partiel'
                    elif t.date_echeance and t.date_echeance < today:
                        rec.statut = 'retard'
                    break
