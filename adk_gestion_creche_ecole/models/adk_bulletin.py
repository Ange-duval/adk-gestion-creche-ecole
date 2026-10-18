# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AdkBulletin(models.Model):
    _name = 'adk.bulletin'
    _description = "Bulletin de notes"
    _order = 'periode_id desc, id desc'
    _rec_name = 'display_name'

    display_name = fields.Char(string="Référence", compute='_compute_display_name', store=True)
    eleve_id = fields.Many2one('adk.eleve', string="Élève", required=True, ondelete='cascade')
    classe_id = fields.Many2one('adk.classe', string="Classe", related='eleve_id.classe_id', store=True)
    etablissement_id = fields.Many2one('adk.etablissement', string="Établissement",
                                        related='eleve_id.etablissement_id', store=True)
    annee_scolaire_id = fields.Many2one(
        'adk.annee.scolaire', related='eleve_id.annee_scolaire_id', store=True, readonly=False,
        string="Année académique",
        help="Pré-remplie depuis l'élève, mais modifiable pour rattraper une saisie "
             "concernant une année académique antérieure.")

    periode_id = fields.Many2one(
        'adk.periode', string="Période", required=True,
        default=lambda self: self.env['adk.periode'].search([], limit=1, order='sequence'))

    date_edition = fields.Date(string="Date d'édition", default=fields.Date.context_today)
    ligne_ids = fields.One2many('adk.bulletin.ligne', 'bulletin_id', string="Détail par matière")

    moyenne_generale = fields.Float(string="Moyenne générale élève", compute='_compute_moyennes', store=True)
    moyenne_classe = fields.Float(string="Moyenne de la classe", compute='_compute_moyennes', store=True)
    note_max_classe = fields.Float(string="Meilleure note de la classe", compute='_compute_moyennes', store=True)
    note_min_classe = fields.Float(string="Note la plus basse de la classe", compute='_compute_moyennes', store=True)
    rang = fields.Integer(string="Rang dans la classe", compute='_compute_moyennes', store=True)

    appreciation_generale = fields.Text(string="Avis global du conseil de classe / directeur")
    etat = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('valide', 'Validé'),
        ('envoye', 'Envoyé aux parents'),
    ], string="État", default='brouillon')

    @api.depends('eleve_id', 'periode_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = "%s - %s" % (rec.eleve_id.name or '?', rec.periode_id.name or '')

    @api.depends('ligne_ids.moyenne_ponderee', 'ligne_ids.matiere_id.coefficient')
    def _compute_moyennes(self):
        for rec in self:
            total_points = sum(l.moyenne_ponderee * l.matiere_id.coefficient for l in rec.ligne_ids)
            total_coeff = sum(l.matiere_id.coefficient for l in rec.ligne_ids) or 1.0
            rec.moyenne_generale = total_points / total_coeff

            # Comparaison avec le reste de la classe sur la même période
            camarades = self.search([
                ('classe_id', '=', rec.classe_id.id),
                ('periode_id', '=', rec.periode_id.id),
            ])
            # Calcul direct pour éviter la récursion sur le champ calculé : on recalcule à la volée
            valeurs = []
            for c in camarades:
                tp = sum(l.moyenne_ponderee * l.matiere_id.coefficient for l in c.ligne_ids)
                tc = sum(l.matiere_id.coefficient for l in c.ligne_ids) or 1.0
                valeurs.append((c.id, tp / tc))
            if valeurs:
                notes = [v for _, v in valeurs]
                rec.moyenne_classe = sum(notes) / len(notes)
                rec.note_max_classe = max(notes)
                rec.note_min_classe = min(notes)
                classement = sorted(valeurs, key=lambda x: x[1], reverse=True)
                rec.rang = [i for i, (cid, _) in enumerate(classement, start=1) if cid == rec.id][0] \
                    if rec.id in [v[0] for v in valeurs] else 0
            else:
                rec.moyenne_classe = 0.0
                rec.note_max_classe = 0.0
                rec.note_min_classe = 0.0
                rec.rang = 0

    def action_generer_lignes_depuis_notes(self):
        """Récupère toutes les notes saisies par les enseignants pour la période et regroupe par matière."""
        Note = self.env['adk.note']
        Ligne = self.env['adk.bulletin.ligne']
        for rec in self:
            rec.ligne_ids.unlink()
            notes = Note.search([('eleve_id', '=', rec.eleve_id.id), ('periode_id', '=', rec.periode_id.id)])
            matieres = notes.mapped('matiere_id')
            for matiere in matieres:
                notes_matiere = notes.filtered(lambda n: n.matiere_id == matiere)
                moyenne = sum(notes_matiere.mapped('note_ponderee_20')) / len(notes_matiere)
                enseignant = notes_matiere[:1].enseignant_id
                Ligne.create({
                    'bulletin_id': rec.id,
                    'matiere_id': matiere.id,
                    'enseignant_id': enseignant.id,
                    'moyenne_ponderee': moyenne,
                })
        return True

    def action_valider(self):
        self.write({'etat': 'valide'})

    def action_envoyer_parents(self):
        """Envoi automatique sur le portail des parents."""
        for rec in self:
            template = self.env.ref('adk_gestion_creche_ecole.mail_template_bulletin_eleve',
                                     raise_if_not_found=False)
            if template and rec.eleve_id.parent_ids:
                template.send_mail(rec.id, force_send=True)
            rec.etat = 'envoye'


class AdkBulletinLigne(models.Model):
    _name = 'adk.bulletin.ligne'
    _description = "Ligne de bulletin (par matière)"

    bulletin_id = fields.Many2one('adk.bulletin', string="Bulletin", required=True, ondelete='cascade')
    matiere_id = fields.Many2one('adk.matiere', string="Matière", required=True)
    enseignant_id = fields.Many2one('hr.employee', string="Enseignant")
    coefficient = fields.Float(related='matiere_id.coefficient', string="Coefficient")
    moyenne_ponderee = fields.Float(string="Moyenne (/20)")
    appreciation = fields.Char(string="Appréciation de l'enseignant")
