# Plex Auto Collections

Automatically create Plex collections from your folder structure.

Each subfolder becomes a collection with the same name, and videos inside it are added automatically.

This tool is intentionally designed to be simple today while remaining easy to extend later.

## Features
- Folder name → Collection name
- Safe to run multiple times (idempotent)
- Dry-run mode
- Cross-platform (Windows + Linux/Fedora)
- Easy to schedule

## Installation

```bash
pip install -r requirements.txt