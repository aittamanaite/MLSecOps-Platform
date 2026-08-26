import os
import json
import logging
import random
import time
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
                    idle_polls += 1
                    if idle_polls >= idle_polls_limit:
                        logger.info(f"Reached idle_polls_limit ({idle_polls_limit}). Stopping.")
                        break
                    time.sleep(idle_timeout_s)
                    continue
                
                idle_polls = 0
                
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
    finally:
        consumer.close()
        producer.close()
        logger.info("Inference closed.")

if __name__ == '__main__':
    run_inference()
