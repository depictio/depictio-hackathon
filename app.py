"""Main Dash application with Flask backend."""

import logging
import sys
from pathlib import Path

import diskcache
from dash import Dash, DiskcacheManager
from flask import Flask, send_file
from flask_caching import Cache

from src.callbacks import register_callbacks
from src.data_loader import extract_metadata_columns, load_phenobase_data
from src.layout import create_layout

sys.stdout.reconfigure(line_buffering=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

cache_dir = diskcache.Cache("./.cache")
background_callback_manager = DiskcacheManager(cache_dir)

# Standard Flask-based Dash app
app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    title="UMAP Image Explorer",
    background_callback_manager=background_callback_manager,
)

server = app.server
server.debug = True

cache = Cache(
    server,
    config={
        "CACHE_TYPE": "FileSystemCache",
        "CACHE_DIR": "./.flask_cache",
        "CACHE_DEFAULT_TIMEOUT": 3600,
        "CACHE_THRESHOLD": 100,
    },
)

df = load_phenobase_data()
metadata = extract_metadata_columns(df)

app.layout = create_layout(
    patch_types=metadata["patch_types"], coordinates=metadata["coordinates"]
)

register_callbacks(app, df, cache)


@server.route("/images/<path:image_path>")
def serve_image(image_path):
    """Serve image files."""
    base_path = Path("data").absolute()
    full_path = base_path / image_path
    if not full_path.exists() or not full_path.is_relative_to(base_path):
        return "Image not found", 404
    return send_file(full_path, mimetype="image/png")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("UMAP Image Explorer (Flask + Dash)")
    print("=" * 60)
    print(f"Loaded {len(df)} images")
    print("Dash UI:           http://127.0.0.1:8050")
    print("FastAPI WebSocket: http://127.0.0.1:8058")
    print("=" * 60 + "\n")

    app.run(debug=True, host="0.0.0.0", port=8050)
