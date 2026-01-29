"""Main Dash application with WebSocket support via async-dash + Quart."""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from quart import send_file as quart_send_file, websocket
from async_dash import Dash
from flask_caching import Cache
import diskcache
from dash import DiskcacheManager
import pandas as pd

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.data_loader import load_phenobase_data, extract_metadata_columns
from src.layout import create_layout
from src.callbacks import register_callbacks

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

# Configure logging for debug mode
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)

# Track connected WebSocket clients
connected_clients = set()

cache_dir = diskcache.Cache("./.cache")
background_callback_manager = DiskcacheManager(cache_dir)

# Create async Dash app (uses Quart under the hood)
app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    title="UMAP Image Explorer",
    background_callback_manager=background_callback_manager,
)

# Get the Quart server from async-dash
server = app.server
server.debug = True  # Enable debug mode

cache = Cache(
    server,
    config={
        "CACHE_TYPE": "FileSystemCache",
        "CACHE_DIR": "./.flask_cache",
        "CACHE_DEFAULT_TIMEOUT": 3600,
        "CACHE_THRESHOLD": 100,
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
async def serve_image(image_path):
    """Serve image files from the data directory."""
    base_path = Path("data").absolute()
    full_path = base_path / image_path
    if not full_path.exists() or not full_path.is_relative_to(base_path):
        return "Image not found", 404
    return await quart_send_file(full_path, mimetype="image/png")


@server.websocket("/ws")
async def ws_endpoint():
    """WebSocket endpoint for real-time notifications."""
    client = websocket._get_current_object()
    connected_clients.add(client)
    print(f"[WebSocket] Client connected. Total: {len(connected_clients)}")
    try:
        while True:
            # Keep connection alive by waiting for any message
            await websocket.receive()
    except asyncio.CancelledError:
        pass
    finally:
        connected_clients.discard(client)
        print(f"[WebSocket] Client disconnected. Total: {len(connected_clients)}")


async def broadcast_new_images(count, total, new_rows_info=None):
    """Broadcast new image notification to all connected clients."""
    if not connected_clients:
        return
    message = json.dumps({
        'type': 'new_image',
        'count': count,
        'total': total,
        'images': new_rows_info or []
    })
    print(f"[WebSocket] Broadcasting to {len(connected_clients)} clients: {count} new images")
    for client in list(connected_clients):
        try:
            await client.send(message)
        except Exception as e:
            print(f"[WebSocket] Error sending to client: {e}")
            connected_clients.discard(client)


class CSVMonitorHandler(FileSystemEventHandler):
    """Monitor CSV for changes and trigger WebSocket broadcast."""

    def __init__(self, csv_path, initial_count, loop):
        self.csv_path = csv_path
        self.last_count = initial_count
        self.loop = loop
        self.last_modified = time.time()

    def on_modified(self, event):
        if not event.src_path.endswith('phenobase.csv'):
            return

        # Debounce
        current_time = time.time()
        if current_time - self.last_modified < 0.5:
            return
        self.last_modified = current_time

        try:
            df_check = pd.read_csv(self.csv_path, skiprows=[0])
            current_count = len(df_check)

            # Handle reset: if count decreased, update baseline
            if current_count < self.last_count:
                print(f"[CSV Monitor] Reset detected: {self.last_count} -> {current_count}")
                self.last_count = current_count
                return

            if current_count > self.last_count:
                new_count = current_count - self.last_count

                # Extract info about new rows
                new_rows = df_check.tail(new_count)
                new_rows_info = []
                for _, row in new_rows.iterrows():
                    info = {
                        'filename': row.get('czi_filename', 'unknown'),
                        'pos': int(row.get('pos', -1)),
                    }
                    new_rows_info.append(info)
                    print(f"[CSV Monitor] New: {info['filename']} (pos={info['pos']})")

                self.last_count = current_count
                print(f"[CSV Monitor] Detected {new_count} new rows, total: {current_count}")

                # Schedule async broadcast on the event loop
                asyncio.run_coroutine_threadsafe(
                    broadcast_new_images(new_count, current_count, new_rows_info),
                    self.loop
                )
        except Exception as e:
            print(f"[CSV Monitor] Error: {e}")


if __name__ == "__main__":
    import signal
    from hypercorn.config import Config
    from hypercorn.asyncio import serve

    print("\n" + "="*60)
    print("Starting UMAP Image Explorer with WebSocket Support")
    print("="*60)
    print(f"Loaded {len(df)} images")
    print(f"Patch types: {', '.join(metadata['patch_types'])}")
    print(f"Coordinates: {', '.join(map(str, metadata['coordinates']))}")
    print("WebSocket endpoint: ws://127.0.0.1:8050/ws")
    print("\nApplication running at: http://127.0.0.1:8050")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")

    config = Config()
    config.bind = ["0.0.0.0:8050"]
    config.use_reloader = False
    config.loglevel = "DEBUG"
    config.accesslog = "-"
    config.errorlog = "-"

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Shutdown event for graceful termination
    shutdown_event = asyncio.Event()

    # Start file watcher first (before signal handler references it)
    handler = CSVMonitorHandler("data/phenobase.csv", len(df), loop)
    observer = Observer()
    observer.schedule(handler, path='data/', recursive=False)
    observer.start()
    print("[CSV Monitor] Watching data/phenobase.csv")

    # Track Ctrl+C presses for force quit
    ctrl_c_count = [0]  # Use list to avoid nonlocal issues

    def signal_handler(_sig, _frame):
        ctrl_c_count[0] += 1
        print(f"\n[Server] Shutdown signal ({ctrl_c_count[0]}/2)...")
        if ctrl_c_count[0] >= 2:
            print("[Server] Force quitting...")
            observer.stop()
            import os
            os._exit(0)
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    async def run_server():
        await serve(server, config, shutdown_trigger=shutdown_event.wait)

    try:
        loop.run_until_complete(run_server())
    except KeyboardInterrupt:
        pass
    finally:
        print("[Server] Cleaning up...")
        observer.stop()
        observer.join()
        loop.close()
        print("[Server] Stopped.")
