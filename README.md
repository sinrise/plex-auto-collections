# Plex Auto Collections

Automatically create and manage Plex collections based on your folder structure. Simple, safe, and effective even on large libraries.

Each subfolder becomes a collection with the same name, and videos inside those folders are added to the collection.

## Features

- Creates collections named after folders
- Updates existing collections when new items are added
- Auto-detects library locations from Plex
- Clean summary at the end of each run
- Safe and non-destructive (never removes items from collections)
- Supports `config.json` for convenience
- Dry-run mode available
- Works on Windows and Linux

## Installation
```bash
pip install -r requirements.txt
```

## Usage
**Requirements**

You must specify your Plex token in `config.json`

You must specify which library to process using the --library flag:

```Bash
py plex_auto_collections.py --library "Your Library Name"
```

# Common Examples

Basic usage:
```Bash
py plex_auto_collections.py --library "Personal Videos"
```
Dry run (recommended first):
```Bash
py plex_auto_collections.py --library "Personal Videos" --dry-run
```
Verbose output:
```Bash
py plex_auto_collections.py --library "Personal Videos" -v
```
Override token from command line:
```Bash
py plex_auto_collections.py --library "Personal Videos" --token your-token-here
```

Summary Output
After each run, the script shows a clean summary:
```text
=== Summary ===
Created:     87 new collections
Updated:     12 existing collections
Up to date:  312 folders (no changes needed)
No items:    45 folders had no matching items in Plex
Total items: 1243
Done.
```
# How It Works

If --base-path is not provided, the script automatically reads the folder locations configured for the library in Plex.
It then scans those locations and creates/updates collections based on subfolder names.
You can safely run this script multiple times.

# Safety
This tool is designed to be safe:

It only adds items to collections.
It never removes items from existing collections.
Items can belong to multiple collections without issue.

# License
MIT License
