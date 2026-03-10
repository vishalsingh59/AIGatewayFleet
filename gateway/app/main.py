import os
import threading
import time

from fastapi import FastAPI

from gateway.app.routes import router
from gateway.app.services import forward_buffered_metrics, is_gateway_online, sync_from_ci

app = FastAPI(title="AI Gateway")
app.include_router(router)

SYNC_INTERVAL_SECONDS = int(os.getenv("GATEWAY_SYNC_INTERVAL", "60"))


def _background_sync_loop():
    while True:
        try:
            if is_gateway_online():
                sync_from_ci()
                forward_buffered_metrics()
        except Exception:
            pass
        time.sleep(SYNC_INTERVAL_SECONDS)


@app.on_event("startup")
def start_background_sync():
    thread = threading.Thread(target=_background_sync_loop, daemon=True)
    thread.start()
