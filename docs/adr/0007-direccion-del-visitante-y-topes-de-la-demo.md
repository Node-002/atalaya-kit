# ADR 0007 — Dirección del visitante resistente a falsificación y topes de la demo pública

- **Fecha:** 2026-11-21
- **Estado:** aceptada. Modifica los puntos 2 y 3 del ADR 0006.

## Contexto
La prueba de intrusión de la demo (`docs/INFORME_PENTEST_DEMO_21_NOV.md`) encontró que la imagen arrancaba `uvicorn --proxy-headers --forwarded-allow-ips='*'`. Con `'*'`, uvicorn cree la **primera** entrada de `X-Forwarded-For`, que escribe el propio cliente. Resultado: con una cabecera falsa distinta en cada petición, 60 visitas nuevas pasaron de golpe (el límite es 20 por minuto), y lo mismo con las escrituras. Además, aun sin falsificar, una sola dirección podía renovar las 200 copias en ~10 minutos (20 visitas/min) y echar a los demás visitantes con la política «descartar la menos usada».

## Decisión
1. **La dirección se calcula en `app/demo_sessions.py` (`client_ip`), no en uvicorn.** La imagen arranca con `--no-proxy-headers`. Con `ATALAYA_TRUSTED_HOPS=N` (la imagen fija 1) se toma la entrada número N contando **desde la derecha** de `X-Forwarded-For` (la que agrega nuestro proxy; lo anterior lo escribió el cliente). Con 0 (valor por defecto, ejecución local) se ignora la cabecera. Si no es una IP válida se usa la del socket. IPv6 se agrupa por /64.
2. **Defensa en profundidad** (por si el número de saltos de Render/Railway no es el supuesto):
   - límite de escrituras **también por cookie** (120/min por copia);
   - tope **global** de visitas nuevas por minuto (300, `ATALAYA_DEMO_GLOBAL_NEW_PER_MIN`);
   - máximo de copias por dirección (10, `ATALAYA_DEMO_MAX_PER_IP`): al pasarlo pierde las suyas más viejas;
   - cuando se llena (200), se descarta la copia más antigua **de quien más copias tiene**, no la de un desconocido: un inundador solo se desaloja a sí mismo.
3. **Topes de tamaño:** cuerpo máximo 16 KB (`ATALAYA_DEMO_MAX_BODY`, `413`; también se rechaza `Transfer-Encoding`, que la app nunca usa), 50 invitaciones por copia, y «Reiniciar demostración» vacía invitaciones y registro de la copia. Cabeceras: las limita el analizador HTTP (httptools, ~80 KB; probado: 40 KB de cabecera o cookie se atienden sin error). La opción `--h11-max-incomplete-event-size` no aplica con `uvicorn[standard]`.
4. Crear una copia se hace fuera del bucle de eventos (`asyncio.to_thread`) para que una avalancha no congele a los visitantes existentes.

## Consecuencias
- Si en Render hay **más de un salto propio** delante (p. ej. Cloudflare + balanceador), `ATALAYA_TRUSTED_HOPS=1` daría la dirección del salto intermedio, compartida por muchos visitantes; los límites por dirección serían más estrictos de lo debido, no más laxos. Se ajusta con la variable sin tocar código. No se pudo comprobar contra Render (no se prueba contra la nube).
- Una oficina con una sola dirección puede tener hasta 10 copias vivas (generoso para un jurado).
- Un atacante distribuido (muchas IP reales) sigue limitado por el tope global de 300 visitas nuevas/min y por los 200 de memoria (~100 MB medidos: 0,5 MB por copia), pero puede, en teoría, hacer que visitantes legítimos reciban `429` mientras dure el ataque. Se acepta: es una demo gratuita; un WAF o CDN sería lo siguiente.
