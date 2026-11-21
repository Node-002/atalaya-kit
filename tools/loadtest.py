"""Prueba de carga de la demo de Atalaya. SOLO contra 127.0.0.1 (nunca contra el servicio publico).

Arranque del servidor como lo hace la imagen:
    ATALAYA_MODE=demo ATALAYA_TRUSTED_HOPS=1 python -m uvicorn app.main:app \
        --host 127.0.0.1 --port 8070 --no-proxy-headers --no-server-header

Uso:
    python tools/loadtest.py --visitors 50 --ips distinct --pid <pid del servidor>
    python tools/loadtest.py --visitors 50 --ips single

Cada visitante recorre: pagina y estaticos, alertas, campanas, aislar campana, PDF de la
organizacion, PDF de un correo, reiniciar y cambiar a supervisor. Mide latencia por paso
(p50/p95/p99), errores, respuestas 429 y, con --pid, memoria (RSS) y CPU del servidor.
Con --ips distinct simula la cabecera que anade un proxy (`X-Forwarded-For: <falsa>, <ip>`);
la app toma la entrada numero N desde la derecha, asi que la falsa no cuenta.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from collections import defaultdict

import httpx

_HOSTS_OK = ("127.0.0.1", "localhost", "[::1]")


def pct(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    return s[min(len(s) - 1, round(q * (len(s) - 1)))]


class Recorder:
    def __init__(self) -> None:
        self.lat: dict[str, list[float]] = defaultdict(list)
        self.status: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self.errors: dict[str, int] = defaultdict(int)  # tipo de fallo de red -> cuantos

    def add(self, step: str, seconds: float, code: int) -> None:
        self.lat[step].append(seconds * 1000)
        self.status[step][code] += 1


async def sample_process(pid: int, stop: asyncio.Event, out: dict) -> None:
    import psutil

    proc = psutil.Process(pid)
    proc.cpu_percent(None)
    peak = 0
    cpus: list[float] = []
    while not stop.is_set():
        try:
            peak = max(peak, proc.memory_info().rss)
            cpus.append(proc.cpu_percent(None))
        except psutil.Error:
            break
        try:
            await asyncio.wait_for(stop.wait(), 0.25)
        except TimeoutError:
            pass
    out["rss_peak_mb"] = peak / 1e6
    out["cpu_avg"] = statistics.fmean(cpus) if cpus else 0.0
    out["cpu_max"] = max(cpus) if cpus else 0.0


async def visitor(n: int, base: str, ips: str, rec: Recorder, gate: asyncio.Event, think: float):
    headers = {"X-Requested-With": "atalaya"}
    if ips == "distinct":
        ip = f"10.{(n >> 16) & 255}.{(n >> 8) & 255}.{n & 255}"
        headers["X-Forwarded-For"] = f"6.6.6.6, {ip}"  # la falsa va a la izquierda
    else:
        headers["X-Forwarded-For"] = "6.6.6.6, 10.9.9.9"
    async with httpx.AsyncClient(base_url=base, headers=headers, timeout=120) as c:

        async def step(name: str, method: str, url: str, **kw) -> httpx.Response | None:
            t = time.perf_counter()
            try:
                r = await c.request(method, url, **kw)
            except httpx.HTTPError as exc:
                rec.errors[type(exc).__name__] += 1
                rec.add(name, time.perf_counter() - t, 0)
                return None
            rec.add(name, time.perf_counter() - t, r.status_code)
            return r

        await gate.wait()
        await step("GET /", "GET", "/")
        for f in ("app.js", "style.css", "favicon.svg"):
            await step("GET /static/*", "GET", f"/static/{f}")
        alerts = await step("GET /api/alerts", "GET", "/api/alerts")
        camps = await step("GET /api/campaigns", "GET", "/api/campaigns")
        await asyncio.sleep(think)
        al = alerts.json() if alerts is not None and alerts.status_code == 200 else []
        cs = camps.json() if camps is not None and camps.status_code == 200 else []
        if cs:
            await step(
                "POST quarantine",
                "POST",
                f"/api/campaigns/{cs[0]['id']}/quarantine",
                json={"reason": "prueba de carga"},
            )
        await step("GET org PDF", "GET", "/api/org-report?formato=pdf")
        if al:
            await step("GET alert PDF", "GET", f"/api/alerts/{al[0]['id']}/report?formato=pdf")
        await step("POST reset", "POST", "/api/demo/reset")
        await step("POST role", "POST", "/api/demo/role", json={"role": "supervisor"})
        await step("GET alerts (sup.)", "GET", "/api/alerts")


def _write_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1)


async def run(args) -> int:
    rec = Recorder()
    gate = asyncio.Event()
    stats: dict = {}
    stop = asyncio.Event()
    sampler = None
    if args.pid:
        sampler = asyncio.create_task(sample_process(args.pid, stop, stats))
    tasks = [
        asyncio.create_task(visitor(i + args.offset, args.base, args.ips, rec, gate, args.think))
        for i in range(args.visitors)
    ]
    await asyncio.sleep(0.5)
    t0 = time.perf_counter()
    gate.set()
    await asyncio.gather(*tasks)
    wall = time.perf_counter() - t0
    stop.set()
    if sampler:
        await sampler

    total = sum(len(v) for v in rec.lat.values())
    codes: dict[int, int] = defaultdict(int)
    for per in rec.status.values():
        for k, v in per.items():
            codes[k] += v
    print(f"\n== {args.visitors} visitantes, ips={args.ips}, {wall:.1f}s, {total} solicitudes ==")
    print(f"{'paso':20} {'n':>5} {'p50':>8} {'p95':>8} {'p99':>8} {'max':>8}  codigos")
    for name, v in rec.lat.items():
        cod = " ".join(f"{k}:{n}" for k, n in sorted(rec.status[name].items()))
        print(
            f"{name:20} {len(v):5} {pct(v, .5):8.0f} {pct(v, .95):8.0f} "
            f"{pct(v, .99):8.0f} {max(v):8.0f}  {cod}"
        )
    errs = sum(n for k, n in codes.items() if k == 0 or k >= 500)
    print(f"codigos: {dict(sorted(codes.items()))}  errores(0/5xx)={errs}  429={codes.get(429, 0)}")
    if rec.errors:
        print(f"fallos de red: {dict(rec.errors)}")
    if stats:
        print(
            f"servidor: RSS pico {stats['rss_peak_mb']:.0f} MB, "
            f"CPU media {stats['cpu_avg']:.0f}% (max {stats['cpu_max']:.0f}%)"
        )
    if args.json:
        data = {
            "visitors": args.visitors,
            "ips": args.ips,
            "wall": wall,
            "codes": codes,
            "stats": stats,
            "steps": {
                k: {
                    "n": len(v),
                    "p50": pct(v, 0.5),
                    "p95": pct(v, 0.95),
                    "p99": pct(v, 0.99),
                    "status": dict(rec.status[k]),
                }
                for k, v in rec.lat.items()
            },
        }
        await asyncio.to_thread(_write_json, args.json, data)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default="http://127.0.0.1:8070")
    ap.add_argument("--visitors", type=int, default=10)
    ap.add_argument("--ips", choices=("distinct", "single"), default="distinct")
    ap.add_argument("--pid", type=int, default=0, help="PID del servidor (memoria y CPU)")
    ap.add_argument("--offset", type=int, default=0, help="desplaza las IPs simuladas")
    ap.add_argument("--think", type=float, default=0.0, help="pausa del visitante (s)")
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    host = httpx.URL(args.base).host
    if host not in _HOSTS_OK and f"[{host}]" not in _HOSTS_OK:
        print("Solo se permite 127.0.0.1 / localhost.", file=sys.stderr)
        return 2
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
