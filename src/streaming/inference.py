import os
import glob
import json
import logging
import time
import numpy as np
import pandas as pd
from kafka import KafkaProducer
from kafka.errors import KafkaError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
            )
        except KafkaError as e:
            logger.warning(f"Failed to connect to Kafka, attempt {attempt + 1}/5: {e}")
            time.sleep(2 ** attempt)
    raise RuntimeError("Could not connect to Kafka after multiple retries.")

def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _sanitize_chunk(chunk):
    chunk = chunk.replace([np.inf, -np.inf], np.nan)
    chunk = chunk.where(pd.notnull(chunk), None)
    return chunk

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
    iterators = _chunk_iterators(csv_files, batch_size)
    
    total_published = 0
    active_iterators = iterators[:]
    
    try:
        while active_iterators:
            if max_records is not None and total_published >= max_records:
                logger.info(f"Reached max_records ({max_records}). Stopping.")
                break
                
            for it in list(active_iterators):
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
                    logger.error(f"Error processing chunk: {e}")
                    active_iterators.remove(it)
                    
            producer.flush()
            time.sleep(0.01) # Small sleep to prevent tight loops
    finally:
        producer.close()
        logger.info("Producer closed.")

if __name__ == '__main__':
    run_producer()
