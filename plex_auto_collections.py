#!/usr/bin/env python3
"""
Plex Auto Collections

Automatically creates collections based on folder names inside any locations
configured for a Plex library.

If no base path is provided, it automatically uses all locations configured
in Plex for the specified library.
"""

import argparse
import logging
import sys
from pathlib import Path

from plexapi.server import PlexServer
from plexapi.exceptions import NotFound, Unauthorized

__version__ = "0.3.0"


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
        logging.warning(f"No items to create collection '{name}'")
        return None

    try:
        logging.info(f"Creating new collection: {name}")
        collection = library.createCollection(title=name, items=items, smart=False)
        return collection
    except Exception as e:
        logging.error(f"Failed to create collection '{name}': {e}")
        return None


def process_folder(library, folder_path: Path, dry_run: bool = False):
    collection_name = folder_path.name
    logging.info(f"Scanning folder: {collection_name}")

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
        logging.info(f"  No matching items found")
        return 0

    existing = None
    try:
        for col in library.collections():
            if col.title == collection_name:
                existing = col
                break
    except Exception:
        pass

    if existing:
        existing_items = set(existing.items())
        missing = [i for i in matching_items if i not in existing_items]

        if not missing:
            logging.info(f"  '{collection_name}' is already up to date")
            return 0

        if dry_run:
            logging.info(f"  [DRY RUN] Would add {len(missing)} item(s)")
            return len(missing)

        for item in missing:
            existing.addItems(item)
            logging.info(f"  + Added: {item.title}")
        return len(missing)

    if dry_run:
        logging.info(f"  [DRY RUN] Would create '{collection_name}' with {len(matching_items)} items")
        return len(matching_items)

    collection = get_or_create_collection(library, collection_name, items=matching_items)
    if collection:
        logging.info(f"  Created '{collection_name}' with {len(matching_items)} items")
        return len(matching_items)

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Plex Auto Collections - Auto-detects library locations from Plex when possible."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--plex-url", default="http://localhost:32400")
    parser.add_argument("--token", required=True)
    parser.add_argument("--library", required=True)
    parser.add_argument("--base-path", type=Path, help="Optional: limit to a specific folder")
    parser.add_argument("--dry-run", action="store_true")
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

    # Determine which locations to scan
    if args.base_path:
        locations = [args.base_path]
        logging.info(f"Using provided base path: {args.base_path}")
    else:
        locations = [Path(loc) for loc in library.locations]
        logging.info(f"Auto-detected library locations from Plex: {locations}")

    total_added = 0
    for location in locations:
        if not location.is_dir():
            logging.warning(f"Location does not exist or is not accessible: {location}")
            continue

        logging.info(f"Processing location: {location}")
        for folder in sorted(location.iterdir()):
            if folder.is_dir():
                added = process_folder(library, folder, dry_run=args.dry_run)
                total_added += added

    logging.info(f"Finished. Total items added/updated: {total_added}")


if __name__ == "__main__":
    main()