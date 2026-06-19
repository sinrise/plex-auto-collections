#!/usr/bin/env python3
"""
Plex Auto Collections

Creates and updates Plex collections based on folder names.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from plexapi.server import PlexServer
from plexapi.exceptions import NotFound, Unauthorized

__version__ = "1.4.0"


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )


def paths_match(plex_location: str, target_folder: Path) -> bool:
    normalized = plex_location.replace('/', '\\').lower()
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


def process_folder(library, folder_path: Path, dry_run: bool = False, stats=None):
    if stats is None:
        stats = {"created": 0, "updated": 0, "up_to_date": 0, "no_items": 0}

    collection_name = folder_path.name
    logging.info(f"Processing: {collection_name}")

    matching_items = []
    try:
        all_items = library.all()
    except Exception as e:
        logging.error(f"Failed to load library: {e}")
        return 0

    for item in all_items:
        for location in item.locations or []:
            if paths_match(location, folder_path):
                matching_items.append(item)
                break

    if not matching_items:
        stats["no_items"] += 1
        logging.info(f"  No items found")
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

    return added


def main():
    parser = argparse.ArgumentParser(
        description="Plex Auto Collections - Create collections from folder names"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--plex-url", help="Plex server URL (overrides config)")
    parser.add_argument("--token", help="Plex token (overrides config)")
    parser.add_argument("--library", required=True, help="Library name (required)")
    parser.add_argument("--base-path", type=Path, help="Limit to a specific base path")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()
    setup_logging(args.verbose)

    config = load_config(Path(args.config))

    plex_url = args.plex_url or config.get("plex_url", "http://localhost:32400")
    token = args.token or config.get("plex_token")
    library_name = args.library
    base_path = args.base_path or (Path(config["base_path"]) if config.get("base_path") else None)

    if not token:
        logging.error("Plex token is required (--token or in config.json)")
        sys.exit(1)

    logging.info("=== Plex Auto Collections ===")
    logging.info(f"Library: {library_name}")

    plex = PlexServer(plex_url, token)

    try:
        library = plex.library.section(library_name)
    except NotFound:
        logging.error(f"Library '{library_name}' not found.")
        sys.exit(1)

    if base_path:
        locations = [base_path]
    else:
        locations = [Path(loc) for loc in library.locations]
        logging.info(f"Auto-detected locations from Plex: {locations}")

    stats = {"created": 0, "updated": 0, "up_to_date": 0, "no_items": 0}
    total_items = 0

    for location in locations:
        if not location.is_dir():
            logging.warning(f"Skipping missing location: {location}")
            continue

        logging.info(f"Scanning location: {location}")
        for folder in sorted(location.iterdir()):
            if folder.is_dir():
                added = process_folder(library, folder, dry_run=args.dry_run, stats=stats)
                total_items += added

    # Final Summary
    logging.info("=== Summary ===")
    if args.dry_run:
        logging.info(f"Dry run complete. Would have processed {total_items} items across {len(locations)} location(s).")
    else:
        logging.info(f"Created:   {stats['created']} new collections")
        logging.info(f"Updated:   {stats['updated']} existing collections")
        logging.info(f"Up to date: {stats['up_to_date']} folders (no changes needed)")
        logging.info(f"No items:   {stats['no_items']} folders had no matching items in Plex")
        logging.info(f"Total items processed: {total_items}")

    logging.info("Done.")


if __name__ == "__main__":
    main()