"""Los informes PDF no deben acaparar el servicio: ReportLab es Python puro y retiene el GIL, asi que
la generacion va a un grupo propio de 2 hilos (ver docs/INFORME_CARGA_21_NOV.md)."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app import main
from app.main import create_app

CSRF = {"X-Requested-With": "atalaya"}


def test_pdf_generation_is_bounded_and_off_the_default_pool(monkeypatch):
    lock = threading.Lock()
    state = {"now": 0, "peak": 0, "names": set()}
    real = main.build_org_pdf

    def slow_build(*args, **kwargs):
        with lock:
            state["now"] += 1
            state["peak"] = max(state["peak"], state["now"])
            state["names"].add(threading.current_thread().name)
        time.sleep(0.05)
        try:
            return real(*args, **kwargs)
        finally:
            with lock:
                state["now"] -= 1

    monkeypatch.setattr(main, "build_org_pdf", slow_build)
    client = TestClient(create_app(), headers=CSRF)

    def get(_):
        return client.get("/api/org-report?formato=pdf")

    with ThreadPoolExecutor(8) as pool:
        responses = list(pool.map(get, range(8)))

    assert all(r.status_code == 200 and r.content.startswith(b"%PDF") for r in responses)
    assert state["peak"] <= 2
    assert all(name.startswith("pdf") for name in state["names"])
