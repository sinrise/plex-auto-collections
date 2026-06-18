#!/usr/bin/env python3
"""
Plex Auto Collections

Automatically creates Plex collections based on folder names.
Safe, non-destructive behavior:
- Only creates collections matching folder names under --base-path
- Only adds items to those specific collections
- Never removes items from any collection
- Never deletes or modifies existing collections

Items can belong to multiple collections without issue.
"""

import argparse
import logging
import sys
from pathlib import Path

from plexapi.server import PlexServer
from plexapi.exceptions import NotFound, Unauthorized

__version__ = "0.2.0"


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )


def paths_match(plex_location: str, target_folder: Path) -> bool:
    """Robust path comparison for Windows + Plex."""
    normalized = plex_location.replace('/', '\\').lower()
    target = str(target_folder).lower()
    return normalized.startswith(target)


def get_or_create_collection(library, name: str, items=None):
    """
    Get existing collection or create one with items.
    Uses items= parameter during creation (most reliable method).
    """
    if items is None:
        items = []

    # Check if it already exists
    try:
        for col in library.collections():
            if col.title == name:
                return col
    except Exception:
        pass

    if not items:
        logging.warning(f"No items available to create collection '{name}'")
        return None

    try:
        logging.info(f"Creating new collection: {name}")
        # Create collection + add items in one call
        collection = library.createCollection(
            title=name,
            items=items,
            smart=False
        )
        return collection
    except Exception as e:
        logging.error(f"Failed to create collection '{name}': {e}")
        return None

def process_folder(library, folder_path: Path, dry_run: bool = False):
    collection_name = folder_path.name
    logging.info(f"Scanning folder: {collection_name}")

    # Find items belonging to this folder
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

    # Check if collection already exists and is complete
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
            logging.info(f"  '{collection_name}' is already up to date ({len(matching_items)} items)")
            return 0

        if dry_run:
            logging.info(f"  [DRY RUN] Would add {len(missing)} missing item(s) to '{collection_name}'")
            return len(missing)

        for item in missing:
            existing.addItems(item)
            logging.info(f"  + Added: {item.title}")
        return len(missing)

    # Collection doesn't exist — create it
    if dry_run:
        logging.info(f"  [DRY RUN] Would create '{collection_name}' with {len(matching_items)} item(s)")
        return len(matching_items)

    collection = get_or_create_collection(library, collection_name, items=matching_items)
    if collection:
        logging.info(f"  Created '{collection_name}' with {len(matching_items)} item(s)")
        return len(matching_items)

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Plex Auto Collections - Create collections from folder names (safe & non-destructive)."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--plex-url", default="http://localhost:32400")
    parser.add_argument("--token", required=True, help="Plex authentication token")
    parser.add_argument("--library", required=True, help="Name of the Plex library")
    parser.add_argument("--base-path", type=Path, required=True, help="Root folder containing your collection folders")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying them")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args()
    setup_logging(args.verbose)

    logging.info("=== Plex Auto Collections ===")
    logging.info(f"Library   : {args.library}")
    logging.info(f"Base Path : {args.base_path}")
    if args.dry_run:
        logging.warning("DRY RUN MODE — No changes will be made to Plex")

    if not args.base_path.is_dir():
        logging.error(f"Base path does not exist: {args.base_path}")
        sys.exit(1)

    plex = PlexServer(args.plex_url, args.token)

    try:
        library = plex.library.section(args.library)
    except NotFound:
        logging.error(f"Library '{args.library}' not found.")
        sys.exit(1)

    total_added = 0
    for folder in sorted(args.base_path.iterdir()):
        if folder.is_dir():
            added = process_folder(library, folder, dry_run=args.dry_run)
            total_added += added

    logging.info(f"Finished. Total items added/updated: {total_added}")


if __name__ == "__main__":
    main()