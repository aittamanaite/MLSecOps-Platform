import os
import json
import logging
import random
import time
<<<<<<< HEAD
=======

>>>>>>> 6c556c4 (Initial commit)
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

<<<<<<< HEAD
def get_kafka_clients(bootstrap_servers, timeout_s: int = 60):
    """Create consumer and producer with retries until broker is available."""
=======

def get_kafka_clients(bootstrap_servers, timeout_s: int = 60):
    """Create consumer and producer with retries until broker is available."""
    max_poll_records = int(os.getenv("KAFKA_MAX_POLL_RECORDS", "5000"))
>>>>>>> 6c556c4 (Initial commit)
    end_time = time.time() + timeout_s
    attempt = 0
    while True:
        try:
            attempt += 1
            logging.info(f"Creating Kafka consumer/producer (attempt={attempt}) to {bootstrap_servers}")
            consumer = KafkaConsumer(
                os.getenv("KAFKA_CLEANED_TOPIC", "cleaned-logs"),
                bootstrap_servers=[bootstrap_servers],
<<<<<<< HEAD
                group_id="inference-group",
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            producer = KafkaProducer(
                bootstrap_servers=[bootstrap_servers],
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
            )
            producer.bootstrap_connected()
            logging.info("Kafka consumer/producer bootstrap succeeded")
=======
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
                buffer_memory=128 * 1024 * 1024,
                retries=5,
            )
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
=======

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


>>>>>>> 6c556c4 (Initial commit)
def mock_predict_anomaly(record):
    """
    Simule un modèle de Machine Learning (ex: Isolation Forest, XGBoost).
    Si l'événement a is_attack = 1 dans les données, on lui donne une probabilité
    élevée d'être détecté. Sinon, probabilité très faible.
    """
    # Dans un vrai système, on utiliserait: model.predict_proba([features])
<<<<<<< HEAD
    
    is_attack = int(record.get("is_attack", 0))
=======
    is_attack = _extract_is_attack(record)
>>>>>>> 6c556c4 (Initial commit)
    if is_attack == 1:
        # Probabilité entre 85% et 99%
        confidence = random.uniform(0.85, 0.99)
    else:
        # Probabilité entre 1% et 10%
        confidence = random.uniform(0.01, 0.10)
<<<<<<< HEAD
        
    # Seuil d'anomalie
    return confidence > 0.80, confidence

=======

    # Seuil d'anomalie
    return confidence > 0.80, confidence


>>>>>>> 6c556c4 (Initial commit)
def get_project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))


<<<<<<< HEAD
def run_inference(max_messages=1000):
    """
    Consomme les messages nettoyés, réalise l'inférence, 
=======
def run_inference(max_messages: int | None = None, idle_polls_limit: int | None = None):
    """
    Consomme les messages nettoyés EN BOUCLE, réalise l'inférence,
>>>>>>> 6c556c4 (Initial commit)
    et pousse les anomalies vers 'app-errors' pour alertement.
    """
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
    alert_topic = os.getenv("KAFKA_ALERT_TOPIC", "app-errors")

<<<<<<< HEAD
    export_dir = os.path.join(get_project_root(), "data", "exports")
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, "app_errors.jsonl")
    
    consumer, producer = get_kafka_clients(bootstrap_servers)
    
    logging.info("Attente de données propres pour l'inférence ML...")
    
    messages_processed = 0
    anomalies_detected = 0
    
    # Consomme un lot (timeout de 2000ms)
    clean_msgs = consumer.poll(timeout_ms=2000)

    with open(export_path, "w", encoding="utf-8") as export_file:
        for tp, messages in clean_msgs.items():
            for msg in messages:
                if messages_processed >= max_messages:
                    break
                    
                record = msg.value
                
                # Inférence ML
                is_anomaly, confidence = mock_predict_anomaly(record)
                
                if is_anomaly:
                    # Ajoute les métadonnées ML au log avant de l'envoyer à l'alerte
                    record["ml_confidence_score"] = round(confidence, 4)
                    record["ml_model_version"] = "v1.2.0-isolation-forest"
                    producer.send(alert_topic, value=record)
                    export_file.write(json.dumps(record, default=str) + "\n")
                    anomalies_detected += 1
                
                messages_processed += 1
                
    if messages_processed > 0:
        producer.flush()
        logging.info(f"Inférence terminée : {messages_processed} événements analysés. {anomalies_detected} anomalies envoyées vers {alert_topic}.")
        logging.info(f"Fichier exporté : {export_path}")
    else:
        logging.info("Aucune donnée propre à analyser.")
        logging.info(f"Fichier d'export créé (vide si aucune anomalie) : {export_path}")
        
    consumer.close()
    producer.close()
    
    return anomalies_detected

=======
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
                    idle_polls += 1
                    if idle_timeout_s > 0 and (time.time() - last_data_ts) > idle_timeout_s:
                        logging.info(
                            f"Flux considéré terminé : aucune donnée depuis {idle_timeout_s}s."
                        )
                        break
                    logging.info(
                        f"Aucun message propre reçu (poll vide {idle_polls}/{idle_polls_limit}) "
                        f"- {messages_processed} analysés jusqu'ici."
                    )
                    continue

                idle_polls = 0
                last_data_ts = time.time()
                batch_lines = []

                for _tp, messages in clean_msgs.items():
                    for msg in messages:
                        if messages_processed >= max_messages:
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

                    if messages_processed >= max_messages:
                        break

                if batch_lines:
                    export_file.write("\n".join(batch_lines) + "\n")
                    export_file.flush()

                elapsed = max(time.time() - start, 1e-6)
                logging.info(
                    f"Progression inférence : {messages_processed}/{max_messages} analysés, "
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
    finally:
        consumer.close()
        producer.close()

    return anomalies_detected


>>>>>>> 6c556c4 (Initial commit)
if __name__ == "__main__":
    run_inference()
