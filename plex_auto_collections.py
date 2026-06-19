#!/usr/bin/env python3
"""
Plex Auto Collections

Creates and updates Plex collections based on folder names.
Safe, simple, and reliable for manual use.
"""

import argparse
import logging
import sys
from pathlib import Path

from plexapi.server import PlexServer
from plexapi.exceptions import NotFound, Unauthorized

__version__ = "1.0.0"


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


def process_folder(library, folder_path: Path, dry_run: bool = False):
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
        logging.info(f"  No items found in Plex for this folder")
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
        logging.info(f"  Already up to date ({len(matching_items)} items)")
    else:
        logging.info(f"  Updated collection with {added} new item(s)")

    return added


def main():
    parser = argparse.ArgumentParser(
        description="Plex Auto Collections - Create collections from folder names"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--plex-url", default="http://localhost:32400")
    parser.add_argument("--token", required=True, help="Plex authentication token")
    parser.add_argument("--library", required=True, help="Library name in Plex")
    parser.add_argument("--base-path", type=Path, help="Optional: specific folder to scan")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes only")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()
    setup_logging(args.verbose)

    logging.info("=== Plex Auto Collections ===")
    logging.info(f"Library: {args.library}")

    plex = PlexServer(args.plex_url, args.token)

    try:
        library = plex.library.section(args.library)
    except NotFound:
        logging.error(f"Library '{args.library}' not found.")
        sys.exit(1)

    # Determine locations to scan
    if args.base_path:
        locations = [args.base_path]
    else:
        locations = [Path(loc) for loc in library.locations]
        logging.info(f"Auto-detected locations from Plex: {locations}")

    total = 0
    for location in locations:
        if not location.is_dir():
            logging.warning(f"Skipping missing location: {location}")
            continue

        logging.info(f"Scanning location: {location}")
        for folder in sorted(location.iterdir()):
            if folder.is_dir():
                total += process_folder(library, folder, dry_run=args.dry_run)

    logging.info(f"Finished. Total items processed: {total}")


if __name__ == "__main__":
    main()