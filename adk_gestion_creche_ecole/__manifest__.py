# -*- coding: utf-8 -*-
{
    'name': "ADK Gestion Crèche & École",
    'version': '18.0.1.2.0',
    'category': 'Education',
    'summary': "Gestion complète d'une crèche ou d'une école : élèves, classes, emplois du temps, "
               "bulletins, badges QR, facturation de la scolarité, paiements et rapports de direction",
    'description': """
ADK Gestion Crèche & École pour Odoo 18
=======================================
* Infrastructure : Établissement > Bâtiment > Étage > Salle
* Classes, matières, sessions de cours, emplois du temps avec anti-conflits
* Élèves, parents (portail), enseignants, intendants, bibliothécaires
* Présences par badge QR, notes, bulletins PDF
* Bibliothèque, librairie, badges d'accès CR80
* Facturation de la scolarité : grilles tarifaires, dossier de scolarité par élève,
  facture et paiements par tranches jusqu'à solde zéro, reportés dans la comptabilité Odoo
* 8 rapports PDF de direction : historique élève, recettes, synthèse, impayés,
  par grille tarifaire, journal des encaissements, effectifs, bilan annuel
""",
    'author': "Kambeu Henang Ange Duval",
    'maintainer': "Kambeu Henang Ange Duval",
    'support': "duvalkambeu61@gmail.com",
    'license': 'OPL-1',
    'price': 39.0,
    'currency': 'EUR',
    'depends': [
        'base',
        'mail',
        'hr',
        'hr_holidays',
        'product',
        'account',
        'portal',
        'web',
    ],
    'assets': {
        'web.assets_backend': [
            'adk_gestion_creche_ecole/static/src/scss/adk_dashboard.scss',
            'adk_gestion_creche_ecole/static/src/js/adk_dashboard.js',
            'adk_gestion_creche_ecole/static/src/xml/adk_dashboard_templates.xml',
        ],
    },
    'data': [
        # Sécurité
        'security/adk_security_groups.xml',
        'security/ir.model.access.csv',
        'security/adk_security_rules.xml',

        # Données
        'data/adk_sequence_data.xml',
        'data/adk_sequence_scolarite.xml',
        'data/adk_parametrage_data.xml',
        'data/adk_cron_data.xml',

        # Vues - Paramétrage (années académiques, périodes, types d'évaluation, niveaux)
        'views/adk_parametrage_views.xml',

        # Vues - Infrastructure
        'views/adk_etablissement_views.xml',
        'views/adk_batiment_views.xml',
        'views/adk_etage_views.xml',
        'views/adk_salle_views.xml',

        # Vues - Programmes académiques
        'views/adk_matiere_views.xml',
        'views/adk_classe_views.xml',
        'views/adk_session_cours_views.xml',
        'views/adk_emploi_temps_views.xml',
        'views/adk_pause_views.xml',

        # Vues - Acteurs
        'views/adk_eleve_views.xml',
        'views/hr_employee_views.xml',
        'views/res_partner_views.xml',

        # Vues - Vie scolaire
        'views/adk_presence_views.xml',
        'views/adk_note_views.xml',
        'views/adk_bulletin_views.xml',

        # Vues - Logistique
        'views/adk_livre_views.xml',
        'views/adk_pret_livre_views.xml',
        'views/adk_article_fourniture_views.xml',

        # Vues - Sécurité / Badges
        'views/adk_badge_views.xml',
        'views/adk_pointage_views.xml',

        # Vues - Facturation scolaire
        'views/adk_scolarite_views.xml',

        # Assistants
        'wizards/adk_wizard_bulletin_views.xml',
        'wizards/adk_wizard_badge_views.xml',
        'wizards/adk_wizard_saisie_notes_views.xml',
        'wizards/adk_wizard_facturation_views.xml',
        'wizards/adk_wizard_scolarite_views.xml',
        'wizards/adk_wizard_rapport_views.xml',

        # Rapports
        'report/adk_report_actions.xml',
        'report/adk_bulletin_report_template.xml',
        'report/adk_badge_report_template.xml',
        'report/adk_rapport_gestion_templates.xml',

        # Données dépendant des rapports (référence action_report_bulletin)
        'data/adk_mail_template_data.xml',

        # Tableau de bord (chargé avant les menus car réutilisé par le menu racine)
        'views/adk_dashboard_views.xml',

        # Menus (chargé en dernier car dépend de toutes les actions)
        'views/adk_menus.xml',
    ],
    'demo': [
        'data/adk_demo_data.xml',
    ],
    'images': ['static/description/banner.png', 'static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
