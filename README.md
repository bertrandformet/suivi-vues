# Suivi Vues

Tableau de bord de suivi de métriques dans le temps (vues, écoutes, ou tout autre compteur — participants, téléchargements, sessions...) pour des URLs ciblées sur YouTube, PeerTube, Apple Podcasts, Spotify, Podcast Addict, Deezer, Pocket Casts, Castbox, Overcast, Castro, ou toute autre plateforme que vous ajoutez vous-même. Chaque plateforme déclare sa propre unité (vues, écoutes, participants...) : l'app n'est pas limitée au comptage de vues vidéo/audio.

Les données (éléments suivis, URLs, relevés) sont stockées sous forme de CSV **dans un dépôt GitHub**, lues et écrites via l'API GitHub — chaque ajout ou ajustement crée un commit, ce qui donne un historique d'audit complet sans base de données externe.

**Collecte** :
- ✅ **YouTube** et **PeerTube** : collecte automatique (API publique), déclenchable manuellement ou chaque semaine via GitHub Actions.
- **Toute autre plateforme** (podcasts, formations, téléchargements...) : ces relevés restent en saisie manuelle ou en import de fichier — la plupart des plateformes n'exposent pas d'API publique de comptage pour du contenu dont on n'est pas propriétaire. L'architecture (`src/collectors.py`) est prévue pour qu'on puisse ajouter facilement une future source automatique, quelle qu'elle soit.

## 0. Code (public) et données (privées) : deux dépôts séparés

Ce dépôt ne contient **aucune donnée réelle** — seulement le code et un jeu de données d'exemple (`example_data/`, non lu par l'app en production) pour illustrer le modèle. Les vraies données (vos URLs suivies, vos relevés) doivent vivre dans un **second dépôt GitHub, privé**, que vous créez séparément :

- **Ce dépôt (public)** : le code de l'app, forkable/réutilisable tel quel. Aucune fuite possible puisqu'il ne contient jamais vos données réelles.
- **Votre dépôt de données (privé)** : un dépôt GitHub minimal contenant seulement les CSV (`dossiers.csv`, `contents.csv`, `platforms.csv`, `tracked_urls.csv`, `snapshots.csv` — voir `example_data/` pour le format exact). L'app y lit/écrit via l'API GitHub Contents, configuré dans les secrets (étape 5).

Cette séparation évite de dupliquer le code à chaque mise à jour : un seul dépôt de code, un dépôt de données par déploiement réel.

## 1. Créer les deux dépôts GitHub

1. Ce dépôt de code reste tel quel (forkez-le ou clonez-le si besoin).
2. Créez un **second dépôt GitHub, privé**, pour vos données — vide, ou initialisé avec une copie de `example_data/` renommée `data/` comme point de départ :
   ```bash
   mkdir mon-projet-data && cd mon-projet-data
   git init && git remote add origin git@github.com:<votre-org>/<votre-repo>-data.git
   cp -r <chemin-vers-ce-repo>/example_data ./data
   git add data && git commit -m "Initialisation des données"
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

Nécessaire uniquement pour activer la collecte automatique des vues YouTube. Sans clé, les URLs YouTube resteront en erreur lors de la collecte automatique — elles peuvent en attendant être suivies manuellement.

**a. Créer (ou sélectionner) un projet Google Cloud**
1. Allez sur [console.cloud.google.com](https://console.cloud.google.com/) (connectez-vous avec un compte Google).
2. En haut de la page, cliquez le sélecteur de projet (à côté du logo « Google Cloud »).
3. Cliquez **Nouveau projet**, donnez-lui un nom (ex. `suivi-vues`), laissez le reste par défaut, cliquez **Créer**.
4. Attendez quelques secondes puis vérifiez que ce projet est bien sélectionné en haut (sinon la clé sera créée dans le mauvais projet).

**b. Activer l'API YouTube Data v3**
1. Allez directement sur [cette page](https://console.cloud.google.com/apis/library/youtube.googleapis.com) (lien direct vers l'API).
2. Vérifiez que le bon projet est sélectionné en haut.
3. Cliquez **Activer**.

**c. Créer la clé API**
1. Allez sur [console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials).
2. Cliquez **+ Créer des identifiants** (en haut) → **Clé API**.
3. Dans la fenêtre **Créer une clé API** qui s'ouvre : donnez-lui un nom (ex. `Clé API YT`), puis dans **Sélectionner des restrictions d'API**, filtrez et cochez **YouTube Data API v3**, cliquez **OK**.
4. Sous **Restrictions relatives aux applications**, laissez **Aucun** (la clé est appelée depuis un script serveur — GitHub Actions / Streamlit Cloud — pas depuis un navigateur ou une appli).
5. Cliquez **Créer**. La clé générée (commence par `AIza...`) s'affiche — copiez-la immédiatement, elle sert dans les secrets (étape suivante) et dans le secret GitHub Actions `YOUTUBE_API_KEY` (étape 6).

## 5. Configurer les secrets

Dupliquez `.streamlit/secrets.toml.example` en `.streamlit/secrets.toml` (local, ignoré par git) ou collez son contenu dans le gestionnaire de secrets de Streamlit Cloud. Remplissez :
- `[github]` : le token généré à l'étape 2, le nom de **votre dépôt de données privé** (`owner/votre-repo-data`, pas ce dépôt de code), la branche.
- `[youtube]` : la clé API de l'étape 4 (optionnel).
- `[auth.cookie]` : une clé aléatoire longue (sert à signer le cookie de session).
- `[auth.credentials.usernames.admin]` et `[auth.credentials.usernames.lecteur]` : les hashs générés à l'étape 3.

## 6. Activer la collecte automatique hebdomadaire (GitHub Actions)

Le fichier `.github/workflows/collect.yml` est déjà inclus et se déclenche chaque lundi, plus manuellement depuis l'onglet **Actions** du dépôt (bouton "Run workflow"). Comme les données vivent dans un dépôt séparé, le token d'écriture automatique de GitHub Actions (`secrets.GITHUB_TOKEN`, généré pour ce dépôt de code) ne suffit pas — il faut lui donner un accès dédié à votre dépôt de données :

1. Modifiez `GITHUB_REPO: bertrandformet/suivi-vues-data` dans `collect.yml` pour y mettre le nom de **votre propre dépôt de données** (`owner/votre-repo-data`).
2. Créez un token fine-grained (github.com/settings/tokens?type=beta) limité à ce dépôt de données, permission **Contents: Read and write**.
3. Sur ce dépôt de code : Settings → Secrets and variables → Actions → New repository secret → nommez-le `DATA_REPO_TOKEN`, collez le token.
4. Ajoutez aussi `YOUTUBE_API_KEY` (même valeur qu'à l'étape 4) si vous voulez la collecte YouTube automatique.

Le déclenchement manuel est aussi possible directement depuis le dashboard (page de collecte, bouton "Lancer la collecte maintenant"), en plus du cron hebdomadaire.

## 7. Déployer sur Streamlit Community Cloud

1. Sur [share.streamlit.io](https://share.streamlit.io), connectez votre compte GitHub.
2. Créez une nouvelle app à partir de ce dépôt, fichier principal `app.py`.
3. Dans les paramètres de l'app → Secrets, collez le contenu de votre `secrets.toml`.
4. Déployez. L'app est accessible via l'URL fournie par Streamlit ; connectez-vous avec `admin` ou `lecteur`.

Streamlit Cloud ne restreint l'accès par email ("app privée") que pour une app déployée depuis un **dépôt GitHub privé** — comme ce dépôt de code reste public par conception (pour rester réutilisable), l'unique barrière d'accès est le login intégré à l'app (admin/lecteur). Si vous voulez la double barrière, déployez plutôt depuis un fork **privé** de ce dépôt de code — vos données réelles resteront de toute façon dans leur dépôt séparé, jamais dans ce dépôt de code.

## 8. Utilisation

- **Lecteur** : consulte le Tableau de bord (courbes d'évolution, comparaison par plateforme, données cumulées, table d'audit).
- **Admin** : en plus, peut créer des éléments suivis, ajouter des URLs à suivre (avec leur méthode de collecte), saisir ou ajuster des relevés, importer des fichiers CSV/Excel, et déclencher la collecte automatique à la demande.
- Chaque relevé est conservé (pas d'édition destructive) : un ajustement est une nouvelle ligne horodatée, cochée « ajustement », avec une note explicative. Les relevés automatiques portent la source « auto ». Un relevé erroné peut aussi être supprimé directement depuis le journal des relevés du tableau de bord, avec une confirmation avant suppression.
- **Données cumulées** : le tableau de bord affiche par défaut un total par plateforme (somme de tous les éléments suivis de cette plateforme, dans le temps). Une section « Données cumulées » permet en plus d'additionner librement plusieurs plateformes entre elles (ex. YouTube + PeerTube), avec un avertissement si leurs unités diffèrent (vues vs participants, par exemple).

### Regrouper les URLs d'un même épisode

Un même épisode (podcast ou vidéo) existe souvent sur plusieurs plateformes à la fois (YouTube, Spotify, Apple Podcasts...). Pour suivre sa performance globale plutôt que plateforme par plateforme, créez un **élément suivi** qui les rassemble :

1. Dans « Éléments suivis & URLs » → onglet **Créer un élément suivi**, donnez-lui un nom (ex. « Mon podcast — Épisode 13 »).
2. Toujours dans « Éléments suivis & URLs » → onglet **Ajouter une URL suivie**, ajoutez chaque URL de cet épisode (une par plateforme) en la rattachant à cet élément via le menu « Rattacher à un élément suivi ».
3. Sur le Tableau de bord, filtrez par plateforme ou passez la vue en « URL suivie (détail) » pour comparer sa portée d'une plateforme à l'autre — toutes les URLs d'un même élément suivi partagent la même couleur sur les graphiques (la couleur code l'élément suivi, jamais la plateforme).

Une URL peut aussi rester indépendante si elle ne fait partie d'aucun élément suivi. Chaque plateforme (`platforms.csv`) déclare sa propre unité — au-delà des vues/écoutes, rien n'empêche de suivre par exemple des participants à une formation ou des téléchargements, voir `example_data/platforms.csv` pour un exemple générique.

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

**2. Restreindre qui peut ouvrir l'app (complémentaire, sans code)**

Si vous déployez depuis un fork privé du dépôt de code (voir étape 7), Streamlit Cloud permet aussi d'inviter des emails précis dans les paramètres de partage de l'app — une deuxième barrière gratuite, native, avant même d'arriver à l'écran de connexion.

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
