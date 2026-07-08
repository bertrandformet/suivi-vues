# Contexte pour le passage design

## Objectif du produit
Tableau de bord de suivi de l'évolution des vues/écoutes d'URLs ciblées sur 11 plateformes vidéo et podcast (YouTube, PeerTube, Apple Podcasts, Spotify, Podcast Addict, Deezer, Pocket Casts, Castbox, Overcast, Castro, Canotech). Le contenu suivi n'appartient pas à l'utilisateur — c'est un outil de veille/suivi, pas un dashboard créateur.

## Rôles et parcours
- **Admin** (éditeur) : accès aux 5 pages — Tableau de bord, Ajouter une vue, Gérer les URLs, Importer un fichier, Collecte automatique.
- **Lecteur** : accès à la seule page Tableau de bord (consultation).
La navigation latérale change selon le rôle (voir captures 02 vs 07).

## Contrainte technique
Application construite avec **Streamlit** (Python). Les retours doivent rester actionnables dans ce cadre : mise en page, hiérarchie visuelle, couleurs, densité d'information, copy, disposition des widgets natifs (formulaires, selectbox, tableaux, graphiques Plotly). Les interactions totalement custom (drag&drop avancé, layouts non supportés nativement) demanderaient un développement significatif hors Streamlit.

## Collecte des données
- YouTube et PeerTube : collecte automatique (API), déclenchable à la demande ou hebdomadaire.
- Les 9 autres plateformes : saisie manuelle ou import de fichier (aucune n'expose de compteur de vues public pour du contenu dont on n'est pas propriétaire).

## Captures fournies
1. `01_connexion.png` — écran de connexion
2. `02_tableau_de_bord_admin.png` — tableau de bord (courbe d'évolution, comparaison par plateforme, table d'audit)
3. `03_ajouter_une_vue.png` — formulaire de saisie/ajustement d'un relevé
4. `04_gerer_les_urls.png` — création de contenu + ajout d'URL suivie + liste
5. `05_importer_un_fichier.png` — import CSV/Excel
6. `06_collecte_automatique.png` — liste des URLs auto-collectées + déclenchement manuel
7. `07_tableau_de_bord_lecteur.png` — même tableau de bord, vu côté lecteur (nav réduite)

Toutes les captures utilisent des données de démonstration (aucune donnée réelle).

## Questions à poser au design review
- La hiérarchie visuelle du tableau de bord (filtres → courbe → comparaison → audit) est-elle claire au premier coup d'œil ?
- Le code couleur par URL/plateforme sur les graphiques aide-t-il ou surcharge-t-il ?
- Le formulaire "Ajouter une vue" est-il assez rapide à remplir pour un usage fréquent (admin) ?
- Les distinctions de rôle (lecteur vs admin) sont-elles suffisamment lisibles dans l'interface ?
- Y a-t-il des problèmes d'accessibilité (contraste, taille des zones cliquables) à corriger ?
