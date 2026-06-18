# Plex Auto Collections

Automatically create Plex collections based on your folder structure.

Each subfolder becomes a collection with the same name, and videos inside it are added automatically.

This tool is designed to be **safe and non-destructive**:
- Only creates collections that match folder names under your base path
- Only adds items to those specific collections
- Never removes items from any collection
- Never deletes or modifies existing collections
- Items can safely belong to multiple collections

## Features

- Folder name → Collection name
- Smart detection (skips folders that are already up to date)
- Dry-run mode for safe testing
- Robust path matching (works well on Windows)
- Cross-platform (Windows + Linux/Fedora)
- Easy to schedule

## Installation

```bash
pip install -r requirements.txt