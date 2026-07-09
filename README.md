# Suivi Vues

Suivi de l'évolution des vues d'URLs ciblées sur YouTube, PeerTube, Apple Podcasts, Spotify, Podcast Addict, Deezer, Pocket Casts, Castbox, Overcast, Castro, etc.

Les données (regroupements, URLs suivies, relevés de vues) sont stockées sous forme de CSV **dans un dépôt GitHub**, lues et écrites via l'API GitHub — chaque ajout ou ajustement crée un commit, ce qui donne un historique d'audit complet sans base de données externe.

Ce dépôt est un **template réutilisable** : il contient des données et des comptes de démonstration (aucune donnée réelle). Pour un usage réel, dupliquez-le en dépôt privé (voir ci-dessous) pour que vos vraies URLs suivies et votre dashboard quotidien ne soient jamais publics.

**Collecte des vues** :
- ✅ **YouTube** et **PeerTube** : collecte automatique (API publique), déclenchable manuellement ou chaque semaine via GitHub Actions.
- **Apple Podcasts, Spotify, Podcast Addict, Deezer, Pocket Casts, Castbox, Overcast, Castro, etc.** : aucune de ces plateformes n'expose publiquement un nombre de vues/écoutes par épisode pour du contenu dont on n'est pas propriétaire — ces relevés restent en saisie manuelle ou en import de fichier. L'architecture (`src/collectors.py`) est prévue pour qu'on puisse ajouter facilement une future source automatique, quelle qu'elle soit.

## 0. Dépôt public (démo) vs dépôt privé (production)

Sur Streamlit Community Cloud (gratuit), une app n'est privée (accès restreint par email) que si elle est déployée depuis un **dépôt GitHub privé** — un seul dépôt privé est permis par compte.

- **Ce dépôt (public)** : gardez-le tel quel, avec ses données de démo et ses mots de passe de démo documentés ci-dessous. Vous pouvez le déployer publiquement sur Streamlit Cloud pour montrer l'outil, ou le partager/forker pour un autre projet.
- **Votre dépôt de production (privé)** : dupliquez ce dépôt (bouton "Use this template" sur GitHub, ou fork rendu privé) dans un nouveau dépôt **privé**. Remplacez le contenu de `data/*.csv` par vos vraies URLs (ou repartez de zéro en ne gardant que les en-têtes), et configurez ses propres secrets (vrai token, vrais mots de passe, vraie clé YouTube). C'est ce dépôt privé qui sera déployé comme l'unique app privée Streamlit Cloud pour un usage quotidien.

Le code est strictement identique entre les deux ; seuls les secrets et les données changent.

## 1. Créer le dépôt GitHub

1. Créez un dépôt sur GitHub (public pour le template/démo, **privé** pour la production) et poussez ce projet dedans :
   ```bash
   git remote add origin git@github.com:<votre-org>/<votre-repo>.git
   git add .
   git commit -m "Initialisation du tableau de bord"
   git push -u origin main
   ```

## 2. Générer un token d'accès GitHub

1. Sur GitHub : Settings → Developer settings → Personal access tokens → Fine-grained tokens.
2. Créez un token limité à ce dépôt, avec la permission **Contents: Read and write**.
3. Conservez-le précieusement, il sera collé dans les secrets Streamlit (jamais dans le code). Ce token est utilisé par l'app Streamlit ; la collecte automatique planifiée (GitHub Actions) utilise un token différent, généré automatiquement (voir étape 6).

## 3. Générer les mots de passe des comptes admin / lecteur

```bash
pip install streamlit-authenticator
python -c "import streamlit_authenticator as stauth; print(stauth.Hasher().hash('votre_mot_de_passe_admin'))"
python -c "import streamlit_authenticator as stauth; print(stauth.Hasher().hash('votre_mot_de_passe_lecteur'))"
```

Copiez chaque hash dans les secrets (voir étape suivante). Pour le déploiement de démo (dépôt public), des mots de passe simples et documentés ici publiquement suffisent ; pour la production, utilisez de vrais mots de passe forts, gardés privés.

## 4. (Optionnel) Créer une clé API YouTube

Nécessaire uniquement pour activer la collecte automatique des vues YouTube :
1. Sur [Google Cloud Console](https://console.cloud.google.com/apis/credentials), créez un projet (gratuit).
2. Activez l'API "YouTube Data API v3".
3. Créez une clé API et copiez-la dans les secrets (étape suivante).

Sans clé, les URLs YouTube resteront en erreur lors de la collecte automatique — elles peuvent en attendant être suivies manuellement.

## 5. Configurer les secrets

Dupliquez `.streamlit/secrets.toml.example` en `.streamlit/secrets.toml` (local, ignoré par git) ou collez son contenu dans le gestionnaire de secrets de Streamlit Cloud. Remplissez :
- `[github]` : le token généré à l'étape 2, le nom du dépôt (`owner/repo`), la branche.
- `[youtube]` : la clé API de l'étape 4 (optionnel).
- `[auth.cookie]` : une clé aléatoire longue (sert à signer le cookie de session).
- `[auth.credentials.usernames.admin]` et `[auth.credentials.usernames.lecteur]` : les hashs générés à l'étape 3.

## 6. Activer la collecte automatique hebdomadaire (GitHub Actions)

Le fichier `.github/workflows/collect.yml` est déjà inclus et se déclenche chaque lundi, plus manuellement depuis l'onglet **Actions** du dépôt (bouton "Run workflow"). Il n'a besoin que d'un seul secret à ajouter vous-même :
1. Sur GitHub : Settings → Secrets and variables → Actions → New repository secret.
2. Ajoutez `YOUTUBE_API_KEY` (même valeur qu'à l'étape 4). Le token d'écriture GitHub est généré automatiquement par Actions, aucun autre secret n'est nécessaire pour ce workflow.

Le déclenchement manuel est aussi possible directement depuis le dashboard (page "Collecte automatique", bouton "Lancer la collecte maintenant"), en plus du cron hebdomadaire.

## 7. Déployer sur Streamlit Community Cloud

1. Sur [share.streamlit.io](https://share.streamlit.io), connectez votre compte GitHub.
2. Créez une nouvelle app à partir de ce dépôt, fichier principal `app.py`.
3. Dans les paramètres de l'app → Secrets, collez le contenu de votre `secrets.toml`.
4. Déployez. L'app est accessible via l'URL fournie par Streamlit ; connectez-vous avec `admin` ou `lecteur`.

Pour le dépôt privé de production, Streamlit Cloud propose une app "privée" (accès restreint à une liste d'emails invités) en plus du login intégré déjà présent dans l'app — à activer dans les paramètres de partage de l'app.

## 8. Utilisation

- **Lecteur** : consulte le Tableau de bord (courbes d'évolution, comparaison par plateforme, table d'audit).
- **Admin** : en plus, peut créer des regroupements, ajouter des URLs à suivre (avec leur méthode de collecte), saisir ou ajuster des relevés de vues, importer des fichiers CSV/Excel, et déclencher la collecte automatique à la demande.
- Chaque relevé est conservé (pas d'édition destructive) : un ajustement est une nouvelle ligne horodatée, cochée « ajustement », avec une note explicative. Les relevés automatiques portent la source « auto ». Un relevé erroné peut aussi être supprimé directement depuis le journal d'audit du tableau de bord, avec une confirmation avant suppression.

### Regrouper les URLs d'un même épisode

Un même épisode (podcast ou vidéo) existe souvent sur plusieurs plateformes à la fois (YouTube, Spotify, Apple Podcasts...). Pour suivre sa performance globale plutôt que plateforme par plateforme, créez un **Regroupement** qui les rassemble :

1. Dans « Regroupements & URLs » → onglet **Créer un regroupement**, donnez-lui un nom (ex. « Mon podcast — Épisode 13 »).
2. Toujours dans « Regroupements & URLs » → onglet **Ajouter une URL suivie**, ajoutez chaque URL de cet épisode (une par plateforme) en la rattachant à ce regroupement via le menu « Rattacher à un regroupement ».
3. Sur le Tableau de bord, le filtre « Regroupement » permet d'isoler cet épisode, et toutes ses URLs partagent la même couleur sur les graphiques (la couleur code le regroupement, jamais la plateforme) pour comparer sa portée d'une plateforme à l'autre.

Une URL peut aussi rester indépendante si elle ne fait partie d'aucun regroupement.

## Passer de deux comptes à plusieurs comptes

L'app est livrée avec exactement deux comptes (`admin`/`lecteur`) pour rester simple, mais ce n'est pas une limite technique : `src/auth.py` lit tout le contenu de `[auth.credentials.usernames.*]` dans les secrets, quel que soit le nombre d'entrées. Voici comment évoluer, du plus simple au plus poussé — tout gratuit et durable, sans revente de données.

**1. Ajouter des comptes individuels (recommandé, rien à développer)**

Dans les secrets Streamlit, dupliquez un bloc `[auth.credentials.usernames.XXX]` par personne, avec son propre nom, son propre mot de passe haché (même commande qu'à l'étape 3) et son rôle (`editeur` ou `lecteur`) :

```toml
[auth.credentials.usernames.marie]
name = "Marie"
password = "$2b$12$..."
role = "editeur"

[auth.credentials.usernames.julien]
name = "Julien"
password = "$2b$12$..."
role = "lecteur"
```

Aucune dépendance nouvelle, aucune donnée envoyée à un tiers : les identifiants restent uniquement dans les secrets Streamlit (chiffrés, jamais dans le dépôt) et dans les commits GitHub (que vous générez et poussez vous-même). Pour révoquer quelqu'un, supprimez son bloc.

**2. Restreindre qui peut même ouvrir l'app (complémentaire, sans code)**

Sur le dépôt privé de production, Streamlit Cloud permet d'inviter des emails précis dans les paramètres de partage de l'app — une deuxième barrière gratuite, native, avant même d'arriver à l'écran de connexion.

**3. Si vous avez besoin d'un vrai système de comptes en libre-service** (auto-inscription, réinitialisation de mot de passe, beaucoup d'utilisateurs), ces options gratuites en démarrage et respectueuses des données méritent d'être évaluées le moment venu — cela demande un vrai développement (remplacer `streamlit-authenticator` par leur SDK), pas juste une configuration :
- [Supabase Auth](https://supabase.com/auth) — offre gratuite généreuse, données hébergées dans une base Postgres que vous contrôlez.
- [Clerk](https://clerk.com) — offre gratuite jusqu'à un certain nombre d'utilisateurs actifs, bon support Python/Streamlit communautaire.

Dans tous les cas, toute clé/secret d'un tel service se stocke dans les secrets Streamlit (jamais dans le code ni dans un CSV), exactement comme le token GitHub ou la clé YouTube aujourd'hui.

## Développement local

```bash
pip install -r requirements.txt
streamlit run app.py
```

Pour tester la collecte en ligne de commande, sans Streamlit (comme le fera GitHub Actions) :
```bash
GITHUB_TOKEN=... GITHUB_REPO=owner/repo YOUTUBE_API_KEY=... python scripts/run_collection.py
```

## Licence

© 2026 Bertrand Formet — [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (Creative Commons Attribution 4.0 International). Voir le fichier [LICENSE](LICENSE).
