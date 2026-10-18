# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AdkEleve(models.Model):
    _name = 'adk.eleve'
    _description = "Élève / Enfant"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(string="Nom complet", required=True, tracking=True)
    prenom = fields.Char(string="Prénom")
    nom = fields.Char(string="Nom de famille")
    photo = fields.Image(string="Photo")
    matricule = fields.Char(string="Matricule", copy=False, readonly=True,
                             default=lambda self: self.env['ir.sequence'].next_by_code('adk.eleve'))
    active = fields.Boolean(default=True)

    date_naissance = fields.Date(string="Date de naissance")
    lieu_naissance = fields.Char(string="Lieu de naissance")
    genre = fields.Selection([('m', 'Masculin'), ('f', 'Féminin')], string="Genre")
    nationalite_id = fields.Many2one('res.country', string="Nationalité")

    # État civil
    adresse = fields.Char(string="Adresse")

    # Affectation
    etablissement_id = fields.Many2one('adk.etablissement', string="Établissement",
                                        required=True, tracking=True)
    classe_id = fields.Many2one('adk.classe', string="Classe d'affectation principale",
                                 tracking=True,
                                 domain="[('etablissement_id', '=', etablissement_id)]")
    annee_scolaire_id = fields.Many2one(
        'adk.annee.scolaire', string="Année académique",
        related='classe_id.annee_scolaire_id', store=True, readonly=False,
        help="Pré-remplie depuis la classe, mais modifiable pour rattraper une saisie "
             "concernant une année académique antérieure.")

    # Historique médical
    medecin_traitant = fields.Char(string="Médecin traitant")
    telephone_medecin = fields.Char(string="Téléphone du médecin")
    allergies = fields.Text(string="Allergies")
    antecedents_medicaux = fields.Text(string="Antécédents médicaux")
    groupe_sanguin = fields.Selection([
        ('a+', 'A+'), ('a-', 'A-'), ('b+', 'B+'), ('b-', 'B-'),
        ('ab+', 'AB+'), ('ab-', 'AB-'), ('o+', 'O+'), ('o-', 'O-'),
    ], string="Groupe sanguin")

    # Parents
    parent_ids = fields.Many2many('res.partner', 'adk_eleve_parent_rel', 'eleve_id', 'parent_id',
                                   string="Parents / Tuteurs",
                                   domain="[('is_adk_parent', '=', True)]")

    # Vie scolaire
    presence_ids = fields.One2many('adk.presence', 'eleve_id', string="Présences")
    note_ids = fields.One2many('adk.note', 'eleve_id', string="Notes")
    bulletin_ids = fields.One2many('adk.bulletin', 'eleve_id', string="Bulletins")
    pointage_ids = fields.One2many('adk.pointage', 'eleve_id', string="Pointages")
    badge_ids = fields.One2many('adk.badge', 'eleve_id', string="Badges")

    taux_absence = fields.Float(string="Taux d'absence (%)", compute='_compute_taux_absence')

    # Scolarité (facturation)
    date_inscription = fields.Date(string="Date d'inscription", copy=False,
                                   help="Sert à compter les nouveaux inscrits dans les rapports.")
    dossier_ids = fields.One2many('adk.dossier.scolarite', 'eleve_id', string="Dossiers de scolarité")
    nb_dossiers = fields.Integer(string="Dossiers de scolarité", compute='_compute_scolarite')
    solde_scolarite = fields.Monetary(string="Solde de scolarité", compute='_compute_scolarite',
                                      currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='etablissement_id.currency_id')

    @api.depends('dossier_ids.solde', 'dossier_ids.etat')
    def _compute_scolarite(self):
        for rec in self:
            actifs = rec.dossier_ids.filtered(lambda d: d.etat in ('facture', 'partiel'))
            rec.nb_dossiers = len(rec.dossier_ids)
            rec.solde_scolarite = sum(actifs.mapped('solde'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault('date_inscription', fields.Date.context_today(self))
        return super().create(vals_list)

    def action_voir_dossiers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': "Scolarité - %s" % self.name,
            'res_model': 'adk.dossier.scolarite',
            'view_mode': 'list,form',
            'domain': [('eleve_id', '=', self.id)],
            'context': {'default_eleve_id': self.id},
        }

    @api.depends('presence_ids.statut')
    def _compute_taux_absence(self):
        for rec in self:
            total = len(rec.presence_ids)
            absences = len(rec.presence_ids.filtered(lambda p: p.statut == 'absent'))
            rec.taux_absence = (absences / total * 100.0) if total else 0.0

    @api.onchange('prenom', 'nom')
    def _onchange_identite(self):
        if self.prenom or self.nom:
            self.name = " ".join(filter(None, [self.prenom, self.nom]))
