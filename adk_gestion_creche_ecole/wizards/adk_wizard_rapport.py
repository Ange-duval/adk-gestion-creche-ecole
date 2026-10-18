# -*- coding: utf-8 -*-
from collections import OrderedDict
from datetime import date, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

MOIS_FR = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août',
           'septembre', 'octobre', 'novembre', 'décembre']

TYPES_RAPPORT = [
    ('01', "01 · Historique financier individuel d'un élève"),
    ('02', "02 · Rapport général des recettes par élève"),
    ('03', "03 · Synthèse financière de la scolarité"),
    ('04', "04 · État des impayés et soldes restants"),
    ('05', "05 · Rapport par grille tarifaire"),
    ('06', "06 · Journal des encaissements"),
    ('07', "07 · Rapport des effectifs scolaires"),
    ('08', "08 · Bilan annuel de l'année académique"),
]


class AdkWizardRapport(models.TransientModel):
    _name = 'adk.wizard.rapport'
    _description = "Assistant : rapports de gestion scolaire (PDF)"

    type_rapport = fields.Selection(TYPES_RAPPORT, string="Rapport", required=True, default='02')
    annee_scolaire_id = fields.Many2one(
        'adk.annee.scolaire', string="Année académique",
        default=lambda self: self.env['adk.annee.scolaire']._get_or_create_courante())
    etablissement_id = fields.Many2one('adk.etablissement', string="Établissement",
                                       help="Laisser vide pour tous les établissements.")
    date_debut = fields.Date(string="Date de début")
    date_fin = fields.Date(string="Date de fin", default=fields.Date.context_today)
    date_arret = fields.Date(string="Date d'arrêté", default=fields.Date.context_today)
    eleve_id = fields.Many2one('adk.eleve', string="Élève")
    classe_id = fields.Many2one('adk.classe', string="Classe")
    niveau_id = fields.Many2one('adk.niveau', string="Niveau")
    grille_id = fields.Many2one('adk.grille.tarifaire', string="Grille tarifaire")
    caissier_id = fields.Many2one('res.users', string="Caissier / utilisateur")
    statut_paiement = fields.Selection([
        ('all', 'Tous'), ('impaye', 'Aucun paiement'), ('partiel', 'Partiellement payés'),
        ('paye', 'Soldés'),
    ], string="Statut de paiement", default='all')
    solde_min = fields.Float(string="Solde minimum")
    retard_min = fields.Integer(string="Retard minimum (jours)")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # ------------------------------------------------------------------ défauts
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        annee = self.env['adk.annee.scolaire']._get_or_create_courante()
        today = fields.Date.context_today(self)
        res['date_debut'] = annee.date_debut or today.replace(month=1, day=1)
        return res

    @api.onchange('annee_scolaire_id')
    def _onchange_annee(self):
        if self.annee_scolaire_id:
            if self.annee_scolaire_id.date_debut:
                self.date_debut = self.annee_scolaire_id.date_debut
            if self.annee_scolaire_id.date_fin and self.annee_scolaire_id.date_fin < fields.Date.context_today(self):
                self.date_fin = self.annee_scolaire_id.date_fin
                self.date_arret = self.annee_scolaire_id.date_fin

    # ------------------------------------------------------------------ impression
    def action_imprimer(self):
        self.ensure_one()
        self._build_data()  # valide les paramètres avant de lancer le PDF
        return self.env.ref('adk_gestion_creche_ecole.action_report_rapport_gestion').report_action(self)

    # ------------------------------------------------------------------ formats
    def _money(self, amount):
        cur = self.currency_id or self.env.company.currency_id
        txt = '{:,.{d}f}'.format(amount or 0.0, d=cur.decimal_places).replace(',', ' ')
        # Les espaces ordinaires évitent les glyphes parasites dans certains moteurs PDF.
        return '%s %s' % (txt, cur.symbol or cur.name)

    @staticmethod
    def _d(value):
        return value.strftime('%d/%m/%Y') if value else '—'

    @staticmethod
    def _pct(num, den):
        return '%s %%' % ('{:.1f}'.format((num / den * 100.0) if den else 0.0).replace('.', ','))

    def _scope_label(self):
        return self.etablissement_id.name or "Établissement complet"

    def _annee_label(self):
        return self.annee_scolaire_id.name or "Toutes les années"

    # ------------------------------------------------------------------ sélection des données
    def _dossiers(self, etats=('facture', 'partiel', 'paye'), avec_eleve=True):
        domain = [('etat', 'in', list(etats))]
        if self.annee_scolaire_id:
            domain.append(('annee_scolaire_id', '=', self.annee_scolaire_id.id))
        if self.etablissement_id:
            domain.append(('etablissement_id', '=', self.etablissement_id.id))
        if self.classe_id:
            domain.append(('classe_id', '=', self.classe_id.id))
        if self.niveau_id:
            domain.append(('classe_id.niveau_id', '=', self.niveau_id.id))
        if self.grille_id:
            domain.append(('grille_id', '=', self.grille_id.id))
        if avec_eleve and self.eleve_id:
            domain.append(('eleve_id', '=', self.eleve_id.id))
        return self.env['adk.dossier.scolarite'].search(domain)

    def _periode(self):
        debut = self.date_debut or date.min
        fin = self.date_fin or fields.Date.context_today(self)
        if debut > fin:
            raise UserError("La date de début doit précéder la date de fin.")
        return debut, fin

    def _kpi_table(self, kpis):
        return [{'label': k, 'value': v} for k, v in kpis]

    # ------------------------------------------------------------------ construction
    def _build_data(self):
        self.ensure_one()
        builder = getattr(self, '_build_%s' % self.type_rapport)
        data = builder()
        data.setdefault('tables', [])
        data.setdefault('kpis', [])
        data.setdefault('meta', [])
        data.setdefault('bars', [])
        data.setdefault('note', '')
        data.setdefault('signature', False)
        data['modele'] = self.type_rapport
        data['annee'] = self._annee_label()
        data['etablissement'] = self._scope_label()
        data['date_edition'] = self._d(fields.Date.context_today(self))
        return data

    # 01 ---------------------------------------------------------------
    def _build_01(self):
        if not self.eleve_id:
            raise UserError("Sélectionnez l'élève dont vous voulez l'historique financier.")
        debut, fin = self._periode()
        dossiers = self._dossiers()
        rows, paye_periode, paye_cumul, brut, net = [], 0.0, 0.0, 0.0, 0.0
        for d in dossiers:
            brut += d.montant_brut
            net += d.montant_net
            for det in d._get_paiements_detail():
                if det['date'] <= fin:
                    paye_cumul += det['amount']
                if debut <= det['date'] <= fin:
                    paye_periode += det['amount']
                    rows.append((det['date'], [
                        self._d(det['date']), det['ref'] or '', '%s · %s' % (d.name, d.grille_id.name or '—'),
                        det['journal'].name or '', self._money(det['amount'])]))
        rows.sort(key=lambda r: r[0])
        solde = max(net - paye_cumul, 0.0)
        eleve = self.eleve_id
        return {
            'titre': "Historique financier individuel d'un élève",
            'sous_titre': "Relevé nominatif des paiements et du solde pour une période donnée.",
            'meta': [("Élève", eleve.name), ("Classe", eleve.classe_id.name or '—'),
                     ("Période", "%s – %s" % (self._d(debut), self._d(fin))), ("Année", self._annee_label())],
            'kpis': self._kpi_table([("FRAIS ATTENDUS", self._money(net)),
                                     ("TOTAL PAYÉ (PÉRIODE)", self._money(paye_periode)),
                                     ("SOLDE RESTANT", self._money(solde))]),
            'tables': [
                {'title': "Détail des paiements",
                 'cols': [("Date", 'l'), ("Référence", 'l'), ("Motif / échéance", 'l'), ("Mode", 'l'),
                          ("Montant payé", 'r')],
                 'rows': [r[1] for r in rows] or [["Aucun paiement sur la période", '', '', '', '']],
                 'total': ["Total payé", '', '', '', self._money(paye_periode)]},
                {'title': "Résumé de facturation",
                 'cols': [("Frais bruts", 'r'), ("Remise", 'r'), ("Net à payer", 'r'),
                          ("Déjà payé (cumul)", 'r'), ("Solde", 'r')],
                 'rows': [[self._money(brut), self._money(brut - net), self._money(net),
                           self._money(paye_cumul), self._money(solde)]]},
            ],
            'note': "Le solde restant = montant net dû, diminué des paiements comptabilisés jusqu'à la "
                    "date de fin de période.",
        }

    # helpers regroupement par élève
    def _par_eleve(self, dossiers, debut, fin):
        data = OrderedDict()
        for d in dossiers.sorted(lambda x: (x.eleve_id.name or '')):
            e = data.setdefault(d.eleve_id, {'net': 0.0, 'periode': 0.0, 'cumul': 0.0, 'dernier': False,
                                             'retard': 0, 'dossiers': self.env['adk.dossier.scolarite']})
            e['net'] += d.montant_net
            e['dossiers'] |= d
            for det in d._get_paiements_detail():
                if det['date'] <= fin:
                    e['cumul'] += det['amount']
                    if not e['dernier'] or det['date'] > e['dernier']:
                        e['dernier'] = det['date']
                if debut <= det['date'] <= fin:
                    e['periode'] += det['amount']
        return data

    # 02 ---------------------------------------------------------------
    def _build_02(self):
        debut, fin = self._periode()
        dossiers = self._dossiers()
        par_eleve = self._par_eleve(dossiers, debut, fin)
        rows, nb_paye, tot_periode, tot_solde, tot_net = [], 0, 0.0, 0.0, 0.0
        n = 0
        for eleve, e in par_eleve.items():
            solde = max(e['net'] - e['cumul'], 0.0)
            statut = 'paye' if solde <= 0 else ('partiel' if e['cumul'] > 0 else 'impaye')
            if self.statut_paiement != 'all' and statut != self.statut_paiement:
                continue
            n += 1
            rows.append([str(n), eleve.name, eleve.classe_id.name or '—', self._money(e['net']),
                         self._money(e['periode']), self._money(solde)])
            nb_paye += 1 if e['periode'] > 0 else 0
            tot_periode += e['periode']
            tot_solde += solde
            tot_net += e['net']
        return {
            'titre': "Rapport général des recettes par élève",
            'sous_titre': "Vue détaillée des montants encaissés par élève sur la période.",
            'meta': [("Période", "%s – %s" % (self._d(debut), self._d(fin))),
                     ("Classe", self.classe_id.name or "Toutes les classes"),
                     ("Année académique", self._annee_label())],
            'kpis': self._kpi_table([("ÉLÈVES AVEC PAIEMENT", str(nb_paye)),
                                     ("RECETTES ENCAISSÉES", self._money(tot_periode)),
                                     ("SOLDES RESTANTS", self._money(tot_solde))]),
            'tables': [{
                'title': '',
                'cols': [("N°", 'l'), ("Élève", 'l'), ("Classe", 'l'), ("Montant net dû", 'r'),
                         ("Payé sur période", 'r'), ("Solde restant", 'r')],
                'rows': rows or [['', "Aucune donnée", '', '', '', '']],
                'total': ["", "TOTAL GÉNÉRAL", "", self._money(tot_net), self._money(tot_periode),
                          self._money(tot_solde)]}],
            'note': "Le solde restant est calculé à la date de fin de période (net dû − paiements comptabilisés).",
        }

    # 03 ---------------------------------------------------------------
    def _build_03(self):
        debut, fin = self._periode()
        dossiers = self._dossiers().filtered(lambda d: d.date_facture <= fin)
        net = sum(dossiers.mapped('montant_net'))
        mois = OrderedDict()
        cur = debut.replace(day=1)
        while cur <= fin:
            mois[(cur.year, cur.month)] = 0.0
            cur = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
        cumul_fin, periode = 0.0, 0.0
        for d in dossiers:
            for det in d._get_paiements_detail():
                if det['date'] <= fin:
                    cumul_fin += det['amount']
                if debut <= det['date'] <= fin:
                    periode += det['amount']
                    mois[(det['date'].year, det['date'].month)] += det['amount']
        reste = max(net - cumul_fin, 0.0)
        rows, run = [], 0.0
        for (y, m), val in mois.items():
            run += val
            rows.append(["%s %s" % (MOIS_FR[m - 1].capitalize(), y), self._money(val),
                         self._pct(val, periode), self._money(run)])
        return {
            'titre': "Synthèse financière de la scolarité",
            'sous_titre': "Vue de direction sur les montants attendus, encaissés et restant à recouvrer.",
            'meta': [("Période", "%s – %s" % (self._d(debut), self._d(fin))), ("Périmètre", self._scope_label()),
                     ("Année", self._annee_label())],
            'kpis': self._kpi_table([("FRAIS NETS ATTENDUS", self._money(net)),
                                     ("ENCAISSÉ (PÉRIODE)", self._money(periode)),
                                     ("RESTE À RECOUVRER", self._money(reste)),
                                     ("TAUX DE RECOUVREMENT", self._pct(cumul_fin, net))]),
            'tables': [
                {'title': "Évolution des encaissements",
                 'cols': [("Mois", 'l'), ("Montant encaissé", 'r'), ("Part du total", 'r'), ("Cumul", 'r')],
                 'rows': rows, 'total': ["Total période", self._money(periode), "100 %", self._money(periode)]},
                {'title': "Indicateurs",
                 'cols': [("Indicateur", 'l'), ("Définition retenue", 'l')],
                 'rows': [["Frais nets attendus", "Frais facturés moins remises et bourses accordées"],
                          ["Encaissé", "Somme des paiements comptabilisés sur la période"],
                          ["Reste à recouvrer", "Net attendu − paiements cumulés à la date de fin"],
                          ["Taux de recouvrement", "Paiements cumulés à la date de fin ÷ frais nets attendus × 100"]]},
            ],
        }

    # 04 ---------------------------------------------------------------
    def _build_04(self):
        arret = self.date_arret or fields.Date.context_today(self)
        dossiers = self._dossiers().filtered(lambda d: d.date_facture <= arret)
        par_eleve = self._par_eleve(dossiers, date.min, arret)
        rows, total, retard_max = [], 0.0, 0
        for eleve, e in par_eleve.items():
            solde = e['net'] - e['cumul']
            if solde <= 0.0001 or solde < (self.solde_min or 0.0):
                continue
            retard = max([d._retard_jours(arret) for d in e['dossiers']] or [0])
            if retard < (self.retard_min or 0):
                continue
            e['retard'] = retard
            e['solde'] = solde
        elig = [(el, e) for el, e in par_eleve.items() if e.get('solde')]
        elig.sort(key=lambda x: -x[1]['solde'])
        for eleve, e in elig:
            total += e['solde']
            retard_max = max(retard_max, e['retard'])
            rows.append([eleve.name, eleve.classe_id.name or '—', self._money(e['net']), self._money(e['cumul']),
                         self._money(e['solde']), self._d(e['dernier']), str(e['retard'])])
        return {
            'titre': "État des impayés et soldes restants",
            'sous_titre': "Liste des dossiers présentant un solde positif à la date d'arrêté.",
            'meta': [("Date d'arrêté", self._d(arret)), ("Classe", self.classe_id.name or "Toutes les classes"),
                     ("Année", self._annee_label())],
            'kpis': self._kpi_table([("ÉLÈVES DÉBITEURS", str(len(elig))),
                                     ("TOTAL DES IMPAYÉS", self._money(total)),
                                     ("PLUS ANCIEN RETARD", "%s jours" % retard_max)]),
            'tables': [{
                'title': '',
                'cols': [("Élève", 'l'), ("Classe", 'l'), ("Net à payer", 'r'), ("Payé", 'r'), ("Solde", 'r'),
                         ("Dernier paiement", 'l'), ("Retard (j)", 'r')],
                'rows': rows or [["Aucun impayé à cette date", '', '', '', '', '', '']],
                'total': ["TOTAL", '', '', '', self._money(total), '', '']}],
            'note': "Un solde nul n'apparaît pas dans cet état. Le retard est mesuré depuis la plus ancienne "
                    "échéance non soldée.",
        }

    # 05 ---------------------------------------------------------------
    def _build_05(self):
        debut, fin = self._periode()
        dossiers = self._dossiers().filtered(lambda d: d.date_facture <= fin)
        groupes = OrderedDict()
        periodicites = dict(self.env['adk.grille.tarifaire']._fields['periodicite'].selection)
        for d in dossiers:
            g = groupes.setdefault(d.grille_id, {'eleves': set(), 'net': 0.0, 'enc': 0.0})
            g['eleves'].add(d.eleve_id.id)
            g['net'] += d.montant_net
            g['enc'] += d._paye_a_date(fin)
        rows, bars = [], []
        tot = {'eleves': set(), 'net': 0.0, 'enc': 0.0}
        maxi = max([g['net'] for g in groupes.values()] or [1.0]) or 1.0
        for grille, g in sorted(groupes.items(), key=lambda x: -x[1]['net']):
            solde = max(g['net'] - g['enc'], 0.0)
            nom = grille.name or "Sans grille"
            rows.append([nom, periodicites.get(grille.periodicite, '—') if grille else '—',
                         str(len(g['eleves'])), self._money(g['net']), self._money(g['enc']),
                         self._money(solde), self._pct(g['enc'], g['net'])])
            bars.append({'label': nom, 'series': [
                ("Net attendu", g['net'] / maxi * 100, self._money(g['net']), '#714B67'),
                ("Encaissé", g['enc'] / maxi * 100, self._money(g['enc']), '#21B799'),
                ("Solde", solde / maxi * 100, self._money(solde), '#E86A5E')]})
            tot['eleves'] |= g['eleves']
            tot['net'] += g['net']
            tot['enc'] += g['enc']
        solde_tot = max(tot['net'] - tot['enc'], 0.0)
        return {
            'titre': "Rapport par grille tarifaire",
            'sous_titre': "Analyse des recettes par grille tarifaire configurée.",
            'meta': [("Période", "%s – %s" % (self._d(debut), self._d(fin))), ("Regroupement", "Grille tarifaire"),
                     ("Devise", (self.currency_id.name or ''))],
            'kpis': self._kpi_table([("GRILLES ACTIVES", str(len(groupes))),
                                     ("RECETTES", self._money(tot['enc'])), ("SOLDE", self._money(solde_tot))]),
            'tables': [{
                'title': '',
                'cols': [("Grille", 'l'), ("Périodicité", 'l'), ("Élèves", 'r'), ("Net attendu", 'r'),
                         ("Encaissé", 'r'), ("Solde", 'r'), ("Recouvrement", 'r')],
                'rows': rows or [["Aucune donnée", '', '', '', '', '', '']],
                'total': ["TOTAL", '', str(len(tot['eleves'])), self._money(tot['net']), self._money(tot['enc']),
                          self._money(solde_tot), self._pct(tot['enc'], tot['net'])]}],
            'bars': bars,
            'note': "La périodicité provient de la configuration de chaque grille, jamais du nom de la grille.",
        }

    # 06 ---------------------------------------------------------------
    def _build_06(self):
        debut, fin = self._periode()
        dossiers = self._dossiers(etats=('facture', 'partiel', 'paye'))
        ops = []
        for d in dossiers:
            for det in d._get_paiements_detail():
                if not (debut <= det['date'] <= fin):
                    continue
                if self.caissier_id and det['user'] != self.caissier_id:
                    continue
                ops.append((d, det))
        ops.sort(key=lambda x: (x[1]['date'], x[1]['create_date'] or fields.Datetime.now()))
        rows, total, especes = [], 0.0, 0.0
        for d, det in ops:
            heure = ''
            if det['create_date']:
                heure = ' ' + fields.Datetime.context_timestamp(self, det['create_date']).strftime('%H:%M')
            rows.append(["%s%s" % (self._d(det['date']), heure), det['ref'] or '', d.eleve_id.name,
                         det['journal'].name or '', det['user'].name or '', self._money(det['amount'])])
            total += det['amount']
            if det['journal'].type == 'cash':
                especes += det['amount']
        return {
            'titre': "Journal des encaissements",
            'sous_titre': "Journal chronologique des paiements enregistrés et comptabilisés.",
            'meta': [("Date début", self._d(debut)), ("Date fin", self._d(fin)),
                     ("Caissier", self.caissier_id.name or "Tous les utilisateurs")],
            'kpis': self._kpi_table([("OPÉRATIONS", str(len(ops))), ("TOTAL ENCAISSÉ", self._money(total)),
                                     ("ESPÈCES", self._money(especes)),
                                     ("AUTRES MOYENS", self._money(total - especes))]),
            'tables': [{
                'title': '',
                'cols': [("Date / heure", 'l'), ("Référence", 'l'), ("Élève", 'l'), ("Mode de paiement", 'l'),
                         ("Enregistré par", 'l'), ("Montant", 'r')],
                'rows': rows or [["Aucun encaissement sur la période", '', '', '', '', '']],
                'total': ["TOTAL", '', '', '', '', self._money(total)]}],
            'note': "Seuls les paiements comptabilisés et lettrés à une facture de scolarité sont retenus ; "
                    "les paiements annulés ou en brouillon sont exclus.",
        }

    # 07 / 08 helpers -----------------------------------------------------
    def _effectifs(self, arret):
        domain = [('active', '=', True)]
        if self.annee_scolaire_id:
            domain.append(('annee_scolaire_id', '=', self.annee_scolaire_id.id))
        if self.etablissement_id:
            domain.append(('etablissement_id', '=', self.etablissement_id.id))
        eleves = self.env['adk.eleve'].search(domain)
        annee = self.annee_scolaire_id

        def est_nouveau(e):
            d = e.date_inscription or (e.create_date and e.create_date.date())
            if not d:
                return False
            if annee.date_debut and annee.date_fin:
                return annee.date_debut <= d <= annee.date_fin
            return d.year == arret.year
        nb_classes = self.env['adk.classe'].search_count(
            [('active', '=', True)]
            + ([('annee_scolaire_id', '=', annee.id)] if annee else [])
            + ([('etablissement_id', '=', self.etablissement_id.id)] if self.etablissement_id else []))
        edomain = [('is_adk_enseignant', '=', True)]
        if self.etablissement_id:
            edomain.append(('etablissement_ids', 'in', self.etablissement_id.id))
        nb_ens = self.env['hr.employee'].search_count(edomain)
        return eleves, est_nouveau, nb_classes, nb_ens

    # 07 ---------------------------------------------------------------
    def _build_07(self):
        arret = self.date_arret or fields.Date.context_today(self)
        eleves, est_nouveau, nb_classes, nb_ens = self._effectifs(arret)
        groupes = OrderedDict()
        for niveau in self.env['adk.niveau'].search([]):
            groupes[niveau.id] = [niveau.name, 0, 0]
        groupes[0] = ["Sans niveau", 0, 0]
        for e in eleves:
            key = e.classe_id.niveau_id.id or 0
            g = groupes.setdefault(key, ["Sans niveau", 0, 0])
            g[1] += 1
            g[2] += 1 if est_nouveau(e) else 0
        total = len(eleves)
        nouveaux = sum(g[2] for g in groupes.values())
        rows = [[g[0], str(g[1]), str(g[2]), self._pct(g[1], total)] for g in groupes.values() if g[1]]
        return {
            'titre': "Rapport des effectifs scolaires",
            'sous_titre': "État des inscriptions par niveau scolaire.",
            'meta': [("Date de référence", self._d(arret)), ("Année académique", self._annee_label()),
                     ("Statut", "Élèves inscrits")],
            'kpis': self._kpi_table([("EFFECTIF TOTAL", str(total)), ("NOUVEAUX INSCRITS", str(nouveaux)),
                                     ("CLASSES", str(nb_classes)), ("ENSEIGNANTS", str(nb_ens))]),
            'tables': [{
                'title': '',
                'cols': [("Niveau", 'l'), ("Effectif", 'r'), ("Nouveaux inscrits", 'r'), ("Part de l'effectif", 'r')],
                'rows': rows or [["Aucun élève", '', '', '']],
                'total': ["TOTAL ÉLÈVES", str(total), str(nouveaux), "100 %"]}],
            'note': "Le personnel enseignant est un indicateur distinct et n'est pas ajouté à l'effectif des élèves.",
        }

    # 08 ---------------------------------------------------------------
    def _build_08(self):
        if not self.annee_scolaire_id:
            raise UserError("Choisissez l'année académique du bilan.")
        annee = self.annee_scolaire_id
        fin = self.date_fin or annee.date_fin or fields.Date.context_today(self)
        dossiers = self._dossiers(avec_eleve=False).filtered(lambda d: d.date_facture <= fin)
        brut = sum(dossiers.mapped('montant_brut'))
        net = sum(dossiers.mapped('montant_net'))
        enc = sum(d._paye_a_date(fin) for d in dossiers)
        reste = max(net - enc, 0.0)
        eleves, est_nouveau, nb_classes, nb_ens = self._effectifs(fin)
        nouveaux = len([e for e in eleves if est_nouveau(e)])
        periode = "%s – %s" % (self._d(annee.date_debut), self._d(annee.date_fin)) if annee.date_debut else annee.name
        return {
            'titre': "Bilan annuel de l'année académique",
            'sous_titre': "Synthèse administrative et financière à présenter à la direction.",
            'meta': [("Année académique", annee.name), ("Période", periode),
                     ("Établissement", self._scope_label())],
            'kpis': self._kpi_table([("ÉLÈVES INSCRITS", str(len(eleves))), ("FRAIS NETS ATTENDUS", self._money(net)),
                                     ("RECETTES ENCAISSÉES", self._money(enc)),
                                     ("SOLDE À RECOUVRER", self._money(reste))]),
            'tables': [
                {'title': "Synthèse financière",
                 'cols': [("Indicateur", 'l'), ("Montant / valeur", 'r'), ("Commentaire", 'l')],
                 'rows': [["Frais bruts facturés", self._money(brut), "Avant remises"],
                          ["Remises accordées", self._money(brut - net), "Remises et bourses"],
                          ["Frais nets attendus", self._money(net), "Après remises"],
                          ["Paiements encaissés", self._money(enc), "Paiements comptabilisés à %s" % self._d(fin)],
                          ["Solde à recouvrer", self._money(reste), "À la date de clôture"],
                          ["Taux de recouvrement", self._pct(enc, net), "Encaissé / frais nets attendus"]]},
                {'title': "Synthèse administrative",
                 'cols': [("Indicateur", 'l'), ("Valeur", 'r')],
                 'rows': [["Effectif élèves inscrits", str(len(eleves))], ["Nouveaux inscrits", str(nouveaux)],
                          ["Nombre de classes", str(nb_classes)], ["Personnel enseignant", str(nb_ens)]]},
            ],
            'signature': True,
        }
