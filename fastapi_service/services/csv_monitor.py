"""CSV file monitoring service for detecting new data."""

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional

import pandas as pd
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from fastapi_service.websocket.manager import manager

logger = logging.getLogger(__name__)


class CSVMonitorHandler(FileSystemEventHandler):
    """Monitors CSV file for changes and broadcasts updates."""

    def __init__(self, csv_path: str, loop: asyncio.AbstractEventLoop):
        self.csv_path = csv_path
        self.loop = loop
        self.last_count = self._get_row_count()
        self.last_modified = time.time()
        self.debounce_delay = 0.5

    def _get_row_count(self) -> int:
        """Get current row count from CSV."""
        try:
            df = pd.read_csv(self.csv_path, skiprows=[0])
            return len(df)
        except Exception as e:
            logger.error(f"Failed to read CSV: {e}")
            return 0

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory or not event.src_path.endswith("phenobase.csv"):
            return

        current_time = time.time()
        if current_time - self.last_modified < self.debounce_delay:
            return
        self.last_modified = current_time

        try:
            current_count = self._get_row_count()

            if current_count < self.last_count:
                logger.info(f"CSV reset: {self.last_count} → {current_count}")
                self.last_count = current_count
                return

            if current_count > self.last_count:
                new_count = current_count - self.last_count
                df = pd.read_csv(self.csv_path, skiprows=[0])
                new_rows = df.tail(new_count)

                new_rows_info = []
                for _, row in new_rows.iterrows():
                    info = {
                        "filename": row.get("czi_filename", "unknown"),
                        "pos": int(row.get("pos", -1)),
                        "patch_path": row.get("patches_2d_ch0_tl_exp_path", ""),
                    }
                    new_rows_info.append(info)

                self.last_count = current_count
                logger.info(f"Detected {new_count} new rows, total: {current_count}")

                asyncio.run_coroutine_threadsafe(
                    manager.notify_new_images(new_count, current_count, new_rows_info),
                    self.loop,
                )
        except Exception as e:
            logger.error(f"CSV monitor error: {e}")


class CSVWatcherService:
    """Service for watching CSV file changes."""

    def __init__(self):
        self.observer: Optional[Observer] = None

    def start(self, csv_path: str, loop: asyncio.AbstractEventLoop):
        """Start monitoring the CSV file."""
        csv_file = Path(csv_path)
        if not csv_file.exists():
            logger.error(f"CSV file not found: {csv_path}")
            return

        handler = CSVMonitorHandler(csv_path, loop)
        self.observer = Observer()
        self.observer.schedule(handler, path=str(csv_file.parent), recursive=False)
        self.observer.start()
        logger.info(f"Started monitoring: {csv_path}")

    def stop(self):
        """Stop monitoring the CSV file."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("CSV Watcher stopped")


csv_watcher = CSVWatcherService()
