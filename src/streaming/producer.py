import os
import glob
import json
import logging
import time
<<<<<<< HEAD
=======

>>>>>>> a9b26615667c811ba792659bef9dcc7c1fa578b2
import numpy as np
import pandas as pd
from kafka import KafkaProducer
from kafka.errors import KafkaError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

<<<<<<< HEAD
NA_VALUES = ['Infinity', 'NaN', 'inf', '-inf', '']

def get_kafka_producer():
    for attempt in range(5):
        try:
            return KafkaProducer(
                bootstrap_servers=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks=1,
                linger_ms=50,
                batch_size=262144,
                compression_type='gzip'
=======
# Valeurs "sales" typiques du dataset CIC-IDS2017 (colonnes Flow Bytes/s, Flow Packets/s)
NA_VALUES = ["", "Infinity", "-Infinity", "infinity", "inf", "-inf", "NaN", "nan", "NULL", "null"]


def get_kafka_producer(bootstrap_servers="redpanda:9092", timeout_s: int = 60):
    """
    Create a KafkaProducer with retries and exponential backoff until `timeout_s` seconds.
    This helps when the broker container is still initializing at startup.

    Le producteur est réglé pour le débit (batching + compression) afin de pouvoir
    pousser plusieurs centaines de milliers d'événements sans s'écrouler.
    """
    end_time = time.time() + timeout_s
    attempt = 0
    while True:
        try:
            attempt += 1
            logging.info(f"Creating KafkaProducer (attempt={attempt}) to {bootstrap_servers}")
            producer = KafkaProducer(
                bootstrap_servers=[bootstrap_servers],
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                # --- Réglages de débit (throughput) ---
                # (paramètres valides sur toutes les versions de kafka-python)
                acks=1,
                linger_ms=50,             # laisse le temps de constituer des lots
                batch_size=256 * 1024,    # 256 KB par lot
                compression_type="gzip",  # réduit fortement le volume réseau
                retries=5,
>>>>>>> a9b26615667c811ba792659bef9dcc7c1fa578b2
            )
        except KafkaError as e:
            logger.warning(f"Failed to connect to Kafka, attempt {attempt + 1}/5: {e}")
            time.sleep(2 ** attempt)
    raise RuntimeError("Could not connect to Kafka after multiple retries.")

<<<<<<< HEAD
def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _sanitize_chunk(chunk):
    chunk = chunk.replace([np.inf, -np.inf], np.nan)
    chunk = chunk.where(pd.notnull(chunk), None)
    return chunk
=======

def get_project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))


def _sanitize_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """
    Rend le chunk sérialisable en JSON valide et cohérent avec le dataset CIC-IDS2017 :
    - remplace +inf/-inf par NaN
    - remplace les valeurs négatives (ex: Flow Duration < 0) par 0, car les
      colonnes de flux sont par nature >= 0 ; un '-' isolé est une artefacts du CSV
    - convertit tous les NaN/NaT en None (=> `null` en JSON, et non `NaN` invalide)
    """
    chunk = chunk.replace([np.inf, -np.inf], np.nan)
    num_cols = chunk.select_dtypes(include=[np.number]).columns
    chunk[num_cols] = chunk[num_cols].clip(lower=0)
    # astype(object) est nécessaire pour pouvoir stocker None dans des colonnes numériques
    return chunk.astype(object).where(pd.notna(chunk), None)
>>>>>>> a9b26615667c811ba792659bef9dcc7c1fa578b2

def _chunk_iterators(file_paths, chunk_size):
    iterators = []
    for fp in file_paths:
        try:
            it = pd.read_csv(fp, chunksize=chunk_size, encoding='cp1252', na_values=NA_VALUES)
            iterators.append(it)
        except Exception as e:
            logger.error(f"Error reading {fp}: {e}")
    return iterators

def run_producer(batch_size=5000, max_records=None, chunk_stride=None):
    env_max = os.environ.get('STREAM_MAX_RECORDS')
    if max_records is None and env_max is not None:
        max_records = int(env_max) if env_max.strip() else None

<<<<<<< HEAD
    env_stride = os.environ.get('PRODUCER_CHUNK_STRIDE')
    if chunk_stride is None:
        chunk_stride = int(env_stride) if env_stride else 100
    
    root_dir = get_project_root()
    data_dir = os.path.join(root_dir, 'data', 'raw')
    csv_files = glob.glob(os.path.join(data_dir, '*.csv'))
    
    if not csv_files:
        logger.error("No CSV files found in data/raw.")
        return
        
    producer = get_kafka_producer()
=======
def run_producer(batch_size: int = 5000, max_records: int | None = None, chunk_stride: int | None = None):
    """
    Lit les fichiers CSV dans data/raw/ et les publie dans le topic 'raw-logs'
    simulant ainsi un flux d'ingestion en temps réel.

    Contrairement à la version précédente (qui s'arrêtait après le 1er chunk de
    chaque fichier), on parcourt ici TOUS les chunks, en alternant les fichiers
    (round-robin) pour que le flux contienne un mélange représentatif de
    BENIGN et des différentes attaques (DDoS, PortScan, WebAttacks, ...).

    Args:
        batch_size: nombre de lignes lues par chunk pandas.
        max_records: nombre maximum d'événements à publier (None => illimité).
                      Par défaut lu depuis STREAM_MAX_RECORDS.
        chunk_stride: 1 = flux séquentiel réaliste (défaut).
                      N > 1 = on publie 1 chunk puis on saute N-1 chunks, ce qui
                      étale l'échantillon sur toute la journée de trafic et
                      ramène beaucoup plus d'attaques (utile pour entraîner un modèle).
                      Par défaut lu depuis PRODUCER_CHUNK_STRIDE.
    """
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
    topic = os.getenv("KAFKA_RAW_TOPIC", "raw-logs")
    data_dir = os.path.join(get_project_root(), "data", "raw")

    if max_records is None:
        max_records = int(os.getenv("STREAM_MAX_RECORDS", "0"))
    if max_records is not None and max_records <= 0:
        max_records = None  # 0 => aucune limite : on lit tout le dataset brut
    if chunk_stride is None:
        chunk_stride = max(1, int(os.getenv("PRODUCER_CHUNK_STRIDE", "1")))

    # Défense défensive : None signifie "illimité" partout (jamais de comparaison
    # int >= None, qui lève TypeError).
    def _under_limit(published: int) -> bool:
        return max_records is None or published < max_records

    csv_files = sorted(glob.glob(os.path.join(data_dir, "*.csv")))
    if not csv_files:
        logging.warning("Aucun fichier CSV trouvé pour l'ingestion.")
        return 0

    target_str = "ILLIMITÉ (tout le dataset)" if max_records is None else f"{max_records}"
    logging.info(
        f"{len(csv_files)} fichier(s) CSV détecté(s). Objectif de publication : {target_str} événements "
        f"(batch_size={batch_size}, chunk_stride={chunk_stride})."
    )

    producer = get_kafka_producer(bootstrap_servers)

>>>>>>> a9b26615667c811ba792659bef9dcc7c1fa578b2
    iterators = _chunk_iterators(csv_files, batch_size)
    
    total_published = 0
    active_iterators = iterators[:]
    
    try:
<<<<<<< HEAD
        while active_iterators:
            if max_records is not None and total_published >= max_records:
                logger.info(f"Reached max_records ({max_records}). Stopping.")
                break
                
            for it in list(active_iterators):
=======
        # Round-robin : on prend un chunk de chaque fichier à tour de rôle
        # (max_records=None => on lit intégralement tous les fichiers)
        while iterators and _under_limit(total_published_param := total_published):
            still_active = []
            for name, reader in iterators:
                if not _under_limit(total_published):
                    still_active.append((name, reader))
                    continue
>>>>>>> a9b26615667c811ba792659bef9dcc7c1fa578b2
                try:
                    chunk = next(it)
                    sanitized_chunk = _sanitize_chunk(chunk)
                    
                    records = sanitized_chunk.to_dict('records')
                    
                    if max_records is not None:
                        remaining = max_records - total_published
                        records = records[:remaining]
                        
                    for record in records:
                        producer.send('raw-logs', record)
                        
                    total_published += len(records)
                    logger.info(f"Published {total_published} records total.")
                    
                    if max_records is not None and total_published >= max_records:
                        break
                        
                except StopIteration:
                    active_iterators.remove(it)
                except Exception as e:
<<<<<<< HEAD
                    logger.error(f"Error processing chunk: {e}")
                    active_iterators.remove(it)
                    
=======
                    logging.warning(f"Erreur de lecture sur {name}: {e}")
                    continue

                chunk = _sanitize_chunk(chunk)
                records = chunk.to_dict(orient="records")

                # Ne pas dépasser l'objectif (None => illimité : on garde tout)
                if max_records is None:
                    remaining = len(records)
                else:
                    remaining = max_records - total_published
                    if len(records) > remaining:
                        records = records[:remaining]

                for record in records:
                    producer.send(topic, value=record)
                    total_published += 1

                # Échantillonnage étalé : on saute des chunks pour couvrir
                # l'ensemble du fichier (et donc les périodes d'attaque).
                exhausted = False
                for _ in range(chunk_stride - 1):
                    try:
                        next(reader)
                    except StopIteration:
                        exhausted = True
                        break
                    except Exception:
                        break

                if not exhausted:
                    still_active.append((name, reader))

                if total_published % 20000 < len(records):
                    elapsed = max(time.time() - start, 1e-6)
                    target_str = "ILLIMITÉ" if max_records is None else f"{max_records}"
                    logging.info(
                        f"Progression : {total_published}/{target_str} événements publiés "
                        f"({total_published/elapsed:.0f} msg/s)"
                    )

            iterators = still_active
>>>>>>> a9b26615667c811ba792659bef9dcc7c1fa578b2
            producer.flush()
            time.sleep(0.01) # Small sleep to prevent tight loops
    finally:
        producer.close()
        logger.info("Producer closed.")

<<<<<<< HEAD
if __name__ == '__main__':
=======
    elapsed = max(time.time() - start, 1e-6)
    logging.info(
        f"Ingestion terminée : {total_published} événements publiés sur '{topic}' "
        f"en {elapsed:.1f}s ({total_published/elapsed:.0f} msg/s)."
    )
    return total_published


if __name__ == "__main__":
>>>>>>> a9b26615667c811ba792659bef9dcc7c1fa578b2
    run_producer()
