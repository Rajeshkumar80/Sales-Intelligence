"""Background sales generator. One instance per API process (uvicorn runs 1 worker)."""

import random
import threading
from datetime import datetime, timedelta, timezone

from . import config, db, ingest
from .catalog import PRODUCTS, REGIONS
from .schemas import TransactionIn


class SalesSimulator:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._interval = config.SIMULATOR_INTERVAL
        self._batch = config.SIMULATOR_BATCH
        self.generated = 0
        self.ticks = 0
        self.started_at: datetime | None = None
        self.last_error: str | None = None
        self._rng = random.Random()

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, interval: float | None = None, batch_size: int | None = None) -> dict:
        with self._lock:
            if self.running:
                return self.status()
            self._interval = float(interval or self._interval)
            self._batch = int(batch_size or self._batch)
            self._stop.clear()
            self.started_at = db.now()
            self.generated = 0
            self.ticks = 0
            self.last_error = None
            self._thread = threading.Thread(target=self._run, name="sales-simulator", daemon=True)
            self._thread.start()
        return self.status()

    def stop(self) -> dict:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=10)
        self._thread = None
        return self.status()

    def status(self) -> dict:
        return {
            "running": self.running,
            "interval_seconds": self._interval,
            "batch_size": self._batch,
            "generated": self.generated,
            "ticks": self.ticks,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_error": self.last_error,
        }

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                payloads = [self._random_transaction() for _ in range(self._batch)]
                docs = [ingest.transaction_doc(p, source="simulator") for p in payloads]
                db.get_db()[db.TRANSACTIONS].insert_many(docs, ordered=False)
                self.generated += len(docs)
                self.ticks += 1
            except Exception as exc:  # keep the generator alive, surface the error in status
                self.last_error = str(exc)[:300]
            self._stop.wait(self._interval)

    def _random_transaction(self) -> TransactionIn:
        product_id, name, category, price = self._rng.choice(PRODUCTS)
        drift = self._rng.uniform(0.95, 1.05)
        return TransactionIn(
            transaction_id=None,
            product_id=product_id,
            product_name=name,
            category=category,
            quantity=self._rng.choices([1, 2, 3, 4, 5, 8], weights=[45, 25, 15, 8, 5, 2])[0],
            unit_price=round(price * drift, 2),
            region=self._rng.choice(REGIONS),
            timestamp=datetime.now(timezone.utc) - timedelta(seconds=self._rng.randint(0, 3600)),
        )


simulator = SalesSimulator()
