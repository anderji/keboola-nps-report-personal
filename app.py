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
    url = f"{KBC_URL.rstrip('/')}/v2/storage/tables/{TABLE_ID}/data-preview"

    # Try JSON format
    try:
        logger.info("Fetching data-preview (JSON, limit=1000)...")
        resp = requests.get(url, headers=headers, params={"format": "json", "limit": 1000}, timeout=60)
        logger.info(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            payload = resp.json()
            columns = payload.get("columns", [])
            rows    = payload.get("rows", [])
            logger.info(f"Columns: {columns}")
            logger.info(f"First row type: {type(rows[0]) if rows else 'no rows'}")
            logger.info(f"First row sample: {str(rows[0])[:200] if rows else 'none'}")

            result = []
            for row in rows:
                if isinstance(row, dict):
                    # rows are already key-value objects
                    result.append(row)
                elif isinstance(row, list):
                    # rows are arrays — zip with columns
                    result.append({item["columnName"]: item["value"] for item in row})
                else:
                    logger.warning(f"Unexpected row type: {type(row)}")

            _data_cache = result
            logger.info(f"Loaded {len(_data_cache)} rows")
            return True
        logger.error(f"JSON failed: {resp.text[:300]}")
    except Exception as e:
        logger.error(f"JSON error: {e}")

    # CSV fallback
    try:
        logger.info("Trying CSV fallback (limit=1000)...")
        resp2 = requests.get(url, headers=headers, params={"format": "rfc", "limit": 1000}, timeout=60)
        logger.info(f"CSV status: {resp2.status_code}")
        if resp2.status_code == 200:
            reader = csv.DictReader(io.StringIO(resp2.text))
            _data_cache = list(reader)
            logger.info(f"Loaded {len(_data_cache)} rows (CSV)")
            return True
        logger.error(f"CSV failed: {resp2.text[:300]}")
    except Exception as e2:
        logger.error(f"CSV error: {e2}")

    return False

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
