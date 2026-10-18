# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AdkSessionCours(models.Model):
    _name = 'adk.session.cours'
    _description = "Session de cours (instance concrète d'une matière)"
    _order = 'name'

    name = fields.Char(string="Référence", compute='_compute_name', store=True)
    matiere_id = fields.Many2one('adk.matiere', string="Matière", required=True, ondelete='cascade')
    classe_id = fields.Many2one('adk.classe', string="Classe", required=True, ondelete='cascade')
    enseignant_id = fields.Many2one('hr.employee', string="Enseignant", required=True)
    salle_id = fields.Many2one('adk.salle', string="Salle par défaut")
    etablissement_id = fields.Many2one(related='classe_id.etablissement_id', store=True)
    annee_scolaire_id = fields.Many2one(
        'adk.annee.scolaire', related='classe_id.annee_scolaire_id', store=True, readonly=False,
        string="Année académique")

    heures_semaine = fields.Float(string="Heures par semaine", default=1.0)
    active = fields.Boolean(default=True)

    emploi_temps_ids = fields.One2many('adk.emploi.temps', 'session_cours_id', string="Créneaux planifiés")

    @api.depends('matiere_id', 'classe_id', 'enseignant_id')
    def _compute_name(self):
        for rec in self:
            rec.name = "%s - %s (%s)" % (
                rec.matiere_id.name or '?', rec.classe_id.name or '?', rec.enseignant_id.name or '?')

    @api.constrains('enseignant_id', 'matiere_id')
    def _check_competence_enseignant(self):
        for rec in self:
            if rec.matiere_id.enseignant_ids and rec.enseignant_id not in rec.matiere_id.enseignant_ids:
                raise ValidationError(
                    "L'enseignant %s n'a pas la compétence déclarée pour dispenser la matière %s."
                    % (rec.enseignant_id.name, rec.matiere_id.name))


class AdkEmploiTemps(models.Model):
    _name = 'adk.emploi.temps'
    _description = "Créneau d'emploi du temps"
    _order = 'jour_semaine, heure_debut'

    name = fields.Char(string="Libellé", compute='_compute_name', store=True)
    session_cours_id = fields.Many2one('adk.session.cours', string="Session de cours",
                                        required=True, ondelete='cascade')
    matiere_id = fields.Many2one(related='session_cours_id.matiere_id', store=True, string="Matière")
    classe_id = fields.Many2one(related='session_cours_id.classe_id', store=True, string="Classe")
    enseignant_id = fields.Many2one(related='session_cours_id.enseignant_id', store=True,
                                     string="Enseignant", readonly=False)
    salle_id = fields.Many2one('adk.salle', string="Salle", required=True)
    etablissement_id = fields.Many2one(related='session_cours_id.etablissement_id', store=True)

    jour_semaine = fields.Selection([
        ('0', 'Lundi'), ('1', 'Mardi'), ('2', 'Mercredi'),
        ('3', 'Jeudi'), ('4', 'Vendredi'), ('5', 'Samedi'), ('6', 'Dimanche'),
    ], string="Jour", required=True, default='0')

    heure_debut = fields.Float(string="Heure de début", required=True, default=8.0)
    heure_fin = fields.Float(string="Heure de fin", required=True, default=9.0)

    color = fields.Integer(related='matiere_id.couleur', string="Couleur")

    @api.depends('matiere_id', 'classe_id', 'jour_semaine')
    def _compute_name(self):
        jours = dict(self._fields['jour_semaine'].selection)
        for rec in self:
            rec.name = "%s - %s (%s)" % (
                rec.matiere_id.name or '?', rec.classe_id.name or '?', jours.get(rec.jour_semaine, ''))

    @api.constrains('heure_debut', 'heure_fin')
    def _check_heures(self):
        for rec in self:
            if rec.heure_debut >= rec.heure_fin:
                raise ValidationError("L'heure de début doit être antérieure à l'heure de fin.")

    def _get_overlap_domain(self):
        self.ensure_one()
        return [
            ('id', '!=', self.id),
            ('jour_semaine', '=', self.jour_semaine),
            ('heure_debut', '<', self.heure_fin),
            ('heure_fin', '>', self.heure_debut),
        ]

    @api.constrains('enseignant_id', 'jour_semaine', 'heure_debut', 'heure_fin')
    def _check_conflit_enseignant(self):
        for rec in self:
            domain = rec._get_overlap_domain() + [('enseignant_id', '=', rec.enseignant_id.id)]
            conflit = self.search(domain, limit=1)
            if conflit:
                raise ValidationError(
                    "Conflit d'emploi du temps : l'enseignant %s est déjà planifié le %s "
                    "de %.2fh à %.2fh sur le cours « %s »."
                    % (rec.enseignant_id.name, dict(rec._fields['jour_semaine'].selection).get(rec.jour_semaine),
                       conflit.heure_debut, conflit.heure_fin, conflit.name))

    @api.constrains('salle_id', 'jour_semaine', 'heure_debut', 'heure_fin')
    def _check_conflit_salle(self):
        for rec in self:
            domain = rec._get_overlap_domain() + [('salle_id', '=', rec.salle_id.id)]
            conflit = self.search(domain, limit=1)
            if conflit:
                raise ValidationError(
                    "Conflit d'emploi du temps : la salle %s est déjà occupée le %s "
                    "de %.2fh à %.2fh par le cours « %s »."
                    % (rec.salle_id.name, dict(rec._fields['jour_semaine'].selection).get(rec.jour_semaine),
                       conflit.heure_debut, conflit.heure_fin, conflit.name))

    @api.constrains('salle_id', 'classe_id')
    def _check_capacite_salle(self):
        for rec in self:
            if rec.salle_id and rec.classe_id:
                effectif = rec.classe_id.effectif
                if rec.salle_id.capacite_max and effectif > rec.salle_id.capacite_max:
                    raise ValidationError(
                        "La classe %s compte %s élèves, ce qui dépasse la capacité maximale "
                        "de la salle %s (%s places) !"
                        % (rec.classe_id.name, effectif, rec.salle_id.name, rec.salle_id.capacite_max))

    @api.constrains('jour_semaine', 'heure_debut', 'heure_fin', 'etablissement_id')
    def _check_pause_institutionnelle(self):
        for rec in self:
            pauses = self.env['adk.pause'].search([
                ('etablissement_id', '=', rec.etablissement_id.id),
                ('jour_semaine', '=', rec.jour_semaine),
            ])
            for pause in pauses:
                if rec.heure_debut < pause.heure_fin and rec.heure_fin > pause.heure_debut:
                    raise ValidationError(
                        "Ce créneau chevauche la pause institutionnelle « %s » (%.2fh - %.2fh). "
                        "Aucun cours académique ne peut être planifié durant cette plage."
                        % (pause.name, pause.heure_debut, pause.heure_fin))
