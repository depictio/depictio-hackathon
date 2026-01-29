"""Main Dash application for UMAP Image Explorer."""

import os
from pathlib import Path
from flask import send_file
from dash import Dash, DiskcacheManager
from flask_caching import Cache
import diskcache

from src.data_loader import load_phenobase_data, extract_metadata_columns
from src.layout import create_layout
from src.callbacks import register_callbacks


cache_dir = diskcache.Cache("./.cache")
background_callback_manager = DiskcacheManager(cache_dir)

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    title="UMAP Image Explorer",
    background_callback_manager=background_callback_manager,
)

server = app.server

cache = Cache(
    app.server,
    config={
        "CACHE_TYPE": "simple",
        "CACHE_DEFAULT_TIMEOUT": 3600,
    }
)

df = load_phenobase_data()
metadata = extract_metadata_columns(df)

app.layout = create_layout(
    patch_types=metadata["patch_types"],
    coordinates=metadata["coordinates"]
)

register_callbacks(app, df, cache)


@server.route("/images/<path:image_path>")
def serve_image(image_path):
    """
    Serve image files from the data directory.

    Args:
        image_path: Relative path to image within data directory

    Returns:
        Image file response
    """
    base_path = Path("data").absolute()
    full_path = base_path / image_path

    if not full_path.exists() or not full_path.is_relative_to(base_path):
        return "Image not found", 404

    return send_file(full_path, mimetype="image/png")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Starting UMAP Image Explorer")
    print("="*60)
    print(f"Loaded {len(df)} images")
    print(f"Patch types: {', '.join(metadata['patch_types'])}")
    print(f"Coordinates: {', '.join(map(str, metadata['coordinates']))}")
    print("\nApplication running at: http://127.0.0.1:8050")
    print("="*60 + "\n")

    app.run(debug=True, host="0.0.0.0", port=8050)
