#!/usr/bin/env python3
"""
Plex Auto Collections Webhook Listener
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

from flask import Flask, request, jsonify

app = Flask(__name__)

# Simple rate limiting
LAST_RUN = 0
MIN_INTERVAL = 300  # 5 minutes in seconds


def load_config(path: Path) -> dict:
    if not path.exists():
        logging.error(f"Config file not found: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def should_run() -> bool:
    global LAST_RUN
    now = time.time()
    if now - LAST_RUN >= MIN_INTERVAL:
        LAST_RUN = now
        return True
    return False


def run_collection_script():
    if not should_run():
        logging.info("Rate limit active — skipping collection update")
        return

    config = app.config["CONFIG"]
    cmd = [
        sys.executable,
        config["collection_script"],
        "--token", config["plex_token"],
        "--library", config["library_name"],
    ]

    if config.get("base_path"):
        cmd.extend(["--base-path", config["base_path"]])

    logging.info(f"Running collection script: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        logging.info(result.stdout)
        if result.stderr:
            logging.warning(result.stderr)
    except Exception as e:
        logging.error(f"Error running collection script: {e}")


@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_json(force=True, silent=True) or {}

    # Handle Plex multipart/form-data
    if not payload and request.form and "payload" in request.form:
        try:
            payload = json.loads(request.form["payload"])
        except Exception:
            payload = {}

    event = payload.get("event", "")
    metadata = payload.get("Metadata", {})
    library_section = metadata.get("librarySectionTitle", "")

    target_library = app.config.get("LIBRARY_NAME")

    if library_section == target_library:
        logging.info(f"Received event from target library: {event}")
        run_collection_script()

    return jsonify({"status": "received"}), 200


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.json")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s | %(levelname)s | %(message)s")

    config = load_config(Path(args.config))

    app.config["CONFIG"] = config
    app.config["LIBRARY_NAME"] = config["library_name"]

    logging.info("Starting Webhook Listener...")
    logging.info(f"Target library: {config['library_name']}")

    app.run(host="0.0.0.0", port=8787, debug=args.verbose)


if __name__ == "__main__":
    main()