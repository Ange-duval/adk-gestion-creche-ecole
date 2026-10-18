# ADK Gestion Crèche & École
Module Odoo 18.0 — Smart ERP Éducation (licence OPL-1)

## Contenu
- **Infrastructure** : Établissement → Bâtiment → Étage → Salle
- **Programmes académiques** : matières, classes, sessions de cours, emplois du temps avec anti-conflits
- **Acteurs** : élèves, parents (portail), enseignants/nounous, intendants, bibliothécaires
- **Vie scolaire** : présences (appel ou badge QR), notes, bulletins PDF
- **Logistique** : bibliothèque, librairie, badges CR80 avec QR code
- **Facturation de la scolarité** : grilles tarifaires, dossier de scolarité par élève et par année,
  facture générée en un clic, paiements par tranches jusqu'à un solde de zéro, reportés dans la
  comptabilité native (Clients > Factures, Clients > Paiements)
- **Rapports de direction (PDF)** : 01 historique élève, 02 recettes par élève, 03 synthèse financière,
  04 impayés, 05 par grille tarifaire, 06 journal des encaissements, 07 effectifs, 08 bilan annuel

## Installation
1. Copier le dossier `adk_gestion_creche_ecole` dans le répertoire `addons` d'Odoo 18.
2. Redémarrer Odoo avec `-u adk_gestion_creche_ecole` ou mettre à jour la liste des applications.
3. Installer « ADK Gestion Crèche & École ».
4. Dépendances : `base`, `mail`, `hr`, `hr_holidays`, `product`, `account`, `portal`, `web`.

## Prise en main de la facturation
1. *Facturation scolaire > Grilles tarifaires* : créer une grille (rubriques, périodicité, tranches).
2. *Facturation scolaire > Dossiers de scolarité* : créer un dossier, ou
   *Générer les factures de scolarité* pour toute une classe.
3. Sur le dossier : **Créer la facture**, puis **Enregistrer un paiement** autant de fois que nécessaire.
4. Définir le journal de vente sur la fiche de l'établissement (sinon le premier journal de vente est utilisé).

## Groupes de sécurité
- **Directeur / Administrateur** : accès complet
- **Enseignant / Nounou** : notes, présences, bulletins de ses classes
- **Intendant** : badges, pointages, salles, dossiers de scolarité, rapports
- **Bibliothécaire** : livres et prêts
- **Parent (Portail)** : fiches, notes, bulletins, présences et dossiers de ses enfants uniquement

## Support
Kambeu Henang Ange Duval — duvalkambeu61@gmail.com
