import os
import json
import logging
<<<<<<< HEAD
import time
=======
import math
import time

>>>>>>> 6c556c4 (Initial commit)
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

<<<<<<< HEAD
def get_kafka_clients(bootstrap_servers, timeout_s: int = 60):
    """Create consumer and producer with retries until broker is available."""
=======
# Valeurs textuelles invalides rencontrées dans CIC-IDS2017
INVALID_STRINGS = {"", "infinity", "-infinity", "inf", "-inf", "nan", "null", "none", "na", "n/a"}


def get_kafka_clients(bootstrap_servers, timeout_s: int = 60):
    """Create consumer and producer with retries until broker is available.

    IMPORTANT : `max_poll_records` vaut 500 par défaut dans kafka-python.
    C'est la raison pour laquelle un seul appel à consumer.poll() ne pouvait
    jamais retourner plus de 500 messages. On l'augmente ici et on boucle.
    """
    max_poll_records = int(os.getenv("KAFKA_MAX_POLL_RECORDS", "5000"))
>>>>>>> 6c556c4 (Initial commit)
    end_time = time.time() + timeout_s
    attempt = 0
    while True:
        try:
            attempt += 1
            logging.info(f"Creating Kafka consumer/producer (attempt={attempt}) to {bootstrap_servers}")
            consumer = KafkaConsumer(
                os.getenv("KAFKA_RAW_TOPIC", "raw-logs"),
                bootstrap_servers=[bootstrap_servers],
<<<<<<< HEAD
                group_id="cleaner-group",
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            producer = KafkaProducer(
                bootstrap_servers=[bootstrap_servers],
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
            )
            # quick check
            producer.bootstrap_connected()
            logging.info("Kafka consumer/producer bootstrap succeeded")
=======
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
                buffer_memory=128 * 1024 * 1024,
                retries=5,
            )
            # quick check
            producer.bootstrap_connected()
            logging.info(f"Kafka consumer/producer bootstrap succeeded (max_poll_records={max_poll_records})")
>>>>>>> 6c556c4 (Initial commit)
            return consumer, producer
        except KafkaError as e:
            remaining = end_time - time.time()
            logging.warning(f"Kafka client attempt {attempt} failed: {e}; retrying, {max(0,int(remaining))}s left")
            if remaining <= 0:
                logging.error("Kafka client bootstrap timed out")
                raise
            sleep = min(5 * (2 ** (attempt - 1)), remaining, 10)
            time.sleep(sleep)

<<<<<<< HEAD
def clean_record(record):
    """
    Simule une fonction de nettoyage : 
    - Formate les colonnes
    - Supprime ou remplace les valeurs invalides
    """
    cleaned = {}
    for k, v in record.items():
        # Standardisation des noms de colonnes (minuscules, sans espaces)
        new_key = str(k).strip().lower().replace(" ", "_")
        
        # Filtrage basique (ex: on force le port en entier, on remplace les None par 0)
        if v is None:
            v = 0
        cleaned[new_key] = v
        
    return cleaned

=======

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
        # tente une conversion numérique (les CSV donnent souvent des str)
        try:
            num = float(stripped)
            if math.isnan(num) or math.isinf(num):
                return 0
            return int(num) if num.is_integer() else num
        except ValueError:
            return stripped
    return value


def _normalize_label(label: str) -> str:
    """
    Uniformise le label d'attaque : les tirets exotiques (– — ‐ et le caractère
    de remplacement U+FFFD dû à l'encodage latin-1) deviennent un '-' simple,
    et les espaces multiples sont réduits. Sans cela, on obtient plusieurs
    variantes du même label ("Web Attack – Brute Force" vs "Web Attack ? Brute Force").
    """
    text = str(label)
    # Caractères à transformer en tiret simple :
    #  – — ‐ ‑ ‒  (tirets typographiques)
    #  U+FFFD      (caractère de remplacement : le fichier CSV contient déjà
    #               "Web Attack U+FFFD Brute Force" à la place du tiret)
    #  \x96        (0x96 lu en latin-1)
    for ch in ("\u2013", "\u2014", "\u2010", "\u2011", "\u2012", "\ufffd", "\x96"):
        text = text.replace(ch, "-")
    text = " ".join(text.split())
    # supprime un tiret isolé en trop : "Web Attack - Brute Force" reste lisible
    return text.strip()


def clean_record(record):
    """
    Nettoyage d'un événement réseau :
    - normalise les noms de colonnes (minuscules, underscores, sans caractères parasites)
    - convertit les valeurs invalides (None, Infinity, NaN) en 0
    - dérive `is_attack` (0/1) à partir de la colonne `label`
    """
    cleaned = {}
    for k, v in record.items():
        # Standardisation des noms de colonnes (minuscules, sans espaces ni '/')
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
    # Sans cela, inference.py lit `is_attack` qui n'existe pas => 0 anomalie détectée.
    label = _normalize_label(cleaned.get("label", ""))
    if label:
        cleaned["label"] = label
        cleaned["is_attack"] = 0 if label.upper() == "BENIGN" else 1
    else:
        cleaned.setdefault("is_attack", 0)

    cleaned["ingested_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    return cleaned


>>>>>>> 6c556c4 (Initial commit)
def get_project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))


<<<<<<< HEAD
def run_cleaner(max_messages=1000):
    """
    Consomme un micro-batch de messages depuis 'raw-logs', les nettoie, 
    et les republie dans 'cleaned-logs'.
    """
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
    cleaned_topic = os.getenv("KAFKA_CLEANED_TOPIC", "cleaned-logs")
    
=======
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
    # (évite de tourner indéfiniment si le flux s'arrête réellement).
    idle_timeout_s = int(os.getenv("KAFKA_IDLE_TIMEOUT_S", "120"))

>>>>>>> 6c556c4 (Initial commit)
    export_dir = os.path.join(get_project_root(), "data", "exports")
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, "cleaned_logs.jsonl")

    consumer, producer = get_kafka_clients(bootstrap_servers)
<<<<<<< HEAD
    
    logging.info("Attente de messages bruts à nettoyer...")
    
    messages_processed = 0
    # Consomme un lot (timeout de 2000ms si plus de messages)
    raw_msgs = consumer.poll(timeout_ms=2000)

    with open(export_path, "w", encoding="utf-8") as export_file:
        for tp, messages in raw_msgs.items():
            for msg in messages:
                if messages_processed >= max_messages:
                    break
                    
                raw_data = msg.value
                cleaned_data = clean_record(raw_data)
                
                producer.send(cleaned_topic, value=cleaned_data)
                export_file.write(json.dumps(cleaned_data, default=str) + "\n")
                messages_processed += 1
                
    if messages_processed > 0:
        producer.flush()
        logging.info(f"Nettoyage terminé : {messages_processed} événements publiés sur {cleaned_topic}.")
        logging.info(f"Fichier exporté : {export_path}")
    else:
        logging.info("Aucun message brut à traiter.")
        logging.info(f"Fichier d'export créé (vide si aucun message) : {export_path}")
        
    consumer.close()
    producer.close()
    
    return messages_processed

=======

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
                            f"Flux considered terminé : aucune donnée depuis {idle_timeout_s}s."
                        )
                        break
                    logging.info(
                        f"Aucun message reçu (poll vide {idle_polls}/{idle_polls_limit}) "
                        f"- {messages_processed} traités jusqu'ici."
                    )
                    continue

                idle_polls = 0  # on a reçu des données, on remet les compteurs à zéro
                last_data_ts = time.time()
                batch_lines = []

                for _tp, messages in raw_msgs.items():
                    for msg in messages:
                        if messages_processed >= max_messages:
                            break

                        cleaned_data = clean_record(msg.value)
                        producer.send(cleaned_topic, value=cleaned_data)
                        batch_lines.append(json.dumps(cleaned_data, default=str))
                        messages_processed += 1
                        attacks_seen += int(cleaned_data.get("is_attack", 0) or 0)

                    if messages_processed >= max_messages:
                        break

                # Écriture groupée : bien plus rapide que ligne par ligne
                if batch_lines:
                    export_file.write("\n".join(batch_lines) + "\n")
                    export_file.flush()

                elapsed = max(time.time() - start, 1e-6)
                logging.info(
                    f"Progression nettoyage : {messages_processed}/{max_messages} "
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
    finally:
        consumer.close()
        producer.close()

    return messages_processed


>>>>>>> 6c556c4 (Initial commit)
if __name__ == "__main__":
    run_cleaner()
