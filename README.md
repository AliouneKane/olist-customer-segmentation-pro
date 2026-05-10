# Olist Customer Segmentation

> **Transformer 93 358 transactions en stratégies marketing actionnables grâce au Machine Learning**

---

## 🚀 Dashboard en ligne

**[https://olist-segmentation-okgrrwjcwq-ew.a.run.app/](https://olist-segmentation-okgrrwjcwq-ew.a.run.app/)**

Dashboard Streamlit déployé sur Google Cloud Run — accès immédiat, sans installation.

---

## 📊 Présentation du projet

**[https://canva.link/zfsgzh7axdnwjaw](https://canva.link/zfsgzh7axdnwjaw)**

Slides de présentation complètes — contexte, méthodologie, résultats et recommandations marketing.

---

## Le contexte

Olist est la principale marketplace e-commerce du Brésil, connectant des milliers de vendeurs indépendants à des millions d'acheteurs. Avec un dataset de **93 358 clients uniques**, **100 000+ commandes** et **8 millions de lignes de données relationnelles**, Olist dispose d'une mine d'informations comportementales — encore trop peu exploitée par les équipes marketing.

La question centrale : **qui sont réellement les clients Olist, et comment leur parler différemment ?**

---

## La problématique

Les équipes marketing opèrent sans visibilité claire sur la diversité des profils clients. Résultat :

- Des campagnes mass-market qui ignorent les clients à fort potentiel
- Des clients inactifs à valeur prouvée qui partent sans qu'on les ait jamais recontactés
- Un budget CRM dépensé indistinctement sur tous les segments, même les moins rentables

**Sans segmentation, toute stratégie marketing est une dépense à l'aveugle.**

---

## Résultats clés

| Segment | Clients | Part | Panier médian | Récence | Signal principal |
|---------|---------|------|---------------|---------|-----------------|
| 🛒 Acheteurs Budget | 21 146 | 28% | 64 BRL | 124j | Récents, économes — volume & fidélisation |
| ⏳ Dormants Budget | 18 775 | 25% | 72 BRL | 292j | Inactifs, faible valeur — réactivation low-cost |
| ⭐ Acheteurs Premium | 18 546 | 24% | 180 BRL | 131j | Récents, fort panier — nurturing & upsell |
| 🌙 Dormants Premium | 17 470 | 23% | 160 BRL | 367j | Inactifs, valeur prouvée — réactivation urgente |

**Algorithme retenu :** UMAP(n_neighbors=750) + KMeans k=4 · Silhouette **0.449** · Davies-Bouldin 0.737

---

## Screenshots du Dashboard

### Vue d'Ensemble — Storytelling & KPIs

![Vue d'ensemble](docs/screenshots/01_overview_hero.png)

*Intro narrative avec les 3 insights critiques (Acheteurs Premium, Dormants Premium, Acheteurs Budget), KPIs globaux, distribution par segment et heatmap des comportements.*

### Vue d'Ensemble — Métriques détaillées

![Vue d'ensemble — KPIs](docs/screenshots/02_overview_kpis.png)

*Distribution des 4 segments, comparaison des métriques clés (Recency, Monetary, Frequency) et heatmap des centroides.*

### Détail Segment

![Détail Segment — Acheteurs Premium](docs/screenshots/03_segment_detail.png)

*Profil radar multi-dimensionnel, carte stratégie marketing, progress bar CLV vs. maximum, et plan d'action généré par Gemini AI.*

### Comparaison des Algorithmes

![Comparaison — Benchmark KMeans / CAH / DBSCAN](docs/screenshots/04_comparison.png)

*Tableau de métriques (Silhouette, Davies-Bouldin, Calinski-Harabasz) et visualisation comparative. UMAP+KMeans k=4 retenu, silhouette 0.449.*

### Guide du Dashboard

![Guide du Dashboard](docs/screenshots/05_guide.png)

*Mode d'emploi complet pour les équipes non techniques : définitions des métriques, lecture des graphiques, priorités par segment.*

### Prédiction Nouveaux Clients

![Prédiction Clients](docs/screenshots/06_prediction.png)

*Upload CSV ou Excel de nouveaux clients — prédiction automatique Budget/Premium, interprétation métier en langage simple et plan d'action en 4 étapes.*

---

## Architecture du projet

```
olist-customer-segmentation/
│
├── .github/workflows/
│   ├── ci.yml                     # Tests + black à chaque push
│   ├── cd.yml                     # Build Docker + deploy Cloud Run (push main)
│   ├── retrain.yml                # Réentraînement trimestriel (janv/avr/juil/oct)
│   └── ingest.yml                 # Ingestion + retrain sur ajout dans data/incoming/
│
├── data/
│   ├── raw/                       # CSVs Kaggle (non versionnés — .gitignore)
│   ├── processed/                 # Parquets générés (versionnés)
│   └── incoming/                  # Nouvelles commandes à ingérer (versionnés)
│
├── models/                        # Modèles sérialisés .pkl + métadonnées .json
│
├── notebooks/                     # Pipeline ML — exécuter dans l'ordre
│   ├── 00_data_presentation.ipynb # Présentation de la base (head par table)
│   ├── 01_eda.ipynb               # Analyse exploratoire
│   ├── 02_preprocessing_fe.ipynb  # Feature engineering (10 features → 9 retenues)
│   ├── 03_clustering.ipynb        # Comparaison 6 algos + recommandations produits + profil socio-démo
│   └── 04_simulation.ipynb        # Stabilité temporelle → fréquence de réentraînement
│
├── src/                           # Modules de production
│   ├── data_loader.py             # Connexion PostgreSQL (local Docker ou Neon cloud)
│   ├── features.py                # build_customer_features(), scale_features()
│   ├── model_utils.py             # save_model(), load_model(), assign_clusters()
│   └── artifact_store.py          # Upload / download artefacts GCS
│
├── scripts/
│   ├── generate_artifacts.py      # Pipeline entraînement complet (standalone)
│   ├── retrain.py                 # Réentraînement avec comparaison silhouette
│   └── ingest_new_data.py         # Ingestion CSV → tables Neon PostgreSQL
│
├── streamlit_app/
│   ├── main.py                    # Point d'entrée + sync GCS au démarrage
│   ├── styles.py                  # Thème Olist (bleu #0041FF / jaune #F0FF00)
│   ├── components/
│   │   ├── sidebar.py
│   │   ├── kpi_cards.py
│   │   ├── charts.py
│   │   ├── data_store.py
│   │   ├── segment_recommendations.py
│   │   └── ai_insight.py          # Gemini 2.5 Flash
│   └── views/
│       ├── overview.py
│       ├── segment_detail.py
│       ├── comparison.py
│       ├── prediction.py          # Prédiction nouveaux clients (upload CSV/Excel)
│       └── guide.py
│
├── tests/
├── docker/
│   └── entrypoint.sh
├── Dockerfile
├── docker-compose.yml             # PostgreSQL local (dev)
└── requirements.txt
```

---

## Pipeline de données & ML

```
Kaggle CSVs / Nouvelles commandes
         ↓
Neon PostgreSQL (cloud) ←──── ingest_new_data.py
         ↓
Feature Engineering (RFM + logistique + satisfaction + géo)
         ↓
IQR filter → log10 → StandardScaler → UMAP(n_neighbors=750)
         ↓
KMeans k-search (k=3..8) → meilleur silhouette
         ↓
Comparaison vs modèle actuel (GCS metadata)
         ↓
Si amélioré → Upload GCS → Dashboard mis à jour
```

---

## Stack technique

| Couche | Technologie |
|--------|-------------|
| Base de données | **Neon PostgreSQL** (cloud, serverless) + PostgreSQL local (docker-compose) |
| Stockage artefacts | **Google Cloud Storage** (modèles, parquets) |
| Machine Learning | scikit-learn 1.5, umap-learn, scipy, MLflow 2.13 |
| Visualisation | Plotly 5.22, Streamlit ≥ 1.36 |
| IA générative | Google Gemini 2.5 Flash |
| Tests | pytest 8.2, black 24.4 |
| Conteneurisation | Docker (python:3.10-slim) |
| Déploiement | Google Cloud Run |
| CI/CD | GitHub Actions |

---

## Reproduire le projet localement

> Temps estimé : **30–45 minutes** (hors téléchargement Kaggle)

### Prérequis

Avant de commencer, s'assurer d'avoir installé :

- **Python 3.10+** — [python.org](https://www.python.org/downloads/)
- **Docker Desktop** — [docker.com](https://www.docker.com/products/docker-desktop/) (pour PostgreSQL local)
- **Git**

Les services cloud (Neon, GCS, Gemini) sont **optionnels** pour faire tourner les notebooks localement. Ils sont nécessaires uniquement pour le déploiement production.

---

### Étape 1 — Cloner le dépôt

```bash
git clone https://github.com/AliouneKane/olist-customer-segmentation.git
cd olist-customer-segmentation
```

---

### Étape 2 — Environnement virtuel & dépendances

```bash
python3.10 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

---

### Étape 3 — Variables d'environnement

Créer le fichier `.env` à la racine du projet :

```env
# ── PostgreSQL local (Docker — obligatoire pour les notebooks) ──────────────
POSTGRES_HOST=localhost
POSTGRES_PORT=5444
POSTGRES_DB=olist_db
POSTGRES_USER=olist_user
POSTGRES_PASSWORD=olist_password

# ── Neon PostgreSQL (cloud — uniquement pour le déploiement production) ──────
# DATABASE_URL=postgresql://user:password@host/neondb?sslmode=require

# ── Gemini AI (optionnel — pour les insights IA du dashboard) ────────────────
# GEMINI_API_KEY=your_gemini_api_key

# ── Google Cloud Storage (optionnel — uniquement pour le déploiement) ────────
# GCS_BUCKET=your-gcs-bucket-name
# GCP_PROJECT=your-gcp-project-id
```

> ⚠️ **Important :** Laisser `DATABASE_URL` commenté en local. Si elle est définie, `data_loader.py` se connecte à Neon (cloud) au lieu du Docker local, ce qui fait échouer les notebooks sans accès internet au serveur Neon.

---

### Étape 4 — Télécharger les données Kaggle

1. Aller sur [Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
2. Télécharger et décompresser les CSV dans `data/raw/`

Structure attendue dans `data/raw/` :

```
data/raw/
├── olist_orders_dataset.csv
├── olist_customers_dataset.csv
├── olist_order_items_dataset.csv
├── olist_products_dataset.csv
├── olist_sellers_dataset.csv
├── olist_order_payments_dataset.csv
├── olist_order_reviews_dataset.csv
├── olist_geolocation_dataset.csv
└── product_category_name_translation.csv
```

---

### Étape 5 — Démarrer PostgreSQL local (Docker)

```bash
docker-compose up -d
```

Vérifier que le conteneur tourne :

```bash
docker ps
# → olist_postgres   Up X minutes   0.0.0.0:5444->5432/tcp
```

Charger les données CSV dans PostgreSQL :

```bash
python src/data_loader.py
```

Cette commande lit les CSV de `data/raw/` et les insère dans les 9 tables PostgreSQL. Durée : ~2–5 minutes.

---

### Étape 6 — Exécuter les notebooks dans l'ordre

Lancer Jupyter :

```bash
jupyter notebook
# ou
jupyter lab
```

Ouvrir et exécuter les notebooks **dans cet ordre** :

| # | Notebook | Contenu | Durée |
|---|----------|---------|-------|
| 0 | `00_data_presentation.ipynb` | Présentation des 9 tables (head, colonnes, stats) | ~2 min |
| 1 | `01_eda.ipynb` | Analyse exploratoire — qualité, distributions, cohortes | ~5 min |
| 2 | `02_preprocessing_fe.ipynb` | Feature engineering — 10 features, StandardScaler, export parquets | ~5 min |
| 3 | `03_clustering.ipynb` | Comparaison 6 algorithmes, sélection KMeans k=4, recommandations produits, profil socio-démo | ~15 min |
| 4 | `04_simulation.ipynb` | Stabilité temporelle, fréquence de réentraînement | ~5 min |

> **Note :** Le notebook 03 peut prendre plus de temps selon la puissance de la machine (UMAP sur 93k clients).

Les notebooks génèrent automatiquement dans `data/processed/` :
- `customer_features_raw.parquet`
- `customer_features_scaled.parquet`
- `customer_features_labeled.parquet`
- `cluster_profile.parquet`

Et dans `models/` :
- `best_clustering_kmeans_k4.pkl` + métadonnées `.json`

---

### Étape 7 — Lancer le dashboard en local

```bash
streamlit run streamlit_app/main.py
```

Ouvrir **[http://localhost:8501](http://localhost:8501)**

> Le dashboard charge les artefacts depuis `models/` et `data/processed/` en local. GCS n'est pas requis.

**Pages disponibles :**
- **Vue d'ensemble** — KPIs globaux, distribution, heatmap
- **Détail Segment** — radar, recommandations marketing, plan IA Gemini
- **Comparaison** — benchmark des 6 algorithmes
- **Prédiction Clients** — upload CSV/Excel → prédiction segment → plan d'action
- **Guide** — mode d'emploi équipe métier

---

### Étape 8 — Tests

```bash
pytest tests/ -v
```

---

## Déploiement (Google Cloud Run)

### Secrets GitHub requis

| Secret | Description |
|--------|-------------|
| `GCP_CREDENTIALS` | JSON du service account (`olist-deployer`) |
| `DATABASE_URL` | Connection string Neon.tech |
| `GCS_BUCKET` | Nom du bucket GCS |
| `GEMINI_API_KEY` | Clé API Gemini |

### Rôles IAM du service account `olist-deployer`

- Administrateur Cloud Run
- Rédacteur Artifact Registry
- Administrateur Storage
- Utilisateur du compte de service

### Pipeline CD (automatique)

Chaque push sur `main` déclenche `.github/workflows/cd.yml` :

```
push main → Build image Docker → Push Artifact Registry → Deploy Cloud Run
```

L'image Docker intègre les artefacts ML depuis `models/` et `data/processed/`.
Au démarrage, l'app télécharge les artefacts les plus récents depuis GCS.

### Build Docker local

```bash
docker build -t olist-segmentation .
docker run -p 8080:8080 --env-file .env olist-segmentation
```

---

## Réentraînement automatique

Le modèle se réentraîne automatiquement **tous les trimestres** (1er janvier, avril, juillet, octobre à 3h UTC) via `.github/workflows/retrain.yml`.

**Déclenchement manuel** (depuis GitHub → Actions → "Quarterly Model Retrain" → Run workflow)

**Logique de décision :**
- Nouveau silhouette ≥ silhouette actuel − 0.005 → artefacts mis à jour sur GCS
- Sinon → modèle actuel conservé, résultat loggé

**Historique des réentraînements :** `data/processed/retrain_log.json`

---

## Ingestion de nouvelles données

Pour ajouter de nouvelles commandes et déclencher automatiquement le réentraînement :

### 1. Préparer le fichier

```bash
cp data/incoming/template_nouvelles_commandes.csv data/incoming/commandes_MOIS_ANNEE.csv
```

**Colonnes requises :**

| Colonne | Description | Exemple |
|---------|-------------|---------|
| `order_id` | Identifiant unique de la commande | `ord-2026-001` |
| `customer_id` | ID client (technique) | `cust-001` |
| `customer_unique_id` | ID client unique (métier) | `uniq-001` |
| `customer_state` | État brésilien (2 lettres) | `SP` |
| `order_purchase_date` | Date d'achat | `2026-05-01 10:00:00` |
| `order_delivered_date` | Date de livraison | `2026-05-08 14:00:00` |
| `order_estimated_delivery_date` | Date estimée | `2026-05-10 00:00:00` |
| `price` | Montant produit (BRL) | `320.00` |
| `freight_value` | Frais de port (BRL) | `18.50` |
| `payment_type` | `credit_card`, `boleto`, `debit_card`, `voucher` | `credit_card` |
| `payment_installments` | Nombre de versements | `3` |
| `payment_value` | Montant total (BRL) | `338.50` |
| `review_score` | Note satisfaction (1–5) | `5` |

### 2. Pusher sur GitHub

```bash
git add data/incoming/commandes_MOIS_ANNEE.csv
git commit -m "feat: nouvelles commandes MOIS ANNEE"
git push
```

### 3. GitHub Actions se déclenche automatiquement

```
Nouveau CSV détecté dans data/incoming/
        ↓
ingest_new_data.py → insère dans Neon (sans doublons sur order_id)
        ↓
retrain.py → réentraîne → compare silhouette
        ↓
Si amélioré → upload GCS → dashboard mis à jour au prochain démarrage
```

---

## Fonctionnement du modèle

Le pipeline agrège toutes les tables au niveau `customer_unique_id` — **une ligne = un client** :

```
orders → order_items → products     ┐
orders → order_payments             ├──→ customer_features (RFM enrichi)
orders → order_reviews              │
orders → customers → geolocation    ┘
```

**Features utilisées pour le clustering (RFM pur) :**

| Feature | Description |
|---------|-------------|
| `Recency` | Jours depuis le dernier achat |
| `Frequency` | Nombre total de commandes |
| `Monetary` | Montant total dépensé (BRL) |

**Features du profil segment (dashboard uniquement — non utilisées pour le clustering) :**

| Feature | Description |
|---------|-------------|
| `avg_freight_ratio` | Frais de port / valeur commande |
| `avg_delivery_delay` | Écart livraison estimée vs. réelle (jours) |
| `avg_review_score` | Note satisfaction 1–5 |
| `avg_installments` | Nombre moyen de versements |
| `payment_type_cc_flag` | 1 = carte de crédit dominante |
| `region_freight_score` | Score logistique régional (1 = Sul, 5 = Norte) |
| `category_tier_encoded` | Macro-segment produit dominant (ordinal 1–10) |
| `CLV_proxy` | Monetary × Frequency |

---

## Auteurs

| Nom | Contribution |
|-----|-------------|
| **Khadidiatou Diakhaté** | Data Science & Feature Engineering |
| **Alioune Abdou Salam Kane** | Machine Learning & Model Evaluation |
| **Jacques Ily** | Data Engineering & Infrastructure |
| **Raherinasolo Ange Emilson Rayan** | Dashboard & Visualisation |

---

## Licence

Projet académique. Données publiques disponibles sur [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) sous licence CC BY-NC-SA 4.0.
