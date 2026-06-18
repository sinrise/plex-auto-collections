#!/usr/bin/env python3
"""
Plex Auto Collections

Create Plex collections automatically based on folder structure.
Designed to be simple today and extensible in the future.

Repository: https://github.com/YOUR_USERNAME/plex-auto-collections
"""

import argparse
import logging
import sys
from pathlib import Path
from importlib.metadata import version, PackageNotFoundError

from plexapi.server import PlexServer
from plexapi.exceptions import NotFound, Unauthorized

__version__ = "0.1.0"

DEFAULT_PLEX_URL = "http://localhost:32400"
DEFAULT_LIBRARY = "Personal Videos"
DEFAULT_BASE_PATH = Path.home() / "Videos" / "Personal"


def get_version() -> str:
    try:
        return version("plex-auto-collections")
    except PackageNotFoundError:
        return __version__


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )


def get_plex_server(url: str, token: str) -> PlexServer:
    try:
        return PlexServer(url, token)
    except Unauthorized:
        logging.error("Invalid Plex token. Please check your token.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Could not connect to Plex server: {e}")
        sys.exit(1)


def get_or_create_collection(library, name: str):
    try:
        return library.collection(name)
    except NotFound:
        logging.info(f"Creating new collection: {name}")
        return library.createCollection(title=name, smart=False)


def process_folder(library, folder_path: Path, dry_run: bool = False) -> int:
    collection_name = folder_path.name
    collection = get_or_create_collection(library, collection_name)

    added_count = 0
    try:
        items = library.all()
    except Exception as e:
        logging.error(f"Failed to load library items: {e}")
        return 0

    for item in items:
        for location in item.locations or []:
            if location.startswith(str(folder_path)):
                if item not in collection.items():
                    if not dry_run:
                        collection.addItems(item)
                    logging.info(f"  + Added to '{collection_name}': {item.title}")
                    added_count += 1
                break
    return added_count


def main():
    parser = argparse.ArgumentParser(
        description="Plex Auto Collections - Create collections from folder names."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {get_version()}")
    parser.add_argument("--plex-url", default=DEFAULT_PLEX_URL)
    parser.add_argument("--token", required=True, help="Your Plex authentication token")
    parser.add_argument("--library", default=DEFAULT_LIBRARY)
    parser.add_argument("--base-path", type=Path, default=DEFAULT_BASE_PATH)
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args()
    setup_logging(args.verbose)

    logging.info("=== Plex Auto Collections ===")
    logging.info(f"Library     : {args.library}")
    logging.info(f"Base Path   : {args.base_path}")
    if args.dry_run:
        logging.warning("DRY RUN MODE — No changes will be made")

    if not args.base_path.is_dir():
        logging.error(f"Base path does not exist: {args.base_path}")
        sys.exit(1)

    plex = get_plex_server(args.plex_url, args.token)

    try:
        library = plex.library.section(args.library)
    except NotFound:
        logging.error(f"Library '{args.library}' was not found.")
        sys.exit(1)

    total_added = 0
    for folder in sorted(args.base_path.iterdir()):
        if folder.is_dir():
            logging.info(f"Scanning folder: {folder.name}")
            added = process_folder(library, folder, dry_run=args.dry_run)
            total_added += added

    logging.info(f"Completed. Total items added: {total_added}")


if __name__ == "__main__":
    main()