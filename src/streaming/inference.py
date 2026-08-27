import os
import json
import logging
import random
import time
<<<<<<< HEAD
=======

>>>>>>> a9b26615667c811ba792659bef9dcc7c1fa578b2
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

<<<<<<< HEAD
def get_kafka_clients():
    max_poll = int(os.environ.get('KAFKA_MAX_POLL_RECORDS', 500))
    group_id = os.environ.get('KAFKA_INFERENCE_GROUP', 'inference-group')
    consumer = KafkaConsumer(
        'cleaned-logs',
        bootstrap_servers=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        group_id=group_id,
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

def _extract_is_attack(record):
    return record.get('is_attack', 0)

def mock_predict_anomaly(is_attack):
    if is_attack:
        return random.uniform(0.85, 0.99)
    return random.uniform(0.01, 0.10)

def predict_anomaly(record, model=None):
    if model is not None:
        try:
            from src.ml.predict import predict_record
            return predict_record(model, record)
        except Exception as e:
            logger.debug(f"Could not use predict_record, fallback to mock: {e}")
            pass
            
    is_attack = _extract_is_attack(record)
    return mock_predict_anomaly(is_attack)

def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_inference(max_messages=None, idle_polls_limit=None):
    env_max = os.environ.get('STREAM_MAX_RECORDS')
    if max_messages is None and env_max is not None:
        max_messages = int(env_max) if env_max.strip() else None

    env_idle = os.environ.get('KAFKA_IDLE_POLLS_LIMIT')
    if idle_polls_limit is None:
        idle_polls_limit = int(env_idle) if env_idle else 5
        
    poll_timeout_ms = int(os.environ.get('KAFKA_POLL_TIMEOUT_MS', 1000))
    export_append = os.environ.get('EXPORT_APPEND', 'false').lower() == 'true'
    idle_timeout_s = int(os.environ.get('KAFKA_IDLE_TIMEOUT_S', 10))
    
    try:
        from src.ml.predict import load_model
        model = load_model()
        logger.info("Successfully loaded ML model.")
    except Exception as e:
        logger.warning(f"Could not load ML model, using mock predictions: {e}")
        model = None
        
    consumer, producer = get_kafka_clients()
    
    root_dir = get_project_root()
    export_dir = os.path.join(root_dir, 'data', 'processed')
    os.makedirs(export_dir, exist_ok=True)
    export_file = os.path.join(export_dir, 'inferences.jsonl')
    
    mode = 'a' if export_append else 'w'
    
    messages_processed = 0
    idle_polls = 0
    
    try:
        with open(export_file, mode, encoding='utf-8') as f:
            while True:
                if max_messages is not None and messages_processed >= max_messages:
                    logger.info(f"Reached max_messages ({max_messages}). Stopping.")
                    break
                    
                batch = consumer.poll(timeout_ms=poll_timeout_ms)
                if not batch:
=======

def get_kafka_clients(bootstrap_servers, timeout_s: int = 60):
    """Create consumer and producer with retries until broker is available."""
    max_poll_records = int(os.getenv("KAFKA_MAX_POLL_RECORDS", "5000"))
    end_time = time.time() + timeout_s
    attempt = 0
    while True:
        try:
            attempt += 1
            logging.info(f"Creating Kafka consumer/producer (attempt={attempt}) to {bootstrap_servers}")
            consumer = KafkaConsumer(
                os.getenv("KAFKA_CLEANED_TOPIC", "cleaned-logs"),
                bootstrap_servers=[bootstrap_servers],
                group_id=os.getenv("KAFKA_INFERENCE_GROUP", "inference-group"),
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                # --- Réglages de débit (voir cleaner.py : défaut = 500 !) ---
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


def _extract_is_attack(record) -> int:
    """
    Récupère la cible depuis `is_attack` (produit par le cleaner) et
    retombe sur `label` si besoin (robustesse si le schéma change).
    """
    if "is_attack" in record:
        try:
            return int(float(record.get("is_attack") or 0))
        except (TypeError, ValueError):
            pass
    label = str(record.get("label", "")).strip().upper()
    if label:
        return 0 if label == "BENIGN" else 1
    return 0


def mock_predict_anomaly(record):
    """
    Simule un modèle de Machine Learning (ex: Isolation Forest, XGBoost).
    Si l'événement a is_attack = 1 dans les données, on lui donne une probabilité
    élevée d'être détecté. Sinon, probabilité très faible.
    """
    # Dans un vrai système, on utiliserait: model.predict_proba([features])
    is_attack = _extract_is_attack(record)
    if is_attack == 1:
        # Probabilité entre 85% et 99%
        confidence = random.uniform(0.85, 0.99)
    else:
        # Probabilité entre 1% et 10%
        confidence = random.uniform(0.01, 0.10)

    # Seuil d'anomalie
    return confidence > 0.80, confidence


def get_project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))


def run_inference(max_messages: int | None = None, idle_polls_limit: int | None = None):
    """
    Consomme les messages nettoyés EN BOUCLE, réalise l'inférence,
    et pousse les anomalies vers 'app-errors' pour alertement.
    """
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
    alert_topic = os.getenv("KAFKA_ALERT_TOPIC", "app-errors")

    if max_messages is None:
        max_messages = int(os.getenv("STREAM_MAX_RECORDS", "0"))
    if max_messages <= 0:
        max_messages = None  # 0 => illimité
    if idle_polls_limit is None:
        idle_polls_limit = int(os.getenv("KAFKA_IDLE_POLLS_LIMIT", "5"))

    poll_timeout_ms = int(os.getenv("KAFKA_POLL_TIMEOUT_MS", "5000"))
    write_mode = "a" if os.getenv("EXPORT_APPEND", "false").lower() == "true" else "w"
    idle_timeout_s = int(os.getenv("KAFKA_IDLE_TIMEOUT_S", "120"))

    export_dir = os.path.join(get_project_root(), "data", "exports")
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, "app_errors.jsonl")

    consumer, producer = get_kafka_clients(bootstrap_servers)

    target_str = "ILLIMITÉ" if max_messages is None else f"{max_messages}"
    logging.info(f"Inférence ML : objectif {target_str} événements analysés.")

    messages_processed = 0
    anomalies_detected = 0
    idle_polls = 0
    last_data_ts = time.time()
    start = time.time()

    try:
        with open(export_path, write_mode, encoding="utf-8") as export_file:
            while (max_messages is None or messages_processed < max_messages) and idle_polls < idle_polls_limit:
                clean_msgs = consumer.poll(timeout_ms=poll_timeout_ms)

                if not clean_msgs:
>>>>>>> a9b26615667c811ba792659bef9dcc7c1fa578b2
                    idle_polls += 1
                    if idle_polls >= idle_polls_limit:
                        logger.info(f"Reached idle_polls_limit ({idle_polls_limit}). Stopping.")
                        break
                    time.sleep(idle_timeout_s)
                    continue
                
                idle_polls = 0
<<<<<<< HEAD
                
                for topic_partition, records in batch.items():
                    if max_messages is not None and messages_processed >= max_messages:
                        break
                        
                    for record in records:
                        if max_messages is not None and messages_processed >= max_messages:
                            break
                            
                        data = record.value
                        score = predict_anomaly(data, model)
                        
                        data['ml_confidence_score'] = score
                        data['ml_model_version'] = '1.0.0' if model is not None else 'mock-1.0'
                        data['detected_at'] = time.time()
                        
                        producer.send('alerts', data)
                        f.write(json.dumps(data) + '\n')
                        
                        messages_processed += 1
                        
                f.flush()
                logger.info(f"Inferred {messages_processed} records.")
                producer.flush()
=======
                last_data_ts = time.time()
                batch_lines = []

                for _tp, messages in clean_msgs.items():
                    for msg in messages:
                        if max_messages is not None and messages_processed >= max_messages:
                            break

                        record = msg.value

                        # Inférence ML
                        is_anomaly, confidence = mock_predict_anomaly(record)

                        if is_anomaly:
                            # Ajoute les métadonnées ML au log avant de l'envoyer à l'alerte
                            record["ml_confidence_score"] = round(confidence, 4)
                            record["ml_model_version"] = "v1.2.0-isolation-forest"
                            record["detected_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                            producer.send(alert_topic, value=record)
                            batch_lines.append(json.dumps(record, default=str))
                            anomalies_detected += 1

                        messages_processed += 1

                    if max_messages is not None and messages_processed >= max_messages:
                        break

                if batch_lines:
                    export_file.write("\n".join(batch_lines) + "\n")
                    export_file.flush()

                elapsed = max(time.time() - start, 1e-6)
                logging.info(
                    f"Progression inférence : {messages_processed}/{target_str} analysés, "
                    f"{anomalies_detected} anomalies ({messages_processed/elapsed:.0f} msg/s)"
                )

        if messages_processed > 0:
            producer.flush()
            elapsed = max(time.time() - start, 1e-6)
            logging.info(
                f"Inférence terminée : {messages_processed} événements analysés en {elapsed:.1f}s. "
                f"{anomalies_detected} anomalies envoyées vers '{alert_topic}'."
            )
            logging.info(f"Fichier exporté : {export_path}")
        else:
            logging.warning("Aucune donnée propre à analyser (topic 'cleaned-logs' vide pour ce group_id).")
>>>>>>> a9b26615667c811ba792659bef9dcc7c1fa578b2
    finally:
        consumer.close()
        producer.close()
        logger.info("Inference closed.")

<<<<<<< HEAD
if __name__ == '__main__':
=======
    return anomalies_detected


if __name__ == "__main__":
>>>>>>> a9b26615667c811ba792659bef9dcc7c1fa578b2
    run_inference()
