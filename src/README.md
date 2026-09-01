# شرح مشروع ML-SecOps داخل `src`

هذا المستند يشرح دور الملفات والمجلدات المتعلقة بـ `Dagster`, `dbt`, و `streaming` في هذا المشروع.

Ce document explique le rôle des fichiers et des dossiers liés à `Dagster`, `dbt` et `streaming` dans ce projet.

## 📁 هيكل المجلد `src`

- `src/ingestion/`
  - يحتوي على سكربتات استيراد البيانات.
  - `ingest.py`: يُعد نقطة دخول بسيطة لتحضير مجلد `data/raw/` واستقبال البيانات.
  - `download_data.py`: (إذا كان موجودًا) يُستخدم لتنزيل مجموعة بيانات من الإنترنت إلى `data/raw/`.

- `src/orchestration/`
  - يحتوي على تعريفات Dagster الرئيسية.
  - `assets.py`: يحتوي على `assets` لـ Dagster التي تمثل المهام الأساسية في خط الأنابيب:
    - `streaming_ingestion_asset`: يقرأ بيانات CSV المحلية وينشرها إلى Kafka/Redpanda.
    - `streaming_cleaning_asset`: يقرأ من الـ topic الخام `raw-logs` وينظف الرسائل ثم يرسلها إلى `cleaned-logs`.
    - `model_inference_asset`: يستهلك البيانات النظيفة ويشتغل نموذج استدلال بسيط ويرسل النتائج إلى `app-errors`.
  - `definitions.py`: يجمع الأصول (`assets`) في تعريف Dagster كامل:
    - job رئيسي `realtime_mlsecops_job` يشغل التسلسل `ingest -> clean -> inference`.
    - sensor يراقب مجلد `data/raw/` ويشغل الدفق عند إضافة ملفات جديدة.
    - schedule اختياري لتشغيل دفق البيانات بشكل دوري.

- `src/streaming/`
  - يحتوي على منطق المعالجة الواقعي للسيرفر:
  - `producer.py`: يقرأ ملفات CSV من `data/raw/` ويُرسِل سجلات إلى Kafka topic `raw-logs`.
  - `cleaner.py`: يقرأ بيانات من `raw-logs`، ينظف السجلات ويرسلها إلى `cleaned-logs`.
  - `inference.py`: يقرأ من `cleaned-logs`، يطبق نموذج تنبؤ وهمي، ويضع النتائج المشبوهة في `app-errors`.

- `src/ingestion/`
  - Contient les scripts d'ingestion de données.
  - `ingest.py` : point d'entrée simple pour préparer le dossier `data/raw/` et recevoir les données.
  - `download_data.py` : (si présent) est utilisé pour télécharger un jeu de données d'internet vers `data/raw/`.

- `src/orchestration/`
  - Contient les définitions principales de Dagster.
  - `assets.py` : contient les `assets` Dagster qui représentent les tâches du pipeline :
    - `streaming_ingestion_asset` : lit les CSV locaux et les publie sur Kafka/Redpanda.
    - `streaming_cleaning_asset` : lit du topic brut `raw-logs`, nettoie les messages et les envoie vers `cleaned-logs`.
    - `model_inference_asset` : consomme les données nettoyées, exécute un modèle d'inférence simple et envoie les résultats à `app-errors`.
  - `definitions.py` : combine les assets dans une définition Dagster complète :
    - job principal `realtime_mlsecops_job` exécute la séquence `ingest -> clean -> inference`.
    - sensor qui surveille le dossier `data/raw/` et déclenche le pipeline quand de nouveaux fichiers apparaissent.
    - schedule optionnel pour exécuter le pipeline périodiquement.

- `src/streaming/`
  - Contient la logique de traitement en temps réel du serveur :
  - `producer.py` : lit les fichiers CSV de `data/raw/` et envoie des enregistrements au topic Kafka `raw-logs`.
  - `cleaner.py` : lit les données de `raw-logs`, nettoie les enregistrements et les envoie à `cleaned-logs`.
  - `inference.py` : lit de `cleaned-logs`, applique un modèle de prédiction simplifié et envoie les alertes à `app-errors`.

## 🔧 ما هي وظيفة `Dagster` هنا؟

- Dagster هو أداة الأتمتة Orchestration لـ Python.
- في هذا المشروع، `Dagster` يدير تسلسل المهام والاعتمادات ما بين:
  - جلب البيانات من ملفات CSV
  - تنظيف البيانات
  - تنفيذ نموذج ML
- `Dagster` يسمح بتشغيل هذه الخطوات كأصول (`assets`) ويقدم واجهة مراقبة وإدارة عبر `dagster-webserver`.

## 🔧 Quel est le rôle de `Dagster` ici ?

- Dagster est un outil d'orchestration Python.
- Dans ce projet, `Dagster` gère la séquence des tâches et les dépendances entre :
  - l'import CSV
  - le nettoyage des données
  - l'exécution du modèle ML
- `Dagster` permet d'exécuter ces étapes comme des `assets` et propose une interface de supervision via `dagster-webserver`.

## 📊 ما هي وظيفة `dbt` هنا؟

- `dbt` مهيأ للعمل مع DuckDB هنا.
- يهدف `dbt` إلى تحويل البيانات الجدولية بطريقة قابلة لإعادة الاستخدام، خاصة في `dbt_project/`.
- تم إعداد ملف `dbt_project/dbt_project.yml` و `profiles.yml` للعمل على قاعدة DuckDB محلية.
- النموذج البسيط الموجود في `dbt_project/models/staging/stg_network_logs.sql` هو مثال لإظهار كيف يمكن تحضير بيانات متغيرة.

## 📊 Quel est le rôle de `dbt` ici ?

- `dbt` est configuré pour fonctionner avec DuckDB.
- `dbt` transforme les données tabulaires de manière réutilisable, principalement dans `dbt_project/`.
- `dbt_project/dbt_project.yml` et `profiles.yml` sont configurés pour une base DuckDB locale.
- Le modèle simple dans `dbt_project/models/staging/stg_network_logs.sql` montre un exemple de transformation de données.

## ⛓ ما هو دور `streaming`؟

- `streaming` يضمن تحويل بيانات CSV إلى تدفق Kafka:
  - `producer.py` يحول ملفات CSV إلى رسائل Kafka.
  - `cleaner.py` يعالج الرسائل وينظف الحقول.
  - `inference.py` يحاكي نموذجًا يقوم بالكشف عن الهجمات ويرسل الإنذارات.
- جميع هذه المهام تعمل مع Redpanda كمزود Kafka محلي.

## ⛓ Quel est le rôle du `streaming` ?

- Le streaming convertit les CSV en flux Kafka :
  - `producer.py` transforme les fichiers CSV en messages Kafka.
  - `cleaner.py` traite les messages et nettoie les champs.
  - `inference.py` simule un modèle qui détecte les anomalies et envoie des alertes.
- Toutes les tâches utilisent Redpanda comme broker Kafka local.

## 🚀 كيف تشغل النظام الصحيح

### 1. تشغيل Docker Compose

من جذر المشروع:

```bash
docker compose up --build
```

- هذا يبني صورة Docker من `src/Dockerfile`.
- يشغل:
  - خدمة `dagster` على المنفذ `3000`
  - خدمة `redpanda` لـ Kafka
  - خدمة `dbt` التي تنفذ `dbt run` على `dbt_project`

## 🚀 Comment démarrer le système

### 1. Lancer Docker Compose

Depuis la racine du projet :

```bash
docker compose up --build
```

- construit l'image Docker à partir de `src/Dockerfile`.
- démarre :
  - le service `dagster` sur le port `3000`
  - le service `redpanda` pour Kafka
  - le service `dbt` qui exécute `dbt run` sur `dbt_project`

### 2. الدخول إلى واجهة Dagster

افتح المتصفح على:

```text
http://localhost:3000
```

### 2. Accès à l'interface Dagster

Ouvrez votre navigateur sur :

```text
http://localhost:3000
```

### 3. تشغيل تدفق البيانات الحقيقي

- استخدام `Dagster` عبر الويب أو من داخل الحاوية.
- يتم ربط `Dagster` بـ `src/orchestration/definitions.py` و `src/orchestration/assets.py`.
- عند اكتشاف ملفات CSV جديدة في `data/raw/`، سيبدأ الـ `sensor` معالجة جديدة.

### 3. Exécution du streaming en temps réel

- Utilisez `Dagster` via l'interface web ou depuis le conteneur.
- `Dagster` est raccordé à `src/orchestration/definitions.py` et `src/orchestration/assets.py`.
- Quand de nouveaux CSV apparaissent dans `data/raw/`, le sensor déclenche le pipeline.

### 4. أوامر dbt داخل الحاوية

لتشغيل dbt يدويًا داخل الحاوية:

```bash
docker compose run --rm dbt
```

أو إذا أردت تشغيل قاعدة dbt من داخل الحاوية `dagster`:

```bash
docker compose exec dagster sh -c "cd /app/dbt_project && dbt run --profiles-dir /app/dbt_project"
```

### 4. Commandes dbt dans le conteneur

Pour exécuter dbt manuellement dans le conteneur :

```bash
docker compose run --rm dbt
```

Ou, pour exécuter dbt depuis le conteneur `dagster` :

```bash
docker compose exec dagster sh -c "cd /app/dbt_project && dbt run --profiles-dir /app/dbt_project"
```

### 5. تشغيل Dagster daemon للـ sensors

الـ `sensor` مثل `csv_streaming_sensor` يحتاج إلى خدمة `dagster-daemon` تعمل دائماً.

أيضًا، يحتاج Dagster إلى متغير البيئة `DAGSTER_HOME` إلى مجلد موجود في النظام لتخزين البيانات الوصفية وملف `dagster.yaml` إذا كان موجودًا.

في إعداد Docker هذا، نستخدم:

- `DAGSTER_HOME=/app/dagster_home`
- يتم ربطه بمجلد محلي `./dagster_home`

لتشغيل `Dagster` و `dagster-daemon` معاً:

```bash
docker compose up --build dagster dagster-daemon
```

أو لتشغيل كل الخدمات بما في ذلك dbt و redpanda:

```bash
docker compose up --build
```

---

### 5. Démarrer le daemon Dagster pour les sensors

Un sensor comme `csv_streaming_sensor` nécessite le service `dagster-daemon` en cours d'exécution.

Dagster a également besoin de la variable d'environnement `DAGSTER_HOME` pointant vers un répertoire existant pour stocker les métadonnées et charger `dagster.yaml` si présent.

Dans cette configuration Docker, nous utilisons :

- `DAGSTER_HOME=/app/dagster_home`
- monté sur le dossier local `./dagster_home`

Pour lancer `Dagster` et `dagster-daemon` ensemble :

```bash
docker compose up --build dagster dagster-daemon
```

Ou pour lancer tous les services, y compris dbt et redpanda :

```bash
docker compose up --build
```

### 5. Démarrer le daemon Dagster pour les sensors

Un sensor comme `csv_streaming_sensor` nécessite le service `dagster-daemon` en cours d'exécution.

Pour lancer `Dagster` et `dagster-daemon` ensemble :

```bash
docker compose up --build dagster dagster-daemon
```

Ou pour démarrer tous les services, y compris dbt et redpanda :

```bash
docker compose up --build
```

### 6. تشغيل تنظيف البيانات + البث

يمكنك تشغيل كل مهمة يدويًا من داخل الحاوية:

```bash
docker compose exec dagster python src/streaming/producer.py
```

```bash
docker compose exec dagster python src/streaming/cleaner.py
```

```bash
docker compose exec dagster python src/streaming/inference.py
```

أو ترك Dagster يتولى الأمر عبر `job` و `sensor` في `definitions.py`.

### 6. Exécution manuelle du streaming

Vous pouvez exécuter chaque tâche manuellement depuis le conteneur :

```bash
docker compose exec dagster python src/streaming/producer.py
```

```bash
docker compose exec dagster python src/streaming/cleaner.py
```

```bash
docker compose exec dagster python src/streaming/inference.py
```

Ou laissez `Dagster` gérer le pipeline via le `job` et le `sensor` dans `definitions.py`.

## ✅ ملخص

- `src/ingestion/` للتحميل المسبق للبيانات.
- `src/orchestration/` لتشغيل Dagster.
- `src/streaming/` لتنفيذ التدفق عبر Kafka.
- `dbt_project/` لتحويل البيانات الجدولية باستخدام dbt + DuckDB.

## ✅ Résumé

- `src/ingestion/` pour l'importation des données.
- `src/orchestration/` pour exécuter Dagster.
- `src/streaming/` pour le pipeline Kafka.
- `dbt_project/` pour transformer les données tabulaires avec dbt + DuckDB.

إذا أردت، يمكنني الآن إضافة `README.md` في الجذر لتوضيح الأوامر خطوة بخطوة بطريقة أبسط أكثر.
Si vous voulez, je peux aussi ajouter un `README.md` à la racine pour expliquer les commandes étape par étape de manière plus simple.