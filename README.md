Cybersecurity Threat Detection MLOps Platform

An end-to-end Machine Learning Operations (MLOps) platform for real-time cybersecurity log processing, data transformation, and alerting. The repository uses Dagster for orchestration, Redpanda for Kafka streaming, and dbt with DuckDB for batch transformation.

This platform is built to:
- ingest raw network logs from `data/raw/`
- stream events into Kafka topics `raw-logs`, `cleaned-logs`, and `app-errors`
- apply cleaning and simple ML inference in a Dagster asset pipeline
- materialize output data and save inspection exports under `data/exports/`
- run dbt models against DuckDB at `dbt_project/target/duck.db`

## 🚀 What the pipeline does

1. `src/streaming/producer.py` reads CSV files from `data/raw/` and publishes records to Redpanda topic `raw-logs`.
2. `src/streaming/cleaner.py` consumes `raw-logs`, cleans records, republishes them to `cleaned-logs`, and writes `data/exports/cleaned_logs.jsonl`.
3. `src/streaming/inference.py` consumes `cleaned-logs`, runs simple anomaly inference, publishes alerts to `app-errors`, and writes `data/exports/app_errors.jsonl`.
4. `dbt` runs SQL models from `dbt_project/models/` against DuckDB and stores results in `dbt_project/target/duck.db`.
5. `src/orchestration/assets.py` defines Dagster assets that orchestrate producer, cleaner, and inference steps.
6. `src/quality/data_quality.py` valide la qualité des données à chaque étape du pipeline (complétude, validité, intégrité).

## 🔧 Services and how to run them

### Start Redpanda

```bash
cd /home/houssame/my_project/MLSecOps-Platform
docker compose up --build redpanda
```

Redpanda provides Kafka brokers on `localhost:9092` and the broker is used by the streaming assets.

### Start Dagster UI and daemon

```bash
docker compose up --build dagster dagster-daemon
```

- `dagster` exposes the UI at `http://localhost:3000`
- `dagster-daemon` runs sensors and schedules
- Both containers share `PYTHONPATH=/app` and `DAGSTER_HOME=/app/dagster_home`

### Run dbt

```bash
docker compose run --rm dbt
```

This executes `dbt run --profiles-dir /app/dbt_project` inside the `dbt` service. The DuckDB database file is written to:

```bash
dbt_project/target/duck.db
```

### Run the full stack

```bash
docker compose up --build
```

This will start Redpanda, Dagster, Dagster daemon, and dbt together. If you want manual control, start Redpanda first and then the Dagster services.

## 📁 Where processed data is stored

- Raw source CSV files: `data/raw/`
- Cleaned streaming export: `data/exports/cleaned_logs.jsonl`
- Anomaly alert export: `data/exports/app_errors.jsonl`
- dbt DuckDB target: `dbt_project/target/duck.db`

## 🧪 Manual test commands

### Ingest raw CSV files manually

```bash
docker compose exec dagster python src/streaming/producer.py
```

### Run the cleaner manually

```bash
docker compose exec dagster python src/streaming/cleaner.py
```

### Run inference manually

```bash
docker compose exec dagster python src/streaming/inference.py
```

### Run dbt tests

```bash
docker compose exec dbt bash -c "cd /app/dbt_project && dbt test --profiles-dir /app/dbt_project"
```

### Inspect exported data files

```bash
ls -la data/exports
head -n 5 data/exports/cleaned_logs.jsonl
head -n 5 data/exports/app_errors.jsonl
```

## 🛡️ Qualité des données (Data Quality)

Le module `src/quality/data_quality.py` implémente des règles de qualité des données qui s'exécutent automatiquement à chaque étape du pipeline. En cas d'échec, le pipeline **s'arrête immédiatement** (hard gate), comme dans un environnement de production.

### Architecture des portes de qualité

```
CSV (data/raw/)                                                   
     │                                                            
     ▼                                                            
┌──────────────────────────────┐                                  
│  PORTE 1 : validate_raw_csv  │  ◄── 12 règles (complétude,     
│  Validation des fichiers CSV │      validité, intégrité)        
└──────────┬───────────────────┘                                  
           │ ✅ PASS                                              
           ▼                                                      
     producer.py → Kafka raw-logs                                 
           │                                                      
           ▼                                                      
     cleaner.py → Kafka cleaned-logs                              
           │                                                      
           ▼                                                      
┌──────────────────────────────────────┐                          
│  PORTE 2 : validate_cleaned_records  │  ◄── 6 règles           
│  Validation des données nettoyées    │                          
└──────────┬───────────────────────────┘                          
           │ ✅ PASS                                              
           ▼                                                      
     inference.py → Kafka app-errors                              
           │                                                      
           ▼                                                      
┌──────────────────────────────────────┐                          
│  PORTE 3 : validate_inference_output │  ◄── 5 règles           
│  Validation de la sortie ML          │                          
└──────────┬───────────────────────────┘                          
           │ ✅ PASS                                              
           ▼                                                      
     Pipeline terminé avec succès                                 
```

> **❌ En cas d'échec** : une exception `DataQualityError` est levée avec un rapport détaillé, et le pipeline Dagster s'arrête.

### Porte 1 — Validation des CSV bruts (`validate_raw_csv`)

Exécutée **avant l'ingestion** sur les fichiers CSV du dossier `data/raw/` :

| # | Règle | Catégorie | Description |
|---|---|---|---|
| C1 | `row_count_minimum` | Complétude | Le fichier doit contenir au moins 1 ligne de données |
| C2 | `column_count_match` | Complétude | Le CSV doit avoir exactement 79 colonnes (schéma CICIDS2017) |
| C3 | `critical_columns_present` | Complétude | Les colonnes `Destination Port` et `Label` doivent exister |
| C4 | `label_null_rate` | Complétude | Le taux de valeurs nulles dans `Label` doit être ≤ 5% |
| C5 | `no_fully_empty_rows` | Complétude | Aucune ligne entièrement vide (toutes les valeurs NaN) |
| C6 | `destination_port_null_rate` | Complétude | Le taux de nulls dans `Destination Port` doit être ≤ 5% |
| V1 | `port_range_valid` | Validité | Les ports doivent être dans l'intervalle [0, 65535] |
| V2 | `label_values_valid` | Validité | Les labels doivent être des catégories CICIDS2017 connues (BENIGN, DoS Hulk, PortScan, etc.) |
| V3 | `no_infinite_values` | Validité | Aucune valeur infinie (`Inf`, `-Inf`) dans les colonnes numériques |
| V4 | `non_negative_numerics` | Validité | Les colonnes de flux et paquets doivent être ≥ 0 |
| I1 | `duplicate_row_rate` | Intégrité | Le taux de doublons doit être < 1% |
| I2 | `schema_column_match` | Intégrité | Les noms de colonnes doivent correspondre au schéma CICIDS2017 attendu |

### Porte 2 — Validation des données nettoyées (`validate_cleaned_records`)

Exécutée **après le nettoyage** sur le fichier `data/exports/cleaned_logs.jsonl` :

| # | Règle | Catégorie | Description |
|---|---|---|---|
| C1 | `record_count_minimum` | Complétude | Au moins 1 enregistrement nettoyé produit |
| C2 | `critical_keys_present` | Complétude | Chaque enregistrement contient les clés : `destination_port`, `label`, `flow_duration`, `total_fwd_packets` |
| V1 | `keys_normalized` | Validité | Toutes les clés sont en snake_case (minuscules, underscores) |
| V2 | `port_values_valid` | Validité | Les ports restent dans [0, 65535] après nettoyage |
| V3 | `cleaned_label_values_valid` | Validité | Les labels restent des valeurs CICIDS2017 valides |
| I1 | `record_field_count` | Intégrité | Chaque enregistrement a au moins 10 champs (détection de corruption) |

### Porte 3 — Validation de la sortie d'inférence (`validate_inference_output`)

Exécutée **après l'inférence ML** sur le fichier `data/exports/app_errors.jsonl` :

| # | Règle | Catégorie | Description |
|---|---|---|---|
| C1 | `ml_metadata_present` | Complétude | Chaque anomalie contient `ml_confidence_score` et `ml_model_version` |
| V1 | `confidence_range_valid` | Validité | Le score de confiance est un float dans [0.0, 1.0] |
| V2 | `model_version_valid` | Validité | La version du modèle est une chaîne non vide |
| V3 | `threshold_consistency` | Validité | Tous les scores de confiance sont > 0.80 (seuil d'anomalie) |
| I1 | `anomaly_count_plausible` | Intégrité | Le nombre d'anomalies ne dépasse pas le total de messages traités |

### Exécution des tests de qualité

```bash
# Exécuter tous les tests de qualité des données
pytest tests/test_data_quality.py -v

# Exécuter les tests dbt (schéma et contraintes)
docker compose exec dbt bash -c "cd /app/dbt_project && dbt test --profiles-dir /app/dbt_project"
```

La suite de tests comprend **29 tests unitaires** couvrant :
- Données valides (doivent passer)
- Données invalides (doivent échouer avec la bonne erreur)
- Cas limites (DataFrames vides, valeurs aux frontières des ports, etc.)

## 🔗 Intégration avec les outils de test et de qualité

Ce dépôt est conçu pour une intégration facile avec :

- **Module de qualité intégré** : `src/quality/data_quality.py` — validation automatique à chaque étape du pipeline
- **dbt tests** : tests de schéma dans `dbt_project/models/staging/schema.yml` (`not_null`, `unique`, `accepted_values`)
- **Great Expectations** : ajouter des suites d'attentes sur `data/raw/` et `data/exports/`
- **kafka-console-consumer / rpk / kcat** : inspection directe des topics Kafka
- **Prometheus / Grafana** : instrumentation de Dagster et des services de streaming
- **MLflow** : suivi des versions de modèles et des métriques de performance

### Workflow de qualité des données

1. Placer les fichiers CSV dans `data/raw/`
2. Le sensor Dagster détecte les nouveaux fichiers et déclenche le pipeline
3. **Porte 1** : validation des CSV bruts (complétude, validité, intégrité)
4. Ingestion et nettoyage des données
5. **Porte 2** : validation des données nettoyées
6. Inférence ML et détection d'anomalies
7. **Porte 3** : validation de la sortie d'inférence
8. En cas d'échec à n'importe quelle porte → le pipeline s'arrête avec un rapport détaillé

## 🧩 Notes

- `data/raw/` is the source ingestion folder. Add new CSV files there for the streaming sensor.
- `data/exports/` is now used to capture the latest cleaned and anomaly output.
- The pipeline is currently focused on stream simulation and simple rule-based/anomaly inference.
- For a production-ready deployment, add proper Kafka topic management, persistent storage, and a real ML model.

## 📦 Structure du projet

```bash
.
├── data/
│   ├── exports/             # Exports du streaming (données nettoyées, anomalies)
│   └── raw/                 # Fichiers CSV bruts (CICIDS2017)
├── dbt_project/
│   ├── models/
│   │   └── staging/
│   │       ├── stg_network_logs.sql   # Modèle SQL dbt
│   │       └── schema.yml             # Tests de schéma dbt (not_null, unique, accepted_values)
│   ├── target/              # Artefacts DuckDB et sorties compilées
│   └── profiles.yml         # Profil dbt DuckDB
├── src/
│   ├── ingestion/           # Téléchargement et ingestion des données
│   ├── orchestration/       # Assets et définitions Dagster
│   │   ├── assets.py        # Assets avec portes de qualité intégrées
│   │   └── definitions.py   # Jobs, sensors et schedules Dagster
│   ├── quality/             # Module de qualité des données
│   │   ├── __init__.py
│   │   └── data_quality.py  # Règles de validation (complétude, validité, intégrité)
│   ├── streaming/           # Logique de traitement Kafka (producer/consumer)
│   └── README.md            # Notes développeur
├── tests/
│   ├── test_ingestion.py    # Tests d'ingestion
│   └── test_data_quality.py # 29 tests unitaires de qualité des données
├── docker-compose.yml       # Orchestration des services
├── requirements.txt         # Dépendances Python
└── README.md
```
