# Gestion du disciple — Assemblée

Application web simple et pratique pour gérer les disciples, évangélistes, planning d'évangélisation et assiduité à l'adoration du dimanche, au sein de l'assemblée de famille.

Développée avec **Flask + SQLAlchemy + Bootstrap 5**. Base de données **PostgreSQL** en production, **SQLite** en local.

---

## 1. Fonctionnalités

- **Disciples** : création / édition / suppression avec tous les champs du cahier des charges (matricule, identité, lieu d'habitation, zone, sous-centre, assemblée, faiseur de disciple, mentore, statut spirituel, niveau académique, 10 amis proches, 5 familles proches).
- **Évangélistes** : fiches complètes (identité, zone, sous-centre, assemblée, qualité).
- **Planning d'évangélisation** : RDV hebdomadaires (semaine, jour, heure, âme à rencontrer, lieu, statut RDV OK/NOK, statut engagement OK/NOK).
- **Assiduité adoration du dimanche** : saisie rapide des présences par dimanche.
- **Rapports** :
  - Évangélisation (par semaine / par mois, par évangéliste et global assemblée)
  - Assiduité (par mois / par année, par disciple et global assemblée — prise en compte des mois achevés pour l'année en cours).

---

## 2. Déploiement gratuit sur Render.com (recommandé)

Render offre un niveau gratuit qui démarre en quelques minutes, sans carte bancaire requise.

### Étape 1 — Pousser le code sur GitHub

1. Créez un compte sur https://github.com (gratuit).
2. Créez un nouveau dépôt, par exemple `gestion-disciple` (public ou privé).
3. Téléversez tous les fichiers du projet dans ce dépôt (via l'interface web « Add file → Upload files », en glissant-déposant tous les fichiers et dossiers).

### Étape 2 — Créer un compte Render.com

Rendez-vous sur https://render.com et créez un compte (gratuit, se connecte avec GitHub).

### Étape 3 — Créer la base de données PostgreSQL (gratuit)

1. Dashboard Render → **New +** → **PostgreSQL**.
2. Donnez un nom (ex. `disciple-db`), région la plus proche (ex. *Frankfurt* pour l'Europe/Afrique), plan **Free**.
3. Cliquez **Create Database**.
4. Une fois créée, ouvrez-la et copiez la valeur **Internal Database URL**.

> ⚠️ La base PostgreSQL gratuite expire après 90 jours. Vous pouvez en recréer une gratuitement à ce moment-là. Pour un usage permanent, prévoyez 7 $/mois ou utilisez un autre provider (Neon.tech, Supabase — tous deux ont des plans gratuits sans expiration).

### Étape 4 — Créer le service Web

1. Dashboard Render → **New +** → **Web Service**.
2. **Connect a repository** → sélectionnez votre dépôt GitHub `gestion-disciple`.
3. Paramétrage :
   - **Name** : `gestion-disciple`
   - **Region** : la même que la base (Frankfurt)
   - **Branch** : `main`
   - **Runtime** : `Python 3`
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `gunicorn app:app --bind 0.0.0.0:$PORT`
   - **Plan** : **Free**
4. Dans la section **Environment Variables**, ajoutez :
   - `DATABASE_URL` = (collez l'Internal Database URL copiée à l'étape 3)
   - `SECRET_KEY` = une longue chaîne aléatoire (ex. `k7d9fj28dk29fjdkqj28d`)
   - `APP_USERNAME` = `assemblee` (ou autre)
   - `APP_PASSWORD` = choisissez un mot de passe fort (à partager avec les personnes habilitées)
5. Cliquez **Create Web Service**.

Render construit et démarre l'application en 2 à 4 minutes. L'URL publique sera de la forme `https://gestion-disciple.onrender.com`.

> 💡 Le plan gratuit met l'application en veille après 15 minutes d'inactivité. Le premier accès après une mise en veille prend environ 30 secondes. Les connexions suivantes sont instantanées.

### Étape 5 — Connexion

1. Ouvrez l'URL publique, par exemple `https://gestion-disciple.onrender.com`.
2. Connectez-vous avec `APP_USERNAME` / `APP_PASSWORD` définis à l'étape 4.
3. Commencez à enregistrer les disciples et les évangélistes.

---

## 3. Alternatives gratuites

### Railway.app
Déployez en 1 clic via Docker. Crédit gratuit de 5 $ par mois (suffisant pour une app légère 24/7).

### Fly.io
Plan gratuit avec PostgreSQL persistant. Commande :
```bash
fly launch
fly postgres create
fly deploy
```

### PythonAnywhere
Plan gratuit avec stockage persistant mais sans Docker. Déploiement manuel — suivre leur guide Flask.

---

## 4. Lancement en local (pour tester)

```bash
# 1. Installer Python 3.11+
# 2. Cloner le projet
git clone <votre-repo>
cd gestion-disciple

# 3. Créer un environnement virtuel
python -m venv venv
source venv/bin/activate         # Linux/Mac
venv\Scripts\activate            # Windows

# 4. Installer les dépendances
pip install -r requirements.txt

# 5. Lancer
python app.py
```

Ouvrez http://localhost:5000 dans votre navigateur.

Identifiants par défaut : `assemblee` / `assemblee2026`.

La base SQLite `disciples.db` est créée automatiquement dans le dossier courant.

---

## 5. Structure du projet

```
gestion-disciple/
├── app.py                  # Application Flask (modèles, routes, logique)
├── requirements.txt        # Dépendances Python
├── Procfile                # Commande de démarrage (Render/Heroku/Railway)
├── render.yaml             # Infrastructure as Code pour Render
├── Dockerfile              # Image Docker (utile pour Fly.io ou auto-hébergement)
├── runtime.txt             # Version Python
├── .env.example            # Exemple de variables d'environnement
├── .gitignore
├── README.md
├── templates/              # Templates Jinja2 (Bootstrap 5)
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── disciples_list.html
│   ├── disciple_form.html
│   ├── disciple_detail.html
│   ├── evangelistes_list.html
│   ├── evangeliste_form.html
│   ├── planning_list.html
│   ├── rdv_form.html
│   ├── adoration.html
│   ├── rapport_evangelisation.html
│   └── rapport_assiduite.html
└── static/                 # CSS/JS personnalisés (vide par défaut)
```

---

## 6. Variables d'environnement

| Variable       | Description                                                       | Défaut local       |
|----------------|-------------------------------------------------------------------|--------------------|
| `SECRET_KEY`   | Clé secrète Flask (sessions). **Obligatoire en production.**      | `change-me-...`    |
| `APP_USERNAME` | Identifiant de connexion de l'assemblée.                          | `assemblee`        |
| `APP_PASSWORD` | Mot de passe de connexion de l'assemblée.                         | `assemblee2026`    |
| `DATABASE_URL` | URL PostgreSQL (prod). Laissée vide → SQLite local `disciples.db`. | (SQLite)           |
| `PORT`         | Port HTTP (défini automatiquement par Render/Railway/Heroku).     | `5000`             |

---

## 7. Améliorations futures possibles

- Téléversement réel de fichiers (plan de domicile, CV) avec stockage S3/Cloudinary
- Gestion multi-utilisateurs avec rôles (admin / évangéliste / simple disciple)
- Export Excel / PDF des rapports
- Notifications SMS/WhatsApp avant les RDV d'évangélisation
- Synchronisation avec Google Calendar

---

**Questions / support** : contactez l'auteur de l'application ou ouvrez une *issue* sur le dépôt GitHub.
