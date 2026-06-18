# Plex Auto Collections

Automatically create Plex collections from your folder structure.

Each subfolder becomes a collection with the same name. Videos inside the folder are automatically added to that collection.

This tool is intentionally designed to be simple today while remaining easy to extend in the future.

## Features
- Folder name → Collection name
- Idempotent (safe to run multiple times)
- Dry-run mode
- Cross-platform (Windows + Linux/Fedora)
- Easy to schedule

## Installation

```bash
pip install plexapi