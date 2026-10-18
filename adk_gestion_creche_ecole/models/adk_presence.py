# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AdkPresence(models.Model):
    _name = 'adk.presence'
    _description = "Registre de présence des élèves"
    _order = 'date desc, heure_debut desc'

    eleve_id = fields.Many2one('adk.eleve', string="Élève", required=True, ondelete='cascade')
    classe_id = fields.Many2one('adk.classe', string="Classe", related='eleve_id.classe_id', store=True)
    annee_scolaire_id = fields.Many2one(
        'adk.annee.scolaire', related='eleve_id.annee_scolaire_id', store=True, readonly=False,
        string="Année académique",
        help="Pré-remplie depuis l'élève, mais modifiable pour rattraper une saisie "
             "concernant une année académique antérieure.")
    session_cours_id = fields.Many2one('adk.session.cours', string="Cours concerné")
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    heure_debut = fields.Float(string="Heure du cours")

    statut = fields.Selection([
        ('present', 'Présent'),
        ('absent', 'Absent'),
        ('retard', 'En retard'),
        ('excuse', 'Absence justifiée'),
    ], string="Statut", required=True, default='present')

    mode_saisie = fields.Selection([
        ('badge', 'Badgeage'),
        ('manuel', 'Appel numérique'),
    ], string="Mode de saisie", default='manuel')

    motif = fields.Char(string="Motif (si absence)")
    notification_envoyee = fields.Boolean(string="Notification parent envoyée", default=False)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.statut == 'absent' and not rec.notification_envoyee:
                rec._notifier_parents_absence()
        return records

    def _notifier_parents_absence(self):
        """Notification automatique par SMS/Email aux parents en cas d'absence non justifiée."""
        for rec in self:
            if rec.statut != 'absent':
                continue
            template = self.env.ref('adk_gestion_creche_ecole.mail_template_absence_eleve',
                                     raise_if_not_found=False)
            if template and rec.eleve_id.parent_ids:
                template.send_mail(rec.id, force_send=True)
            rec.notification_envoyee = True
