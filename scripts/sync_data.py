#!/usr/bin/env python3
"""
Sync YAML data files from the shedding-hub/shedding-hub repository.

This script downloads all YAML files from the data/ directory of the
shedding-hub repository and saves them to the local data/ directory.
"""

import os
from pathlib import Path

import fsspec


def sync_data():
    """Sync YAML files from shedding-hub repository."""
    # Destination directory
    destination = Path(__file__).parent.parent / "data"
    destination.mkdir(exist_ok=True, parents=True)

    print(f"Syncing data to {destination}")

    # Set up GitHub filesystem with authentication for higher rate limits
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        # Use token auth (username can be anything with token auth)
        fs = fsspec.filesystem(
            "github",
            org="shedding-hub",
            repo="shedding-hub",
            username="x-access-token",
            token=token
        )
        print("Using authenticated GitHub API (5000 requests/hour)")
    else:
        # Fall back to unauthenticated (60 requests/hour)
        fs = fsspec.filesystem("github", org="shedding-hub", repo="shedding-hub")
        print("Using unauthenticated GitHub API (60 requests/hour)")

    # Find all YAML files in the data directory
    yaml_files = fs.glob("data/**/*.yaml")
    print(f"Found {len(yaml_files)} YAML files in shedding-hub repository")

    # Download each file (flatten structure - all YAML files go directly into data/)
    synced_count = 0
    for remote_path in yaml_files:
        # Skip schema files or hidden files
        filename = Path(remote_path).name
        if filename.startswith('.'):
            continue

        # Flatten: all YAML files go directly into data/ directory
        local_path = destination / filename

        # Download the file
        try:
            with fs.open(remote_path, 'rb') as remote_file:
                content = remote_file.read()

            with open(local_path, 'wb') as local_file:
                local_file.write(content)

            synced_count += 1
        except Exception as e:
            print(f"Error syncing {remote_path}: {e}")

    print(f"Successfully synced {synced_count} files")


if __name__ == "__main__":
    sync_data()
