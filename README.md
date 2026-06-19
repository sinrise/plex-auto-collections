# Plex Auto Collections

A simple tool to automatically create and update Plex collections based on your folder structure.

Each subfolder inside your library becomes a collection with the same name, and videos inside those folders are added to the collection.

## Features

- Creates collections named after folders
- Updates existing collections with new items
- Auto-detects library locations from Plex (no need to specify paths manually)
- Safe and non-destructive (never removes items from collections)
- Dry-run mode for testing
- Works on Windows and Linux

## Installation

```bash
pip install -r requirements.txt