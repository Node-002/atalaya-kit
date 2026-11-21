# Informe de carga de la demo y cuelgue de las pruebas — 21 nov 2026

Todo medido en local (127.0.0.1, puertos 8070/8071; nunca contra Render), en un Windows de 8 núcleos compartido con otras sesiones de trabajo, así que hay ruido. Servidor arrancado como la imagen: `ATALAYA_MODE=demo ATALAYA_TRUSTED_HOPS=1 uvicorn ... --no-proxy-headers --no-server-header`. Cliente: `tools/loadtest.py` (cada visitante: `/`, 3 estáticos, alertas, campañas, aislar campaña, PDF de organización, PDF de un correo, reiniciar, cambiar a supervisor, alertas).

## A. Carga

### Latencia (ms, p50 / p95), IP distintas, 12 solicitudes por visitante, todos a la vez
| Paso | 10 | 50 | 100 | 200 |
|---|---|---|---|---|
| `GET /` (crea la copia) | 1055 / 1336 | 1100 / 4900 | 3992 / 4167 | 7717 / 25645 |
| `/api/alerts` | 56 / 450 | 77 / 128 | 237 / 254 | 481 / 5416 |
| `/api/campaigns` | 59 / 149 | 91 / 177 | 227 / 268 | 1325 / 3645 |
| PDF de organización | 392 / 691 | 1536 / 1715 | 3365 / 3688 | 4519 / 6522 |
| PDF de un correo | 306 / 625 | 1390 / 1664 | 2606 / 3388 | 3061 / 6103 |
| reiniciar | 123 / 444 | 655 / 1633 | 1740 / 2400 | 2358 / 4463 |

Las cifras de cada columna salen de una sola corrida limpia; repetir da variaciones grandes por el ruido del equipo. Un visitante solo: la primera página tarda 205 ms, el resto 3–50 ms; una visita completa ≈ 0,33 s.

Errores: 0 en 10 y 50 visitantes (una corrida de 50 y otra de 100 con otras sesiones activas dieron 7 y 43 fallos de red, ver abajo) y 0 en 250. A 200 simultáneos hubo 42–78 fallos de red de ~2400 (`ConnectError`, `RemoteProtocolError`) y ninguna respuesta 5xx. Con 250 visitantes: 300 respuestas 429 (50 visitantes echados por el tope de 200 copias volvieron a pedir copia y chocaron con el límite global de 300 altas por minuto).

### Una sola dirección
Con 200 visitantes desde la misma IP se atienden 20 altas (límite por dirección) y el resto recibe 429: 1347 de 2020 solicitudes. Es el comportamiento diseñado (ADR 0007). Aviso: una oficina o aula tras un solo NAT comparte ese límite de 20 altas por minuto y 10 copias.

### Memoria y CPU
| Situación | RSS | CPU |
|---|---|---|
| Reposo | 69–70 MB | ~0 |
| 10 visitantes | 80 MB | media 106 %, pico 264 % |
| 100 visitantes | 132–145 MB | media 50–150 % |
| 200 visitantes | 190–210 MB | media ~100 % |
| 250 visitantes (tope 200, desalojo) | 244 MB pico | media 95 % |

- ≈ 0,6 MB por copia (0,49 MB medido en proceso). Reiniciar la demo 300 veces seguidas: RSS 67,6 → 67,7 MB, **sin fuga**.
- Un PDF de organización cuesta ~40 ms de CPU y menos de 1 MB de memoria de Python; no crece con el número de alertas (el documento se queda en 6 KB con 5, 200 o 1000 alertas). 100 PDF simultáneos subieron el RSS ~12 MB.

### Capacidad estimada con 512 MB
- Memoria: 70 + 0,6 × 200 ≈ 190–250 MB. El tope de 200 copias cabe con holgura (el límite de RAM estaría en ~500 copias). No hace falta bajarlo por memoria.
- El límite real es la **CPU de un solo núcleo** (GIL): ~50 solicitudes por segundo en este equipo (una visita completa ≈ 0,25 s de CPU). Render gratuito da una fracción de núcleo: espere de 5 a 10 veces menos (extrapolación, no medida).
- Con 50 visitantes en ráfaga la latencia p95 fue ≈ 2 s; con 100, ≈ 4 s; con 200 o más se degrada (p95 de 5 a 25 s). Son ráfagas extremas sin pausa; personas reales esperan decenas de segundos entre pasos.
- Conclusión: decenas de visitantes activos a la vez van bien; no se cae por memoria hasta el tope de copias; por encima de ~100 en ráfaga va lento, no falla.

### PDF bajo concurrencia
Los endpoints eran síncronos (40 hilos a la vez). ReportLab es Python puro y retiene el GIL: con 100 PDF simultáneos `/health` (medido desde un proceso aparte) tardaba 1–3,7 s y una corrida terminó con `ReadError`.
**Corrección:** la generación del PDF va a un grupo propio de 2 hilos (`_PDF_POOL` en `app/main.py`; los dos endpoints de informe pasan a `async`). Con 100 PDF a la vez: 100 respuestas 200 sin errores. El tiempo total fue de 3–9 s (con ruido) frente a 7,7–10,5 s. `/health` siguió con picos de 1,2–3,5 s en ambos casos: el arreglo evita acaparar el grupo de hilos y reduce la contención, pero **no elimina** el estancamiento del bucle bajo ráfagas (GIL con una sola CPU).
Probado y no aplicado: `sys.setswitchinterval(0.001)` (p50 de `/health` de ~13 a ~3–5 ms, resultados ruidosos) y limitar el grupo de hilos de anyio a 6 (PDF p50 de 8,3 s a 0,6 s, pero el p95 de alertas empeoró a 3,6 s).
Prueba añadida: `app/tests/test_pdf_concurrency.py` (como máximo 2 PDF a la vez y fuera del grupo por defecto).

### Otros hallazgos (no corregidos)
- Las lecturas (`GET`) no tienen límite por dirección: cualquiera puede pedir PDF en ráfaga (~40 ms de CPU cada uno). Recomendado: límite de PDF por dirección.
- Alta de copia: `create_app` tarda 25 ms; bajo ráfaga de 200 el primer `GET /` tarda 8–14 s por cola de CPU, no por fuga.

## B. Cuelgue intermitente de pytest en Windows

**Conclusión: es del entorno (la red de loopback de Windows), no de nuestro código.** Evidencia:
1. Sin importar nada nuestro, `asyncio.new_event_loop()` tardó hasta 16 s (3000 intentos) y `socket.socketpair()` suelto tuvo paradas de 1, 2, 4, 8 y 16 s en rachas (1722 pares en 42 s con paradas de 2–8 s; otra racha: 14 pares en 40 s). Los tiempos 1-2-4-8-16 s son la espera doble de reintento de SYN de TCP: la conexión por loopback con la que Python emula `socketpair` en Windows pierde SYN de forma intermitente. Conexiones loopback normales a un `listen` fijo también mostraron paradas de 1–4 s en rachas, y `::1` fue lento. Sospechosos: Npcap, Proton VPN, antivirus; no identifiqué cuál (no toqué controladores).
2. Cada petición de `TestClient` sin `with` crea un bucle de eventos nuevo (y por tanto un `socketpair`): miles por ejecución. Coincide con el síntoma de `py-spy` (hilo principal en `BlockingPortal.call`, bucle inactivo en `IocpProactor._poll`).
3. Ningún bloqueo en nuestro código: la demo bajo carga (miles de solicitudes con `to_thread`, `threading.Lock`, `BaseHTTPMiddleware` y SQLite en memoria) nunca se colgó.
4. Una ejecución completa con el comportamiento original y `pytest-timeout` a 120 s se colgó hasta el límite (3 min 15 s); la misma suite con bucle compartido pasó 433 pruebas en 46 s.

**Arreglo aplicado** (`app/tests/conftest.py`, solo Windows; `ATALAYA_PORTAL_PER_REQUEST=1` lo desactiva): las pruebas sin `with` comparten un solo bucle por ejecución (un `socketpair` en vez de miles). Comparación A/B posterior, 4 ejecuciones completas por modo: ninguna se colgó (compartido: 80, 58, 46, 50 s; por petición: 72, 51, 69, 45 s). **No pude demostrar estadísticamente la mejora**: la parada es episódica y en esas 8 ejecuciones no apareció. El cambio es seguro (434 pruebas pasan) y reduce la exposición de miles de `socketpair` a uno.
Descartado: `WindowsSelectorEventLoopPolicy` también crea un `socketpair`, así que no evita la causa (un benchmark de 3000 bucles con esa política se quedó colgado más de 5 minutos). Un `socketpair` propio que reintenta el SYN cada 0,25 s no ayudó en las rachas largas (llegó a 21 s): en esas rachas caen todos los SYN.
Si vuelve a colgarse: cerrar herramientas de captura de red (Npcap) y probar sin VPN; `pytest-timeout` acota el daño.

## Lo que no pude verificar
- Rendimiento real en Render (CPU fraccionaria, red real): solo extrapolación.
- Los fallos de red a 200 simultáneos pueden ser del cliente o del Proactor de Windows (cierre de conexiones inactivas a 5 s, cola de aceptación), no de la app; en Linux no se midió.
- Qué controlador causa el SYN perdido, y si el bucle compartido elimina por completo los cuelgues.
- El cliente corre en la misma máquina y compite por CPU con el servidor: las latencias son pesimistas.
