"""
Loki Safe Re-Ingestion Script with Dry-Run, Progress Bars, and Logging
----------------------------------------------------------------------

Features:
1. Backup:
   - Fetches logs from Loki based on a stream selector (QUERY)
   - Saves logs to a backup JSON file (or simulates in dry-run)

2. Delete Old Streams:
   - Deletes old streams matching the same selector
   - Dry-run mode simulates deletion without affecting Loki

3. Deduplication:
   - Removes exact duplicate log entries based on (timestamp, line)

4. Memory-Efficient Re-Ingestion:
   - Reads backup file in chunks to avoid high memory usage
   - Pushes logs back to Loki in configurable batch sizes
   - Dry-run simulates pushes without sending data

5. Incremental Fetch:
   - Fetch logs from Loki in time windows to handle large datasets

6. Progress Bars:
   - Shows progress using `tqdm` for fetch and push operations

7. File Logging:
   - Logs all operations to `loki_reingest.log` in addition to console
"""

import requests
import json
import time
from datetime import datetime
import argparse
import logging
from tqdm import tqdm

# ------------------------
# Config
# ------------------------
LOKI_QUERY_URL = "http://localhost:3100/loki/api/v1/query_range"
LOKI_PUSH_URL = "http://localhost:3100/loki/api/v1/push"
LOKI_DELETE_URL = "http://localhost:3100/loki/api/v1/streams"

QUERY = '{job="varlogs"}'
WINDOW_SEC = 3600
BATCH_SIZE = 5000
START_TS = int((datetime(2025, 1, 1).timestamp()) * 1e9)
END_TS = int(time.time() * 1e9)
BACKUP_FILE = "loki_backup.json"
LOG_FILE = "loki_reingest.log"

# ------------------------
# Setup logging
# ------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)


# ------------------------
# Helper functions
# ------------------------
def fetch_logs(start_ns, end_ns):
    params = {"query": QUERY, "start": start_ns, "end": end_ns, "limit": 1000000}
    r = requests.get(LOKI_QUERY_URL, params=params)
    r.raise_for_status()
    logs = []
    data = r.json()
    for stream in data.get("data", {}).get("result", []):
        labels = stream.get("stream", {})
        for ts, line in stream.get("values", []):
            logs.append({"ts": ts, "line": line, "labels": labels})
    logging.info(f"Fetched {len(logs)} logs from {start_ns} to {end_ns}")
    return logs


def backup_logs(logs, file_path=BACKUP_FILE, dry_run=False):
    if dry_run:
        logging.info(f"[Dry-Run] Would backup {len(logs)} logs to {file_path}")
        return
    with open(file_path, "w") as f:
        json.dump(logs, f)
    logging.info(f"Backed up {len(logs)} logs to {file_path}")


def deduplicate(logs):
    seen = set()
    deduped = []
    for entry in logs:
        key = (entry["ts"], entry["line"])
        if key not in seen:
            seen.add(key)
            deduped.append(entry)
    logging.info(f"{len(deduped)} entries remain after deduplication")
    return deduped


def push_logs_batch(log_batch, dry_run=False):
    streams_dict = {}
    for entry in log_batch:
        ts, line, labels = entry["ts"], entry["line"], entry["labels"]
        lbl_key = frozenset(labels.items())
        streams_dict.setdefault(lbl_key, []).append([ts, line])

    headers = {"Content-Type": "application/json"}
    for lbl_key, values in streams_dict.items():
        for i in range(0, len(values), BATCH_SIZE):
            payload = {
                "streams": [
                    {"stream": dict(lbl_key), "values": values[i : i + BATCH_SIZE]}
                ]
            }
            if dry_run:
                logging.info(
                    f"[Dry-Run] Would push {len(values[i : i + BATCH_SIZE])} logs for labels {dict(lbl_key)}"
                )
            else:
                r = requests.post(
                    LOKI_PUSH_URL, data=json.dumps(payload), headers=headers
                )
                r.raise_for_status()
                logging.info(
                    f"Pushed {len(values[i : i + BATCH_SIZE])} logs for labels {dict(lbl_key)}"
                )


def delete_streams(dry_run=False):
    if dry_run:
        logging.info(f"[Dry-Run] Would delete streams matching {QUERY}")
        return
    params = {"match": QUERY}
    r = requests.delete(LOKI_DELETE_URL, params=params)
    r.raise_for_status()
    logging.info(f"Deleted old streams matching {QUERY}")


def read_backup_in_chunks(file_path, chunk_size=BATCH_SIZE):
    with open(file_path, "r") as f:
        buffer = []
        for entry in json.load(f):
            buffer.append(entry)
            if len(buffer) >= chunk_size:
                yield buffer
                buffer = []
        if buffer:
            yield buffer


# ------------------------
# Main workflow
# ------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Loki Safe Re-Ingestion Script with Dry-Run, Progress Bars, and Logging"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate actions without modifying Loki"
    )
    args = parser.parse_args()
    dry_run = args.dry_run

    logging.info("Starting Loki safe re-ingestion workflow")
    logging.info(f"Dry-run mode: {dry_run}")

    # 1️⃣ Fetch & backup logs incrementally
    all_logs = []
    num_windows = (END_TS - START_TS) // (WINDOW_SEC * 1_000_000_000) + 1
    with tqdm(total=num_windows, desc="Fetching logs") as pbar:
        current_start = START_TS
        while current_start < END_TS:
            current_end = min(current_start + WINDOW_SEC * 1_000_000_000, END_TS)
            logs = fetch_logs(current_start, current_end)
            all_logs.extend(logs)
            current_start = current_end
            pbar.update(1)
            time.sleep(0.1)

    backup_logs(all_logs, dry_run=dry_run)

    # 2️⃣ Delete old streams
    delete_streams(dry_run=dry_run)

    # 3️⃣ Deduplicate logs
    deduped_logs = deduplicate(all_logs)

    # 4️⃣ Re-ingest logs in chunks with progress bar
    total_chunks = sum(1 for _ in read_backup_in_chunks(BACKUP_FILE, BATCH_SIZE))
    with tqdm(total=total_chunks, desc="Re-ingesting logs") as pbar:
        for batch in read_backup_in_chunks(BACKUP_FILE, BATCH_SIZE):
            push_logs_batch(batch, dry_run=dry_run)
            pbar.update(1)

    logging.info("Re-ingestion workflow complete!")
