#!/usr/bin/env python3
"""
Plex Auto Collections v2.1

Default: Fast incremental update
--force: Full re-scan
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import platformdirs
from plexapi.server import PlexServer
from plexapi.exceptions import NotFound

__version__ = "2.1.0"
APP_NAME = "plex-auto-collections"


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )


def load_config(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_state_file() -> Path:
    data_dir = Path(platformdirs.user_data_dir(APP_NAME))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "state.json"


def load_state() -> dict:
    state_file = get_state_file()
    if state_file.exists():
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"processed": {}}


def save_state(state: dict):
    state_file = get_state_file()
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def paths_match(plex_location: str, target_folder: Path) -> bool:
    normalized = plex_location.replace('\\', '/').lower()
    target = str(target_folder).lower()
    return normalized.startswith(target)


def get_or_create_collection(library, name: str, items=None):
    if items is None:
        items = []

    try:
        for col in library.collections():
            if col.title == name:
                return col
    except Exception:
        pass

    if not items:
        return None

    try:
        logging.info(f"Creating collection: {name}")
        return library.createCollection(title=name, items=items, smart=False)
    except Exception as e:
        logging.error(f"Failed to create collection '{name}': {e}")
        return None


def should_process_folder(folder_path: Path, state: dict, force: bool) -> bool:
    if force:
        return True

    folder_str = str(folder_path)
    processed = state.get("processed", {})

    if folder_str not in processed:
        return True  # New folder

    stored_mtime = processed[folder_str].get("folder_mtime", 0)
    try:
        current_mtime = os.stat(folder_path).st_mtime
    except OSError:
        return True

    return current_mtime > stored_mtime


def update_folder_state(folder_path: Path, state: dict):
    folder_str = str(folder_path)
    try:
        mtime = os.stat(folder_path).st_mtime
    except OSError:
        mtime = time.time()

    state.setdefault("processed", {})[folder_str] = {
        "last_processed": datetime.now().isoformat(),
        "folder_mtime": mtime
    }


def process_folder(library, library_items, folder_path: Path, dry_run: bool, force: bool, state: dict, stats: dict):
    if not should_process_folder(folder_path, state, force):
        logging.info(f"Skipping (up to date): {folder_path.name}")
        stats["skipped"] += 1
        return 0

    collection_name = folder_path.name
    logging.info(f"Processing: {collection_name}")

    matching_items = []
    for item in library_items:
        for location in item.locations or []:
            if paths_match(location, folder_path):
                matching_items.append(item)
                break

    if not matching_items:
        stats["no_items"] += 1
        logging.info(f"  No items found")
        if not force:
            update_folder_state(folder_path, state)
        return 0

    if dry_run:
        logging.info(f"  [DRY RUN] Would manage {len(matching_items)} item(s)")
        return len(matching_items)

    collection = get_or_create_collection(library, collection_name, items=matching_items)
    if not collection:
        return 0

    added = 0
    for item in matching_items:
        if item not in collection.items():
            collection.addItems(item)
            logging.info(f"  + Added: {item.title}")
            added += 1

    if added == 0:
        stats["up_to_date"] += 1
        logging.info(f"  Already up to date")
    else:
        stats["updated"] += 1
        logging.info(f"  Updated with {added} new item(s)")

    if not force:
        update_folder_state(folder_path, state)

    return added


def main():
    parser = argparse.ArgumentParser(
        description="Plex Auto Collections"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--plex-url", help="Plex server URL (overrides config)")
    parser.add_argument("--token", help="Plex token (overrides config)")
    parser.add_argument("--library", required=True, help="Library name (required)")
    parser.add_argument("--base-path", type=Path, help="Limit to a specific base path")
    parser.add_argument("--force", action="store_true", help="Force full re-scan (ignore state)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()
    setup_logging(args.verbose)

    config = load_config(Path(args.config))

    plex_url = args.plex_url or config.get("plex_url", "http://localhost:32400")
    token = args.token or config.get("plex_token")
    library_name = args.library
    base_path = args.base_path

    if not token:
        logging.error("Plex token is required (--token or in config.json)")
        sys.exit(1)

    logging.info("=== Plex Auto Collections ===")
    logging.info(f"Library: {library_name}")
    if args.force:
        logging.info("Mode: FORCE FULL SCAN")
    else:
        logging.info("Mode: Fast incremental (use --force for full scan)")

    plex = PlexServer(plex_url, token)

    try:
        library = plex.library.section(library_name)
    except NotFound:
        logging.error(f"Library '{library_name}' not found.")
        sys.exit(1)

    logging.info("Loading all library items...")
    try:
        library_items = library.all()
        logging.info(f"Loaded {len(library_items)} items from Plex")
    except Exception as e:
        logging.error(f"Failed to load library items: {e}")
        sys.exit(1)

    if base_path:
        locations = [base_path]
    else:
        locations = [Path(loc) for loc in library.locations]
        logging.info(f"Auto-detected locations from Plex: {locations}")

    state = load_state() if not args.force else {"processed": {}}
    stats = {"created": 0, "updated": 0, "up_to_date": 0, "no_items": 0, "skipped": 0}
    total_items = 0

    for location in locations:
        if not location.is_dir():
            logging.warning(f"Skipping missing location: {location}")
            continue

        logging.info(f"Scanning location: {location}")
        for folder in sorted(location.iterdir()):
            if folder.is_dir():
                added = process_folder(
                    library, library_items, folder, args.dry_run, args.force, state, stats
                )
                total_items += added

    if not args.force and not args.dry_run:
        save_state(state)

    logging.info("=== Summary ===")
    if args.dry_run:
        logging.info(f"Dry run complete. Would have processed items across {len(locations)} location(s).")
    else:
        logging.info(f"Created:     {stats['created']} new collections")
        logging.info(f"Updated:     {stats['updated']} existing collections")
        logging.info(f"Up to date:  {stats['up_to_date']} folders")
        logging.info(f"No items:    {stats['no_items']} folders")
        if not args.force:
            logging.info(f"Skipped:     {stats['skipped']} folders (no changes)")
        logging.info(f"Total items: {total_items}")

    logging.info("Done.")


if __name__ == "__main__":
    main()
