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

### How to Get Your Plex Token

There are a few easy ways to get your Plex token:

1. **Easiest method**:
   - Go to [https://app.plex.tv](https://app.plex.tv) while logged into your Plex account.
   - Open Developer Tools (`F12` or right-click → Inspect).
   - Go to the **Network** tab.
   - Refresh the page and look for any request that includes `X-Plex-Token` in the request headers.

2. **Alternative method**:
   - Visit any page in Plex Web (for example your server dashboard).
   - Add `?X-Plex-Token=1` to the end of the URL and press Enter.
   - Look at the page source or network requests for your token.

Your token is a long string of letters and numbers. Copy it into your `config.json`.

## Installation

```bash
pip install -r requirements.txt