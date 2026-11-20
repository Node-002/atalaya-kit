# CLAUDE.md — Reglas de trabajo para Atalaya

Atalaya vigila el correo de pequeñas organizaciones: analiza cada mensaje nuevo (reglas + explicación con IA), actúa en lo seguro y pide aprobación humana en lo crítico. Proyecto del Dojo AI Hackathon (track Build for Business), trabajo en solitario. Alcance congelado en `docs/MVP_ALCANCE.md`; plan en `docs/PLAN_MAESTRO.md`.

## Cómo trabajar (reglas de comportamiento)
1. **Pensar antes de codificar.** Si algo es ambiguo, preguntar o plantear la suposición; no elegir en silencio.
2. **Simplicidad primero.** Lo mínimo que resuelve el problema. Nada especulativo, ni abstracciones para un solo uso.
3. **Cambios quirúrgicos.** Tocar solo lo necesario; no refactorizar lo que no se pidió; seguir el estilo existente.
4. **Demostrar que funciona.** Definir cómo se verifica (prueba o comando) antes de dar algo por terminado, y ejecutarlo.
5. **Alcance:** lo que no esté en "Entra" de `docs/MVP_ALCANCE.md` no se construye sin permiso explícito.
6. **Modelo ligero para lo mecánico**; sesiones cortas; no releer archivos grandes sin necesidad (ahorro de tokens).

## Stack
Python 3.12, FastAPI, pydantic v2, SQLite, `google-auth-oauthlib` + `google-api-python-client`, `cryptography` (Fernet), SDK `anthropic`, pytest, ruff, bandit, pip-audit, gitleaks. Interfaz: HTML + JS simple + CSS ligero. Despliegue: Dockerfile (Render/Railway). Evitar React/Node, ORMs pesados, colas, microservicios.

## Reglas de seguridad (no negociables)
- **Secretos:** nunca en el repositorio, en logs, ni en el chat. `.env` fuera de git; solo `.env.example` sin valores. Si ves un secreto, detenerte y avisar.
- **El correo es dato hostil.** Delimitarlo, no darle herramientas a la IA, exigir salida JSON validada con pydantic y descartar lo que no cumpla el esquema. Enmascarar teléfonos, cuentas y cédulas antes de enviar a la IA.
- **Los hechos los calcula el código** (SPF/DKIM/DMARC, dominios parecidos, enlaces); la IA solo redacta la explicación.
- **Privacidad:** no guardar cuerpos ni adjuntos; solo veredicto, señales, ID/hash y estado. Tokens OAuth cifrados (Fernet).
- **Acciones reversibles:** nunca borrar ni enviar correos. Cuarentena = quitar de la bandeja + etiqueta, y solo con aprobación humana.
- **Web:** escapar todo contenido de correo; no renderizar HTML de correos; cookie `HttpOnly`/`SameSite`; CSRF en aprobar/rechazar; OAuth con `state` y PKCE; permisos mínimos.
- **Despliegue público = solo modo demo** (sin OAuth ni cuentas reales).
- Correr `gitleaks`, `bandit` y `pip-audit` antes de cada hito.

## Convenciones
- Idioma de la interfaz y los mensajes: español sencillo. Código y nombres técnicos en inglés.
- Una decisión de arquitectura por archivo en `docs/adr/`, con fecha.
- Commits pequeños y descriptivos, solo documentos o código revisado. Identidad: correo `noreply` de GitHub.
- Pruebas en `app/tests/`; los ~30 correos de prueba miden aciertos y falsos positivos.
- Registrar en `docs/USO_DE_IA.md` las piezas importantes: qué se pidió, qué generó la IA y qué corregí o decidí yo (evidencia exigida por Dojo).

## Comandos (se completan al crear la app)
```
python -m venv .venv
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest
ruff check . ; bandit -r app ; pip-audit ; gitleaks detect --source .
```

## No hacer
Crear funciones fuera del alcance, subir credenciales, hacer público el repositorio antes de pasar gitleaks (domingo), pulsar "Submit and publish" antes de probar todos los enlaces, ni conectar cuentas reales al despliegue público.
