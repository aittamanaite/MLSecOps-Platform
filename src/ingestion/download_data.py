import os
import gdown
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Exact IDs for the CICIDS2017 CSV files
DATASET_FILES = {
    "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv": "1UOau3RCtAe2Y9qivtteI_5Y05TA_JTXI",
    "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv": "1KP0fXPpLfiaNTh6WDgWOSadGyRilMkrp",
    "Friday-WorkingHours-Morning.pcap_ISCX.csv": "1IV8K7V4ulJN-7pEJbaJfBG1ByLLwvGNg",
    "Monday-WorkingHours.pcap_ISCX.csv": "17baplnD90s9BlyqShg1utwUZhBc7cvUE",
    "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv": "1XSu3_PGUoBSsiY4tSg5g5JHtkJSVEPsA",
    "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv": "1vZu0qrpn69CZdpex6XLqfPkiTwB4fMt6",
    "Tuesday-WorkingHours.pcap_ISCX.csv": "1Q96kL_T2bvhgDkMEr9557ApqqEOlgMzu",
    "Wednesday-workingHours.pcap_ISCX.csv": "1c0cX8dBp_pNDTjrFyOzb4XBHjsJX_KAR",
}

CLEAN_FOLDER_ID = "11Pv-TauVhMHxH5Th3SaKvvU9HLuYL1rC"

def main():
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/raw/'))
    os.makedirs(output_dir, exist_ok=True)
    
    logging.info(f"Target directory: {output_dir}")
    downloaded_count = 0

    for filename, file_id in DATASET_FILES.items():
        out_path = os.path.join(output_dir, filename)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
            logging.info(f"File {filename} already exists, skipping.")
            downloaded_count += 1
            continue
            
        logging.info(f"Downloading {filename}...")
        try:
            url = f"https://drive.google.com/uc?id={file_id}"
            gdown.download(url, out_path, quiet=False)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
                downloaded_count += 1
        except Exception as e:
            logging.warning(f"Direct download failed for {filename}: {e}")

    if downloaded_count == 0:
        logging.info("Attempting clean folder download fallback...")
        try:
            gdown.download_folder(id=CLEAN_FOLDER_ID, output=output_dir, quiet=False, use_cookies=False)
        except Exception as e:
            logging.error(f"Fallback folder download error: {e}")

    logging.info(f"Download complete. Total CSV files present: {downloaded_count}")

if __name__ == '__main__':
    main()
