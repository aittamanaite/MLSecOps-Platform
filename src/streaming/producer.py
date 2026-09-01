import os
import glob
import json
import logging
<<<<<<< HEAD
import pandas as pd
import time
=======
import time

import numpy as np
import pandas as pd
>>>>>>> 6c556c4 (Initial commit)
from kafka import KafkaProducer
from kafka.errors import KafkaError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

<<<<<<< HEAD
=======
# Valeurs "sales" typiques du dataset CIC-IDS2017 (colonnes Flow Bytes/s, Flow Packets/s)
NA_VALUES = ["", "Infinity", "-Infinity", "infinity", "inf", "-inf", "NaN", "nan", "NULL", "null"]


>>>>>>> 6c556c4 (Initial commit)
def get_kafka_producer(bootstrap_servers="redpanda:9092", timeout_s: int = 60):
    """
    Create a KafkaProducer with retries and exponential backoff until `timeout_s` seconds.
    This helps when the broker container is still initializing at startup.
<<<<<<< HEAD
=======

    Le producteur est réglé pour le débit (batching + compression) afin de pouvoir
    pousser plusieurs centaines de milliers d'événements sans s'écrouler.
>>>>>>> 6c556c4 (Initial commit)
    """
    end_time = time.time() + timeout_s
    attempt = 0
    while True:
        try:
            attempt += 1
            logging.info(f"Creating KafkaProducer (attempt={attempt}) to {bootstrap_servers}")
            producer = KafkaProducer(
                bootstrap_servers=[bootstrap_servers],
<<<<<<< HEAD
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
=======
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                # --- Réglages de débit (throughput) ---
                acks=1,
                linger_ms=50,             # laisse le temps de constituer des lots
                batch_size=256 * 1024,    # 256 KB par lot
                compression_type="gzip",  # réduit fortement le volume réseau
                buffer_memory=128 * 1024 * 1024,
                max_in_flight_requests_per_connection=5,
                retries=5,
>>>>>>> 6c556c4 (Initial commit)
            )
            # perform a quick metadata request to ensure bootstrap succeeded
            producer.bootstrap_connected()
            logging.info("KafkaProducer bootstrap succeeded")
            return producer
        except KafkaError as e:
            remaining = end_time - time.time()
            logging.warning(f"Kafka bootstrap attempt {attempt} failed: {e}; retrying, {max(0,int(remaining))}s left")
            if remaining <= 0:
                logging.error("Kafka bootstrap timed out")
                raise
            sleep = min(5 * (2 ** (attempt - 1)), remaining, 10)
            time.sleep(sleep)

<<<<<<< HEAD
=======

>>>>>>> 6c556c4 (Initial commit)
def get_project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))


<<<<<<< HEAD
def run_producer(batch_size=1000):
    """
    Lit les fichiers CSV dans data/raw/ et les publie dans le topic 'raw-logs'
    simulant ainsi un flux d'ingestion en temps réel.
=======
def _sanitize_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """
    Rend le chunk sérialisable en JSON valide :
    - remplace +inf/-inf par NaN
    - convertit tous les NaN/NaT en None (=> `null` en JSON, et non `NaN` invalide)
    """
    chunk = chunk.replace([np.inf, -np.inf], np.nan)
    # astype(object) est nécessaire pour pouvoir stocker None dans des colonnes numériques
    return chunk.astype(object).where(pd.notna(chunk), None)


def _chunk_iterators(csv_files, batch_size):
    """Ouvre un itérateur de chunks par fichier CSV (lecture paresseuse, faible mémoire)."""
    # CIC-IDS2017 utilise l'encodage Windows-1252 (cp1252) : certains labels
    # contiennent un tiret 0x96 ("Web Attack – Brute Force"). Lu en UTF-8/latin-1
    # standard cela produit un caractère de remplacement "" qui casse le
    # regroupement par label dans dbt/ML. cp1252 décode correctement ce tiret.
    encoding = os.getenv("CSV_ENCODING", "cp1252")
    iterators = []
    for filepath in csv_files:
        try:
            reader = pd.read_csv(
                filepath,
                chunksize=batch_size,
                na_values=NA_VALUES,
                keep_default_na=True,
                low_memory=False,
                encoding=encoding,
                encoding_errors="replace",
                on_bad_lines="skip",
            )
            iterators.append((os.path.basename(filepath), reader))
        except Exception as e:  # fichier corrompu -> on continue avec les autres
            logging.warning(f"Impossible d'ouvrir {filepath}: {e}")
    return iterators


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
>>>>>>> 6c556c4 (Initial commit)
    """
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
    topic = os.getenv("KAFKA_RAW_TOPIC", "raw-logs")
    data_dir = os.path.join(get_project_root(), "data", "raw")
<<<<<<< HEAD
    
    producer = get_kafka_producer(bootstrap_servers)
    
    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
=======

    if max_records is None:
        max_records = int(os.getenv("STREAM_MAX_RECORDS", "0"))
    if max_records <= 0:
        max_records = None  # 0 => aucune limite : on lit tout le dataset brut
    if chunk_stride is None:
        chunk_stride = max(1, int(os.getenv("PRODUCER_CHUNK_STRIDE", "1")))

    csv_files = sorted(glob.glob(os.path.join(data_dir, "*.csv")))
>>>>>>> 6c556c4 (Initial commit)
    if not csv_files:
        logging.warning("Aucun fichier CSV trouvé pour l'ingestion.")
        return 0

<<<<<<< HEAD
    total_published = 0
    
    for filepath in csv_files:
        logging.info(f"Lecture du fichier: {filepath}")
        
        # Lecture par chunks pour ne pas saturer la mémoire et simuler un flux
        for chunk in pd.read_csv(filepath, chunksize=batch_size, keep_default_na=False):
            # Remplacement des éventuelles valeurs infinies générées par pandas
            chunk = chunk.replace([float('inf'), float('-inf')], None)
            records = chunk.to_dict(orient="records")
            
            for record in records:
                producer.send(topic, value=record)
                total_published += 1
                
            producer.flush()
            logging.info(f"Publié {len(records)} événements sur {topic}.")
            break # Dans le cadre du micro-batching, on traite un chunk à la fois pour la démo
            
    producer.close()
    return total_published

=======
    target_str = "ILLIMITÉ (tout le dataset)" if max_records is None else f"{max_records}"
    logging.info(
        f"{len(csv_files)} fichier(s) CSV détecté(s). Objectif de publication : {target_str} événements "
        f"(batch_size={batch_size}, chunk_stride={chunk_stride})."
    )


    producer = get_kafka_producer(bootstrap_servers)

    iterators = _chunk_iterators(csv_files, batch_size)
    total_published = 0
    start = time.time()

    try:
        # Round-robin : on prend un chunk de chaque fichier à tour de rôle
        # (max_records=None => on lit intégralement tous les fichiers)
        while iterators and (max_records is None or total_published < max_records):
            still_active = []
            for name, reader in iterators:
                if total_published >= max_records:
                    still_active.append((name, reader))
                    continue
                try:
                    chunk = next(reader)
                except StopIteration:
                    logging.info(f"Fichier terminé : {name}")
                    continue
                except Exception as e:
                    logging.warning(f"Erreur de lecture sur {name}: {e}")
                    continue

                chunk = _sanitize_chunk(chunk)
                records = chunk.to_dict(orient="records")

                # Ne pas dépasser l'objectif
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
                    logging.info(
                        f"Progression : {total_published}/{max_records} événements publiés "
                        f"({total_published/elapsed:.0f} msg/s)"
                    )

            iterators = still_active
            producer.flush()

        producer.flush()
    finally:
        producer.close()

    elapsed = max(time.time() - start, 1e-6)
    logging.info(
        f"Ingestion terminée : {total_published} événements publiés sur '{topic}' "
        f"en {elapsed:.1f}s ({total_published/elapsed:.0f} msg/s)."
    )
    return total_published


>>>>>>> 6c556c4 (Initial commit)
if __name__ == "__main__":
    run_producer()
