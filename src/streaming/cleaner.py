import os
import json
import logging
import math
import time
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

INVALID_STRINGS = {'', 'none', 'null', 'nan', 'inf', '-inf'}

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

def clean_record(record):
    cleaned = {}
    for k, v in record.items():
        new_k = k.strip().lower().replace(' ', '_').replace('/', '_').replace('-', '_').replace('.', '_')
        cleaned[new_k] = _coerce_value(v)
    
    label = cleaned.get('label', 'benign')
    label = _normalize_label(label)
    cleaned['label'] = label
    cleaned['is_attack'] = 1 if label != 'benign' else 0
    cleaned['ingested_at'] = time.time()
    return cleaned

def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
                            
                        cleaned = clean_record(record.value)
                        attacks_found += cleaned['is_attack']
                        
                        producer.send('cleaned-logs', cleaned)
                        f.write(json.dumps(cleaned) + '\n')
                        
                        messages_processed += 1
                        
                f.flush()
                logger.info(f"Cleaned {messages_processed} records. Attacks: {attacks_found}")
                producer.flush()
    finally:
        consumer.close()
        producer.close()
        logger.info("Cleaner closed.")

if __name__ == '__main__':
    run_cleaner()
