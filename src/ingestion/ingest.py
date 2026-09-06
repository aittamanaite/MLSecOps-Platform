import os
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def ingest_data():
    logging.info("Starting cybersecurity log ingestion...")

    # Target directory for raw datasets
    raw_data_dir = os.path.join("data", "raw")
    os.makedirs(raw_data_dir, exist_ok=True)

    logging.info(f"Raw data directory ready at: {raw_data_dir}")
    # TODO: Data Science team will add dataset fetch logic here
    return True


if __name__ == "__main__":
    ingest_data()
