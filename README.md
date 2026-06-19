# Plex Auto Collections

Automatically create Plex collections based on your folder structure.

Each subfolder becomes a collection with the same name, and videos inside it are added automatically.

This tool is designed to be **safe and non-destructive** — it only adds items to folder-named collections and never removes items from existing collections.

## Features

- Folder name → Collection name
- Smart "already up to date" detection
- Dry-run mode
- Webhook support for automatic triggering after Plex library activity
- Cross-platform (Windows + Linux)

## Installation

```bash
pip install -r requirements.txt