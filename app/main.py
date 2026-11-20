"""API de Atalaya. Version del viernes: solo modo demo.

Modo 'gmail' se implementa despues; hoy se rechaza explicitamente.
"""

import os

from fastapi import FastAPI, HTTPException

from app.models import Alert, Coverage
from app.providers.base import MailProvider
from app.providers.demo import DemoProvider
from app.store import AlertStore

ADMIN = "admin-demo"  # en modo conectado vendra de la sesion autenticada


def create_app(provider: MailProvider | None = None) -> FastAPI:
    mode = os.environ.get("ATALAYA_MODE", "demo")
    if provider is None:
        if mode != "demo":
            raise RuntimeError("Solo el modo 'demo' esta implementado por ahora.")
        provider = DemoProvider()

    store = AlertStore(provider)
    store.poll()

    app = FastAPI(title="Atalaya", version="0.1.0")

    def _alert_or_404(alert_id: str) -> Alert:
        alert = store.get(alert_id)
        if alert is None:
            raise HTTPException(status_code=404, detail="Alerta no encontrada.")
        return alert

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": mode}

    @app.get("/api/alerts", response_model=list[Alert])
    def list_alerts() -> list[Alert]:
        return store.list()

    @app.get("/api/alerts/{alert_id}", response_model=Alert)
    def get_alert(alert_id: str) -> Alert:
        return _alert_or_404(alert_id)

    @app.post("/api/alerts/{alert_id}/approve", response_model=Alert)
    def approve(alert_id: str) -> Alert:
        _alert_or_404(alert_id)
        try:
            return store.approve(alert_id, ADMIN)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/alerts/{alert_id}/reject", response_model=Alert)
    def reject(alert_id: str) -> Alert:
        _alert_or_404(alert_id)
        try:
            return store.reject(alert_id, ADMIN)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/alerts/{alert_id}/legit", response_model=Alert)
    def legit(alert_id: str) -> Alert:
        _alert_or_404(alert_id)
        return store.mark_legit(alert_id, ADMIN)

    @app.get("/api/coverage", response_model=list[Coverage])
    def coverage() -> list[Coverage]:
        return [
            Coverage(
                account=provider.account_name(), status=provider.connection_status()
            )
        ]

    @app.post("/api/demo/reset")
    def demo_reset() -> dict[str, str]:
        if not isinstance(provider, DemoProvider):
            raise HTTPException(status_code=404, detail="Solo disponible en modo demo.")
        provider.reset()
        store.clear()
        store.poll()
        return {"status": "reset"}

    return app


app = create_app()
