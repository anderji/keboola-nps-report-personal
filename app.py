import os
import csv
import io
import logging
import requests
from flask import Flask, jsonify, send_from_directory

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

KBC_TOKEN = os.environ.get("KBC_TOKEN", "") or os.environ.get("STORAGE_TOKEN", "")
KBC_URL   = os.environ.get("KBC_URL", "https://connection.europe-west3.gcp.keboola.com")
TABLE_ID  = "in.c-dataaps-test.nps_text_feedback"

logger.info(f"KBC_URL: {KBC_URL}")
logger.info(f"KBC_TOKEN present: {'Yes' if KBC_TOKEN else 'No'}")

_data_cache = []

def load_data():
    global _data_cache
    if not KBC_TOKEN:
        logger.error("No token available")
        return False

    headers = {"X-StorageApi-Token": KBC_TOKEN}
    all_rows = []
    offset = 0
    limit = 1000

    while True:
        url = f"{KBC_URL.rstrip('/')}/v2/storage/tables/{TABLE_ID}/data-preview"
        params = {"format": "json", "limit": limit, "offset": offset}
        try:
            logger.info(f"Fetching rows {offset}–{offset+limit}...")
            resp = requests.get(url, headers=headers, params=params, timeout=60)
            logger.info(f"Status: {resp.status_code}")
            if resp.status_code != 200:
                logger.error(f"Failed: {resp.text[:300]}")
                break
            payload = resp.json()
            columns = payload.get("columns", [])
            rows    = payload.get("rows", [])
            if not rows:
                logger.info("No more rows, done.")
                break
            for row in rows:
                all_rows.append({col: (row[i] if i < len(row) else None) for i, col in enumerate(columns)})
            logger.info(f"Got {len(rows)} rows, total so far: {len(all_rows)}")
            if len(rows) < limit:
                break
            offset += limit
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            break

    _data_cache = all_rows
    logger.info(f"Total loaded: {len(_data_cache)} rows")
    return len(_data_cache) > 0

load_data()

@app.route("/", methods=["GET", "POST"])
def index():
    return send_from_directory(".", "index.html")

@app.route("/api/data", methods=["GET"])
def get_data():
    return jsonify(_data_cache)

@app.route("/api/debug", methods=["GET"])
def debug():
    env_info = {k: ("***" if "TOKEN" in k.upper() else v)
                for k, v in os.environ.items()
                if any(x in k.upper() for x in ["TOKEN","KBC","STORAGE","WORKSPACE","BRANCH"])}
    return jsonify({
        "row_count":     len(_data_cache),
        "token_present": bool(KBC_TOKEN),
        "kbc_url":       KBC_URL,
        "env_vars":      env_info,
        "sample_row":    _data_cache[0] if _data_cache else None,
    })

@app.route("/api/reload", methods=["POST"])
def reload_data():
    success = load_data()
    return jsonify({"success": success, "count": len(_data_cache)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
