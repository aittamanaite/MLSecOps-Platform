import os
import json
import logging
import math
import time
<<<<<<< HEAD
=======

>>>>>>> a9b26615667c811ba792659bef9dcc7c1fa578b2
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

<<<<<<< HEAD
INVALID_STRINGS = {'', 'none', 'null', 'nan', 'inf', '-inf'}
=======
# Valeurs textuelles invalides rencontrées dans CIC-IDS2017
INVALID_STRINGS = {"", "infinity", "-infinity", "inf", "-inf", "nan", "null", "none", "na", "n/a"}
>>>>>>> a9b26615667c811ba792659bef9dcc7c1fa578b2

def get_kafka_clients():
    max_poll = int(os.environ.get('KAFKA_MAX_POLL_RECORDS', 500))
    consumer = KafkaConsumer(
        'raw-logs',
        bootstrap_servers=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        group_id='cleaner-group',
        value_deserializer=lambda v: json.loads(v.decode('utf-8')),
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        max_poll_records=max_poll,
        fetch_max_bytes=67108864,
        session_timeout_ms=60000,
        request_timeout_ms=120000
    )
    
    producer = KafkaProducer(
        bootstrap_servers=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        acks=1,
        linger_ms=50,
        batch_size=262144,
        compression_type='gzip'
    )
    return consumer, producer

<<<<<<< HEAD
def _coerce_value(val):
    if val is None:
        return 0.0
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return 0.0
    if isinstance(val, str):
        s = val.strip().lower()
        if s in INVALID_STRINGS:
            return 0.0
        try:
            return float(val)
        except ValueError:
            return val
    return val

def _normalize_label(label):
    if not isinstance(label, str):
        return 'benign'
    # Handle cp1252 decoded UTF-8 en-dash (\xe2\x80\x93)
    label = label.replace('\xe2\u20ac\u201c', '-')
    label = label.replace('\uFFFD', '-').replace('\u2013', '-').replace('\u2014', '-')
    label = label.encode('ascii', 'ignore').decode('ascii').strip().lower()
    label = label.replace('  ', ' - ')
    if label == '':
        return 'benign'
    return label
=======
def get_kafka_clients(bootstrap_servers, timeout_s: int = 60):
    """Create consumer and producer with retries until broker is available.

    IMPORTANT : `max_poll_records` vaut 500 par défaut dans kafka-python.
    C'est la raison pour laquelle un seul appel à consumer.poll() ne pouvait
    jamais retourner plus de 500 messages. On l'augmente ici et on boucle.
    """
    max_poll_records = int(os.getenv("KAFKA_MAX_POLL_RECORDS", "5000"))
    end_time = time.time() + timeout_s
    attempt = 0
    while True:
        try:
            attempt += 1
            logging.info(f"Creating Kafka consumer/producer (attempt={attempt}) to {bootstrap_servers}")
            consumer = KafkaConsumer(
                os.getenv("KAFKA_RAW_TOPIC", "raw-logs"),
                bootstrap_servers=[bootstrap_servers],
                group_id=os.getenv("KAFKA_CLEANER_GROUP", "cleaner-group"),
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                # --- Réglages de débit ---
                max_poll_records=max_poll_records,
                fetch_max_bytes=64 * 1024 * 1024,
                max_partition_fetch_bytes=16 * 1024 * 1024,
                fetch_max_wait_ms=500,
                session_timeout_ms=60000,
                request_timeout_ms=120000,
            )
            producer = KafkaProducer(
                bootstrap_servers=[bootstrap_servers],
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                acks=1,
                linger_ms=50,
                batch_size=256 * 1024,
                compression_type="gzip",
                retries=5,
            )
            # quick check
            producer.bootstrap_connected()
            logging.info(f"Kafka consumer/producer bootstrap succeeded (max_poll_records={max_poll_records})")
            return consumer, producer
        except KafkaError as e:
            remaining = end_time - time.time()
            logging.warning(f"Kafka client attempt {attempt} failed: {e}; retrying, {max(0,int(remaining))}s left")
            if remaining <= 0:
                logging.error("Kafka client bootstrap timed out")
                raise
            sleep = min(5 * (2 ** (attempt - 1)), remaining, 10)
            time.sleep(sleep)


def _normalize_label(label: str) -> str:
    """
    Uniformise le label d'attaque : les tirets exotiques (– — ‐ …) et le caractère
    de remplacement U+FFFD (présent tel quel dans le CSV : "Web Attack U+FFFD Brute Force")
    deviennent un '-' simple, et les espaces multiples sont réduits. Sans cela on
    obtient plusieurs variantes du même label.
    """
    text = str(label)
    for ch in ("\u2013", "\u2014", "\u2010", "\u2011", "\u2012", "\ufffd", "\x96"):
        text = text.replace(ch, "-")
    return " ".join(text.split())


def _coerce_value(value):
    """Normalise une valeur : None/inf/NaN -> 0, chaînes numériques -> nombre."""
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return 0
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lower() in INVALID_STRINGS:
            return 0
        try:
            num = float(stripped)
            if math.isnan(num) or math.isinf(num):
                return 0
            return int(num) if num.is_integer() else num
        except ValueError:
            return stripped
    return value

>>>>>>> a9b26615667c811ba792659bef9dcc7c1fa578b2

def clean_record(record):
    cleaned = {}
    for k, v in record.items():
<<<<<<< HEAD
        new_k = k.strip().lower().replace(' ', '_').replace('/', '_').replace('-', '_').replace('.', '_')
        cleaned[new_k] = _coerce_value(v)
    
    label = cleaned.get('label', 'benign')
    label = _normalize_label(label)
    cleaned['label'] = label
    cleaned['is_attack'] = 1 if label != 'benign' else 0
    cleaned['ingested_at'] = time.time()
=======
        # Standardisation des noms de colonnes
        new_key = (
            str(k)
            .strip()
            .lower()
            .replace(" ", "_")
            .replace("/", "_per_")
            .replace("-", "_")
            .replace(".", "_")
        )
        while "__" in new_key:
            new_key = new_key.replace("__", "_")
        cleaned[new_key] = _coerce_value(v)

    # --- Dérivation de la cible pour le modèle ML ---
    label = _normalize_label(cleaned.get("label", ""))
    if label:
        cleaned["label"] = label
        cleaned["is_attack"] = 0 if label.upper() == "BENIGN" else 1
    else:
        cleaned.setdefault("is_attack", 0)

    cleaned["ingested_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
>>>>>>> a9b26615667c811ba792659bef9dcc7c1fa578b2
    return cleaned

def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

<<<<<<< HEAD
def run_cleaner(max_messages=None, idle_polls_limit=None):
    env_max = os.environ.get('STREAM_MAX_RECORDS')
    if max_messages is None and env_max is not None:
        max_messages = int(env_max) if env_max.strip() else None

    env_idle = os.environ.get('KAFKA_IDLE_POLLS_LIMIT')
    if idle_polls_limit is None:
        idle_polls_limit = int(env_idle) if env_idle else 5
        
    poll_timeout_ms = int(os.environ.get('KAFKA_POLL_TIMEOUT_MS', 1000))
    export_append = os.environ.get('EXPORT_APPEND', 'false').lower() == 'true'
    idle_timeout_s = int(os.environ.get('KAFKA_IDLE_TIMEOUT_S', 10))
    
    consumer, producer = get_kafka_clients()
    
    root_dir = get_project_root()
    export_dir = os.path.join(root_dir, 'data', 'exports')
    os.makedirs(export_dir, exist_ok=True)
    export_file = os.path.join(export_dir, 'cleaned_logs.jsonl')
    
    mode = 'a' if export_append else 'w'
    
    messages_processed = 0
    attacks_found = 0
    idle_polls = 0
    
    try:
        with open(export_file, mode, encoding='utf-8') as f:
            while True:
                if max_messages is not None and messages_processed >= max_messages:
                    logger.info(f"Reached max_messages ({max_messages}). Stopping.")
                    break
                    
                batch = consumer.poll(timeout_ms=poll_timeout_ms)
                if not batch:
                    idle_polls += 1
                    if idle_polls >= idle_polls_limit:
                        logger.info(f"Reached idle_polls_limit ({idle_polls_limit}). Stopping.")
=======
def get_project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))


def run_cleaner(max_messages: int | None = None, idle_polls_limit: int | None = None):
    """
    Consomme le flux 'raw-logs' en BOUCLE, nettoie les événements,
    les republie sur 'cleaned-logs' et les exporte en JSONL.

    Correction majeure : la version précédente n'appelait `consumer.poll()`
    qu'UNE seule fois. Comme kafka-python plafonne à `max_poll_records=500`,
    l'export ne contenait jamais plus de 500 lignes. On boucle désormais
    jusqu'à atteindre `max_messages` ou jusqu'à ce que le flux soit vide.

    Args:
        max_messages: nombre maximum d'événements à traiter (défaut STREAM_MAX_RECORDS).
                      0 => illimité (on consomme tout ce qui est publié).
        idle_polls_limit: nombre de polls vides consécutifs avant d'arrêter.
    """
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
    cleaned_topic = os.getenv("KAFKA_CLEANED_TOPIC", "cleaned-logs")

    if max_messages is None:
        max_messages = int(os.getenv("STREAM_MAX_RECORDS", "0"))
    if max_messages <= 0:
        max_messages = None  # 0 => illimité : on consomme tout ce qui est publié
    if idle_polls_limit is None:
        idle_polls_limit = int(os.getenv("KAFKA_IDLE_POLLS_LIMIT", "5"))

    poll_timeout_ms = int(os.getenv("KAFKA_POLL_TIMEOUT_MS", "5000"))
    # "a" permet de cumuler les micro-batchs entre plusieurs runs Dagster
    write_mode = "a" if os.getenv("EXPORT_APPEND", "false").lower() == "true" else "w"
    # Sécurité : arrêt si le producteur est muet pendant > X fois le poll_timeout
    idle_timeout_s = int(os.getenv("KAFKA_IDLE_TIMEOUT_S", "120"))

    export_dir = os.path.join(get_project_root(), "data", "exports")
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, "cleaned_logs.jsonl")

    consumer, producer = get_kafka_clients(bootstrap_servers)

    target_str = "ILLIMITÉ" if max_messages is None else f"{max_messages}"
    logging.info(
        f"Nettoyage du flux : objectif {target_str} événements "
        f"(mode export='{write_mode}', poll_timeout={poll_timeout_ms}ms)"
    )

    messages_processed = 0
    attacks_seen = 0
    idle_polls = 0
    last_data_ts = time.time()
    start = time.time()

    try:
        with open(export_path, write_mode, encoding="utf-8") as export_file:
            while (max_messages is None or messages_processed < max_messages) and idle_polls < idle_polls_limit:
                raw_msgs = consumer.poll(timeout_ms=poll_timeout_ms)

                if not raw_msgs:
                    idle_polls += 1
                    # Sécurité temporelle : si le producteur est muet depuis longtemps,
                    # on arrête (le flux temps réel est réellement terminé).
                    if idle_timeout_s > 0 and (time.time() - last_data_ts) > idle_timeout_s:
                        logging.info(
                            f"Flux considéré terminé : aucune donnée depuis {idle_timeout_s}s."
                        )
>>>>>>> a9b26615667c811ba792659bef9dcc7c1fa578b2
                        break
                    time.sleep(idle_timeout_s)
                    continue
<<<<<<< HEAD
                
                idle_polls = 0
                
                for topic_partition, records in batch.items():
                    if max_messages is not None and messages_processed >= max_messages:
                        break
                        
                    for record in records:
                        if max_messages is not None and messages_processed >= max_messages:
                            break
                            
                        cleaned = clean_record(record.value)
                        attacks_found += cleaned['is_attack']
                        
                        producer.send('cleaned-logs', cleaned)
                        f.write(json.dumps(cleaned) + '\n')
                        
                        messages_processed += 1
                        
                f.flush()
                logger.info(f"Cleaned {messages_processed} records. Attacks: {attacks_found}")
                producer.flush()
=======

                idle_polls = 0  # on a reçu des données, on remet les compteurs à zéro
                last_data_ts = time.time()
                batch_lines = []

                for _tp, messages in raw_msgs.items():
                    for msg in messages:
                        if max_messages is not None and messages_processed >= max_messages:
                            break

                        cleaned_data = clean_record(msg.value)
                        producer.send(cleaned_topic, value=cleaned_data)
                        batch_lines.append(json.dumps(cleaned_data, default=str))
                        messages_processed += 1
                        attacks_seen += int(cleaned_data.get("is_attack", 0) or 0)

                    if max_messages is not None and messages_processed >= max_messages:
                        break

                # Écriture groupée : bien plus rapide que ligne par ligne
                if batch_lines:
                    export_file.write("\n".join(batch_lines) + "\n")
                    export_file.flush()

                elapsed = max(time.time() - start, 1e-6)
                logging.info(
                    f"Progression nettoyage : {messages_processed}/{target_str} "
                    f"({messages_processed/elapsed:.0f} msg/s, {attacks_seen} attaques)"
                )

        if messages_processed > 0:
            producer.flush()
            elapsed = max(time.time() - start, 1e-6)
            logging.info(
                f"Nettoyage terminé : {messages_processed} événements publiés sur "
                f"'{cleaned_topic}' en {elapsed:.1f}s ({attacks_seen} attaques détectées dans les labels)."
            )
            logging.info(f"Fichier exporté : {export_path}")
        else:
            logging.warning(
                "Aucun message brut à traiter. Vérifiez que le producer a bien publié "
                "sur 'raw-logs' et que le group_id n'a pas déjà consommé tout le topic."
            )
>>>>>>> a9b26615667c811ba792659bef9dcc7c1fa578b2
    finally:
        consumer.close()
        producer.close()
        logger.info("Cleaner closed.")

<<<<<<< HEAD
if __name__ == '__main__':
=======
    return messages_processed


if __name__ == "__main__":
>>>>>>> a9b26615667c811ba792659bef9dcc7c1fa578b2
    run_cleaner()
