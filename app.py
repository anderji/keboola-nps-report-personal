import os
import csv
import io
import json
import requests
from flask import Flask, jsonify, send_from_directory, request

app = Flask(__name__)

KBC_TOKEN = os.environ.get("KBC_TOKEN", "")
KBC_URL = os.environ.get("KBC_URL", "https://connection.europe-west3.gcp.keboola.com")
TABLE_ID = "in.c-dataaps-test.nps_text_feedback"

_data_cache = []

def load_data():
    global _data_cache
    try:
        url = f"{KBC_URL.rstrip('/')}/v2/storage/tables/{TABLE_ID}/data-preview"
        headers = {"X-StorageApi-Token": KBC_TOKEN}
        params = {"format": "json", "limit": 10000}
        resp = requests.get(url, headers=headers, params=params, timeout=60)
        if resp.status_code == 200:
            payload = resp.json()
            columns = payload.get("columns", [])
            rows = payload.get("rows", [])
            _data_cache = []
            for row in rows:
                record = {}
                for i, col in enumerate(columns):
                    record[col] = row[i] if i < len(row) else None
                _data_cache.append(record)
            print(f"[INFO] Loaded {len(_data_cache)} rows from Keboola")
            return True
        else:
            # Try export endpoint
            url2 = f"{KBC_URL.rstrip('/')}/v2/storage/tables/{TABLE_ID}/export-async"
            resp2 = requests.post(url2, headers=headers, timeout=60)
            raise Exception(f"Preview failed {resp.status_code}, export async: {resp2.status_code}")
    except Exception as e:
        print(f"[ERROR] load_data: {e}")
        # Try CSV export
        try:
            url3 = f"{KBC_URL.rstrip('/')}/v2/storage/tables/{TABLE_ID}/data-preview?format=rfc&limit=10000"
            resp3 = requests.get(url3, headers={"X-StorageApi-Token": KBC_TOKEN}, timeout=60)
            if resp3.status_code == 200:
                reader = csv.DictReader(io.StringIO(resp3.text))
                _data_cache = [row for row in reader]
                print(f"[INFO] Loaded {len(_data_cache)} rows (CSV fallback)")
                return True
        except Exception as e2:
            print(f"[ERROR] CSV fallback: {e2}")
        return False

# Load on startup
load_data()

@app.route("/", methods=["GET", "POST"])
def index():
    return send_from_directory(".", "index.html")

@app.route("/api/data", methods=["GET"])
def get_data():
    return jsonify(_data_cache)

@app.route("/api/reload", methods=["POST"])
def reload_data():
    success = load_data()
    return jsonify({"success": success, "count": len(_data_cache)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
