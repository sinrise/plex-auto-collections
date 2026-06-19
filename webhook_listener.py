#!/usr/bin/env python3
"""
Plex Auto Collections - Webhook Listener

Listens for Plex webhooks and triggers the collection script
when the target library has activity (new media, scan, etc.).

Configuration is primarily done via config.json, with CLI overrides supported.
"""

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path

from flask import Flask, request, jsonify

app = Flask(__name__)


def load_config(config_path: Path) -> dict:
    """Load configuration from JSON file."""
    if not config_path.exists():
        logging.error(f"Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_config(config: dict, args: argparse.Namespace) -> dict:
    """Allow CLI arguments to override config values."""
    if args.library:
        config["library_name"] = args.library
    if args.token:
        config["plex_token"] = args.token
    if args.base_path:
        config["base_path"] = str(args.base_path)
    if args.script_path:
        config["collection_script"] = str(args.script_path)
    return config


def run_collection_script(config: dict, dry_run: bool = False):
    """Execute the collection script."""
    script_path = Path(config["collection_script"])
    if not script_path.exists():
        logging.error(f"Collection script not found: {script_path}")
        return

    cmd = [
        sys.executable,
        str(script_path),
        "--token", config["plex_token"],
        "--library", config["library_name"],
        "--base-path", config["base_path"],
    ]

    if dry_run:
        cmd.append("--dry-run")

    logging.info(f"Triggering collection script: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        logging.info(result.stdout)
        if result.stderr:
            logging.error(result.stderr)
    except Exception as e:
        logging.error(f"Failed to run collection script: {e}")


@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.json or {}
    event = payload.get("event", "")
    metadata = payload.get("Metadata", {})
    library_section = metadata.get("librarySectionTitle", "")

    target_library = app.config["LIBRARY_NAME"]

    # Trigger on relevant events for our target library
    relevant_events = ["library.new", "library.on.deck", "media.scrobble", "library.scan"]

    if event in relevant_events and library_section == target_library:
        logging.info(f"Received relevant event: {event} for library: {library_section}")
        run_collection_script(app.config["CONFIG"], dry_run=app.config.get("DRY_RUN", False))
        return jsonify({"status": "triggered"}), 200

    return jsonify({"status": "ignored"}), 200


def main():
    parser = argparse.ArgumentParser(description="Plex Auto Collections Webhook Listener")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--library", help="Override library name from config")
    parser.add_argument("--token", help="Override Plex token from config")
    parser.add_argument("--base-path", type=Path, help="Override base path from config")
    parser.add_argument("--script-path", type=Path, help="Path to plex_auto_collections.py")
    parser.add_argument("--dry-run", action="store_true", help="Run collection script in dry-run mode")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s | %(levelname)s | %(message)s")

    config_path = Path(args.config)
    config = load_config(config_path)
    config = merge_config(config, args)

    # Store config in Flask app for the webhook route
    app.config["CONFIG"] = config
    app.config["LIBRARY_NAME"] = config.get("library_name")
    app.config["DRY_RUN"] = args.dry_run

    logging.info("Starting Plex Auto Collections Webhook Listener...")
    logging.info(f"Listening for events on library: {app.config['LIBRARY_NAME']}")

    app.run(host="0.0.0.0", port=8787, debug=args.verbose)


if __name__ == "__main__":
    main()