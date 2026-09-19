import os
import sys
import socket
import time
import gdown
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

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

# CICIDS2017 CSVs are tens to hundreds of MB. A "successful" download under
# this size is almost certainly a Google Drive HTML error/quota page, not
# real data, so we validate against it instead of the old 1KB threshold.
MIN_VALID_SIZE_BYTES = 1_000_000

DNS_CHECK_HOST = "drive.google.com"
DNS_CHECK_TIMEOUT_S = 5
MAX_ATTEMPTS_PER_FILE = 3
RETRY_BACKOFF_S = 5


def check_connectivity(host: str = DNS_CHECK_HOST, timeout: float = DNS_CHECK_TIMEOUT_S) -> bool:
    """Fail fast with a clear diagnosis instead of letting every file
    individually burn ~15s on DNS retries before finally erroring out."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.gethostbyname(host)
        return True
    except OSError as e:
        log.error(f"Cannot resolve '{host}': {e}")
        return False


def looks_like_html(path: str, sniff_bytes: int = 512) -> bool:
    """Google Drive sometimes serves a small HTML page (quota exceeded,
    virus-scan warning, permission error) with HTTP 200 instead of the
    actual file. Catch that instead of writing it to disk as if it were
    valid CSV data."""
    try:
        with open(path, "rb") as f:
            head = f.read(sniff_bytes).lstrip().lower()
        return head.startswith(b"<!doctype") or head.startswith(b"<html")
    except OSError:
        return False


def is_valid_download(path: str) -> bool:
    if not os.path.exists(path):
        return False
    if os.path.getsize(path) < MIN_VALID_SIZE_BYTES:
        return False
    if looks_like_html(path):
        return False
    return True


def download_one(filename: str, file_id: str, out_path: str) -> bool:
    url = f"https://drive.google.com/uc?id={file_id}"
    for attempt in range(1, MAX_ATTEMPTS_PER_FILE + 1):
        try:
            log.info(f"Downloading {filename} (attempt {attempt}/{MAX_ATTEMPTS_PER_FILE})...")
            gdown.download(url, out_path, quiet=False)
        except Exception as e:
            log.warning(f"Download error for {filename}: {e}")

        if is_valid_download(out_path):
            return True

        # Clean up partial/bad files (e.g. HTML error pages) before retrying
        if os.path.exists(out_path):
            reason = "looked like an HTML error page" if looks_like_html(out_path) else "was too small"
            log.warning(f"Downloaded file for {filename} {reason}; discarding.")
            os.remove(out_path)

        if attempt < MAX_ATTEMPTS_PER_FILE:
            time.sleep(RETRY_BACKOFF_S)

    return False


def main():
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/raw/'))
    os.makedirs(output_dir, exist_ok=True)
    log.info(f"Target directory: {output_dir}")

    if not check_connectivity():
        log.error(
            "No network route to Google Drive — this is a DNS/connectivity "
            "problem in the current environment, not a bug in this script. "
            "Common causes: (1) running inside a container/CI sandbox with "
            "an outbound-traffic allowlist that excludes drive.google.com, "
            "(2) missing/broken DNS config on the host (check /etc/resolv.conf "
            "or try `docker run --dns 8.8.8.8 ...`), (3) no internet access "
            "at all on this machine. Fix connectivity first, or download the "
            "CICIDS2017 CSVs manually from https://www.unb.ca/cic/datasets/ids-2017.html "
            "and place them in "
            f"{output_dir}"
        )
        sys.exit(1)

    downloaded_count = 0
    failed_files = []

    for filename, file_id in DATASET_FILES.items():
        out_path = os.path.join(output_dir, filename)
        if is_valid_download(out_path):
            log.info(f"File {filename} already exists, skipping.")
            downloaded_count += 1
            continue

        if download_one(filename, file_id, out_path):
            downloaded_count += 1
        else:
            log.warning(f"Giving up on {filename} after {MAX_ATTEMPTS_PER_FILE} attempts.")
            failed_files.append(filename)

    if downloaded_count == 0:
        log.info("No files downloaded directly. Attempting clean folder download fallback...")
        try:
            gdown.download_folder(id=CLEAN_FOLDER_ID, output=output_dir, quiet=False, use_cookies=False)
        except Exception as e:
            log.error(f"Fallback folder download error: {e}")

    log.info(f"Download complete. Valid CSV files present: {downloaded_count}/{len(DATASET_FILES)}")
    if failed_files:
        log.warning(f"Files that could not be downloaded: {', '.join(failed_files)}")

    if downloaded_count == 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
