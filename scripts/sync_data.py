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

    # Set up GitHub filesystem
    # Use GITHUB_TOKEN if available (for higher rate limits)
    token = os.environ.get("GITHUB_TOKEN")

    fs_kwargs = {
        "org": "shedding-hub",
        "repo": "shedding-hub",
    }
    if token:
        fs_kwargs["token"] = token

    fs = fsspec.filesystem("github", **fs_kwargs)

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
