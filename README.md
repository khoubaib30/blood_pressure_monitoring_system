# Système de Surveillance de Pression Artérielle avec Machine Learning

Système de monitoring en temps réel pour la surveillance de la pression artérielle, intégrant le streaming de données (Kafka), le stockage (Elasticsearch), la visualisation (Kibana), et des prédictions ML pour anticiper les risques de crise hypertensive.

## Description du Projet

Ce projet est une plateforme complète de surveillance médicale qui :

- **Collecte** des données de pression artérielle en temps réel via Kafka
- **Stocke** les observations dans Elasticsearch pour l'analyse historique
- **Visualise** les données dans Kibana avec des dashboards interactifs
- **Prédit** les risques de crise hypertensive à 1h, 6h et 24h grâce au Machine Learning
- **Alerte** les professionnels de santé en cas de risque élevé

### Fonctionnalités Principales

- **Dashboard Web Flask** : Interface de monitoring avec authentification
- **Prédictions ML en Temps Réel** : Modèle XGBoost pour prédire les risques (légèrement meilleur que Random Forest, voir [Évaluation du modèle](#évaluation-du-modèle))
- **Système d'Alertes** : Niveaux d'alerte basés sur la probabilité de crise (CRITICAL, HIGH, MEDIUM, LOW)
- **Visualisation Kibana** : Dashboards pour l'analyse des tendances et patterns
- **Streaming Kafka** : Ingestion de données en temps réel
- **Stockage Elasticsearch** : Base de données pour l'historique des observations

## Architecture et Infrastructure

### Vue d'Ensemble du Système

Le système est composé de plusieurs couches interconnectées :

```
┌─────────────────────────────────────────────────────────────────┐
│                    COUCHE DE GÉNÉRATION DE DONNÉES              │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
            ┌───────▼──────┐    ┌───────▼────────┐
            │  Producer    │    │ Patient Profile │
            │  (Python)    │    │  (Simulation)  │
            └───────┬──────┘    └────────────────┘
                    │
                    │ Génère des données FHIR
                    │ (systolic, diastolic, heart_rate)
                    │
┌───────────────────▼─────────────────────────────────────────────┐
│                    COUCHE DE STREAMING                           │
└─────────────────────────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
┌───────▼──────┐      ┌─────────▼────────┐
│  Zookeeper   │      │     Kafka      │
│  (Coordination)│      │  (Message Queue)│
│  Port: 2181   │      │  Port: 9092    │
└───────────────┘      └────────┬───────┘
                                │
                                │ Streaming en temps réel
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                    COUCHE DE TRAITEMENT                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
            ┌───────▼──────┐      ┌─────────▼────────┐
            │   Consumer   │      │  FHIR Utils      │
            │   (Python)   │      │  (Parsing)       │
            └───────┬──────┘      └──────────────────┘
                    │
                    │ Traite et normalise les données
                    │
┌───────────────────▼─────────────────────────────────────────────┐
│                    COUCHE DE STOCKAGE                              │
└─────────────────────────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
┌───────▼──────┐      ┌─────────▼────────┐
│ Elasticsearch│      │   CSV Files      │
│  (NoSQL DB)  │      │  (Backup/Local)  │
│  Port: 9200  │      │  data/*.csv      │
└───────┬──────┘      └──────────────────┘
        │
        │ Index: blood-pressure-observations
        │
┌───────▼─────────────────────────────────────────────────────────┐
│                    COUCHE DE VISUALISATION                        │
└─────────────────────────────────────────────────────────────────┘
        │
        ├──→ ┌──────────────┐
        │    │    Kibana    │ → Dashboards interactifs
        │    │  Port: 5601  │ → Visualisations de données
        │    └──────────────┘ → Analyse de tendances
        │
        └──→ ┌──────────────────────────────────────┐
             │    Flask Dashboard (Monitoring)      │
             │         Port: 5000                    │
             │                                       │
             │  ┌─────────────────────────────────┐ │
             │  │  Dashboard Principal            │ │
             │  │  - Visualisation temps réel     │ │
             │  │  - Statistiques globales        │ │
             │  │  - Filtres par patient          │ │
             │  └─────────────────────────────────┘ │
             │                                       │
             │  ┌─────────────────────────────────┐ │
             │  │  Prédictions ML                 │ │
             │  │  - Risques 1h, 6h, 24h          │ │
             │  │  - Niveaux d'alerte             │ │
             │  │  - Alertes critiques            │ │
             │  └─────────────────────────────────┘ │
             └───────────────────────────────────────┘
                              │
                              │ Utilise
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                    COUCHE MACHINE LEARNING                       │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼──────┐    ┌─────────▼────────┐  ┌────────▼────────┐
│ ML Inference │    │  XGBoost Model   │  │ Random Forest    │
│  (Runtime)   │    │  (Regression)     │  │  (Regression)    │
│              │    │  models/*.pkl    │  │  models/*.pkl    │
└───────┬──────┘    └──────────────────┘  └──────────────────┘
        │
        │ Prédictions basées sur 30 observations historiques
        │
┌───────▼─────────────────────────────────────────────────────────┐
│                    COUCHE D'ENTRAÎNEMENT ML                      │
└─────────────────────────────────────────────────────────────────┘
        │
        ├──→ ┌──────────────────────┐
        │    │ ML Data Generator    │ → Génère données synthétiques
        │    │ ml_data_generator.py │ → 5000 séquences d'entraînement
        │    └───────────┬────────────┘
        │                │
        │                ↓
        │    ┌──────────────────────┐
        │    │ Training Data        │ → data/ml_training_data.csv
        │    │ (30 obs × 4 features)│ → 3 targets (1h, 6h, 24h)
        │    └───────────┬──────────┘
        │                │
        │                ↓
        │    ┌──────────────────────┐
        │    │ Train XGBoost        │ → ml_train_xgboost.py
        │    │ Train Random Forest  │ → ml_train_random_forest.py
        │    └───────────┬──────────┘
        │                │
        │                ↓
        │    ┌──────────────────────┐
        │    │ Trained Models       │ → models/xgboost_regression.pkl
        │    │                      │ → models/random_forest_regression.pkl
        │    └──────────────────────┘
        │
        └──→ ┌──────────────────────┐
             │ Evaluation Metrics   │ → MAE, RMSE, R²
             │ Visualization        │ → Scatter plots, métriques
             └──────────────────────┘
```

### Composants Détaillés

#### Infrastructure de Streaming

- **Zookeeper** : Service de coordination pour Kafka, gère la configuration et la synchronisation des brokers
- **Kafka** : Plateforme de streaming distribuée, gère les messages en temps réel avec persistance
  - Topic : `blood-pressure-data`

#### Services de Traitement

- **Producer** : Service Python qui génère des données de pression artérielle simulées
  - Utilise `patient_profile.py` pour créer des profils de patients réalistes
  - Génère des données au format FHIR
  - Envoie les messages vers Kafka toutes les 15 minutes par patient

- **Consumer** : Service Python qui consomme les messages Kafka
  - Parse les données FHIR avec `fhir_utils.py`
  - Normalise et valide les données
  - Stocke dans Elasticsearch et sauvegarde dans CSV

#### Base de Données

- **Elasticsearch** : Base de données NoSQL pour le stockage et la recherche
  - Index : `blood-pressure-observations`
  - Stockage persistant via volumes Docker

#### Visualisation

- **Kibana** : Interface de visualisation et d'analyse
  - Dashboards interactifs
  - Visualisations personnalisables
  - Filtres et agrégations avancées
  - Import automatique des dashboards au démarrage

- **Flask Dashboard** : Application web de monitoring
  - Authentification utilisateur (`auth.py`)
  - Visualisation en temps réel
  - API REST pour les données et prédictions
  - Interface responsive avec templates HTML

#### Machine Learning

- **ML Data Generator** (`ml_data_generator.py`) : Génère des données d'entraînement synthétiques
  - Crée 5000 séquences de 30 observations
  - Calcule les targets (risques 1h, 6h, 24h) basés sur les futures observations
  - Format : 120 features (30 obs × 4 features) → 3 targets

- **Modèles d'Entraînement** :
  - `ml_train_xgboost.py` : Entraîne un modèle XGBoost de régression
  - `ml_train_random_forest.py` : Entraîne un modèle Random Forest de régression
  - Les deux modèles prédisent 3 valeurs : critical_risk_1h, critical_risk_6h, critical_risk_24h

- **ML Inference** (`ml_inference.py`) : Module de prédiction en temps réel
  - Utilise le modèle **XGBoost** (retenu après comparaison avec Random Forest, voir [Évaluation du modèle](#évaluation-du-modèle))
  - Charge le modèle entraîné depuis `models/xgboost_regression.pkl`
  - Récupère les 30 dernières observations d'un patient
  - Prépare les features (même format que l'entraînement)
  - Fait les prédictions et calcule le niveau d'alerte

#### Utilitaires

- **create_users.py** : Crée les utilisateurs pour l'authentification Flask
- **check_patient_observations.py** : Vérifie le nombre d'observations par patient dans Elasticsearch

## Technologies Utilisées

### Backend et Langages
- **Python 3.9** : Langage principal
- **Flask 2.3.3** : Framework web pour le dashboard
- **Pandas 2.0.3** : Manipulation de données
- **NumPy 1.24.3** : Calculs numériques

### Streaming et Messagerie
- **Apache Kafka 7.5.0** : Plateforme de streaming
- **Zookeeper 7.5.0** : Coordination pour Kafka
- **kafka-python 2.0.2** : Client Python pour Kafka

### Base de Données et Recherche
- **Elasticsearch 8.11.0** : Base de données NoSQL
- **elasticsearch 8.11.0** : Client Python pour Elasticsearch

### Visualisation
- **Kibana 8.11.0** : Interface de visualisation
- **Matplotlib 3.7.2** : Visualisation Python (pour ML)
- **Seaborn 0.12.2** : Visualisation statistique

### Machine Learning
- **XGBoost 2.0.0** : Gradient Boosting optimisé
- **scikit-learn 1.3.0** : Random Forest et métriques
- **joblib 1.3.1** : Sauvegarde/chargement des modèles

### Conteneurisation
- **Docker** : Conteneurisation des services
- **Docker Compose** : Orchestration multi-conteneurs

### Sécurité et Authentification
- **bcrypt 4.0.1** : Hashage des mots de passe
- **Flask-CORS 4.0.0** : Gestion CORS

## Installation et Démarrage Local

### Prérequis

- Docker Desktop installé et démarré
- Git
- PowerShell (Windows) ou Bash (Linux/Mac)

### Installation Rapide

1. **Cloner le dépôt** :
```bash
git clone https://github.com/khoubaib30/blood_pressure_monitoring_system.git
cd blood_pressure_monitoring_system
```

2. **Créer le fichier d'environnement** :
```powershell
# Windows PowerShell
Copy-Item env.example .env

# Linux/Mac
cp env.example .env
```

3. **Créer les comptes de démonstration du dashboard** (le mot de passe est demandé au lancement) :
```bash
python create_users.py
```
Cela crée `data/users.json` (ignoré par Git) avec deux comptes : `admin@example.com` et `user@example.com`.

4. **Démarrer tous les services** :
```bash
# Avec rebuild des images
docker compose up -d --build

# Sans rebuild (si les images existent déjà)
docker compose up -d
```

5. **Accéder aux interfaces** :
   - **Dashboard Flask** : http://localhost:5000
   - **Kibana** : http://localhost:5601
   - **Elasticsearch** : http://localhost:9200

### Configuration (Optionnel)

Les ports et autres paramètres peuvent être modifiés dans le fichier `.env` (voir `env.example` pour la liste complète des variables).



## Structure du Projet

```
DS_projet/
├── src/
│   ├── producer.py              # Génère des données de pression artérielle
│   ├── consumer.py              # Consomme Kafka et envoie à Elasticsearch
│   ├── monitoring_dashboard.py  # Application Flask principale
│   ├── ml_inference.py          # Prédictions ML en temps réel
│   ├── ml_train_xgboost.py      # Entraînement modèle XGBoost
│   ├── ml_train_random_forest.py # Entraînement modèle Random Forest
│   ├── ml_evaluate_baselines.py # Évaluation : XGBoost vs baselines (validation croisée)
│   ├── ml_data_generator.py     # Génération de données d'entraînement
│   ├── patient_profile.py       # Profils de patients simulés
│   ├── elasticsearch_connector.py # Connexion Elasticsearch
│   ├── auth.py                  # Authentification
│   └── templates/               # Templates HTML Flask
│       ├── dashboard.html       # Dashboard principal
│       ├── predictions.html     # Page prédictions ML
│       └── login.html           # Page de connexion
├── data/
│   ├── blood_pressure_data.csv  # Données historiques
│   └── ml_training_data.csv     # Données d'entraînement ML
├── models/                      # Modèles ML entraînés
├── kibana/                      # Dashboards Kibana (saved objects)
│   └── saved_objects.ndjson     # Export des dashboards Kibana
├── docker-compose.yml          # Configuration Docker
├── Dockerfile.*                 # Images Docker
├── requirements.txt            # Dépendances Python
└── README.md                   # Ce fichier
```

## Utilisation

### Dashboard Web

1. Accéder à http://localhost:5000
2. Se connecter avec les identifiants créés (voir `create_users.py`)
3. **Dashboard Principal** : Visualisation en temps réel des données
4. **Prédictions ML** : Prédictions de risque pour chaque patient

### Prédictions Machine Learning

Le système prédit pour chaque patient :
- **Risque 1h** : Probabilité de crise hypertensive dans 1 heure
- **Risque 6h** : Probabilité de crise hypertensive dans 6 heures (indicateur principal)
- **Risque 24h** : Probabilité de crise hypertensive dans 24 heures
- **Niveau d'Alerte** : Basé sur le Risque 6h
  - **CRITICAL** : ≥ 60% - Intervention immédiate
  - **HIGH** : ≥ 40% - Surveillance renforcée
  - **MEDIUM** : ≥ 20% - Surveillance normale
  - **LOW** : < 20% - Surveillance standard

### Kibana

1. Accéder à http://localhost:5601
2. Les dashboards sont automatiquement importés au démarrage depuis `kibana/saved_objects.ndjson` (si le fichier existe)
3. Créer/modifier des visualisations selon vos besoins


## Machine Learning

### Modèles Disponibles

- **XGBoost** : Gradient Boosting optimisé (modèle utilisé en production)
- **Random Forest** : Ensemble de décisions trees (modèle d'entraînement pour comparaison)

**Note** : XGBoost et Random Forest obtiennent des performances très proches. XGBoost est retenu pour les prédictions en temps réel car il est légèrement meilleur sur les trois horizons.

## Évaluation du modèle

Le modèle est évalué en **validation croisée à 5 plis** sur les 5 000 séquences d'entraînement. Chaque séquence correspond à un patient différent, le découpage se fait donc par patient. XGBoost est comparé à deux baselines :

- **Moyenne** : prédit toujours le risque moyen observé à l'entraînement (aucun modèle) ;
- **Linéaire sur les dernières mesures** : régression linéaire sur la dernière mesure et la moyenne des 5 dernières mesures (pression systolique et diastolique).

| Modèle | MAE 1 h | MAE 6 h | MAE 24 h | R² (1 h / 6 h / 24 h) |
|---|---|---|---|---|
| Moyenne (sans modèle) | 0.165 | 0.193 | 0.223 | 0.00 / 0.00 / 0.00 |
| Linéaire sur les dernières mesures | 0.093 | 0.108 | 0.117 | 0.60 / 0.67 / 0.71 |
| Random Forest | 0.050 | 0.054 | 0.061 | 0.80 / 0.84 / 0.86 |
| **XGBoost** | **0.050** | **0.053** | **0.059** | **0.81 / 0.86 / 0.87** |

**Résultat :** XGBoost réduit l'erreur (MAE) de **46 % à 1 h** et d'environ **50 % à 6 h et 24 h** par rapport à la baseline linéaire. Le modèle exploite donc la tendance des 30 dernières mesures, et pas seulement la dernière valeur.

Pour reproduire ces résultats :

```bash
python src/ml_evaluate_baselines.py
```

### Limites

- **Données synthétiques.** Les séquences sont générées par un simulateur de patients (pression de base, tendance, rythme circadien, bruit). La cible correspond à la proportion de mesures futures au-dessus du seuil de crise (180/120 mmHg).
- **Biais de génération.** La cible est ensuite ajustée selon le profil de risque du patient (faible, moyen, élevé), qui détermine aussi sa pression de base. Le modèle apprend donc en partie la règle de simulation : les scores obtenus sont une borne haute, pas une performance clinique. C'est pour cette raison que le modèle est comparé à des baselines plutôt que jugé sur son R² seul.
- **Sur des données réelles**, il faudrait valider avec un découpage par patient et dans le temps, et vérifier la calibration des probabilités avant tout usage clinique.

