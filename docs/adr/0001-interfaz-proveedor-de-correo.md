# ADR 0001 — Interfaz común de proveedores de correo (`MailProvider`)

- **Fecha:** 2026-11-20
- **Estado:** aceptada
- **Contexto de trabajo:** hackathon, en solitario, ~3 días

## Contexto
Atalaya debe vigilar el correo de organizaciones que pueden usar Gmail (Google Workspace) o Microsoft 365. Aún no se sabe cuál domina entre las personas entrevistadas (la una universidad pública usa Microsoft 365; el resto se decide por entrevistas). Además, Gmail en modo de pruebas solo admite usuarios registrados, por lo que los jueces no podrían iniciar sesión: hace falta un modo demo que funcione sin cuentas reales.

## Decisión
Toda lectura y acción sobre el correo pasa por una interfaz `MailProvider`. El núcleo (analizadores, motor de decisión, API, panel) no conoce a Gmail ni a Microsoft.

```python
class MailProvider(Protocol):
    def list_new_messages(self, since: datetime | None) -> list[MessageMeta]: ...
    def get_message(self, ref: str) -> Message: ...          # cabeceras + texto recortado
    def apply_label(self, ref: str, label: Label) -> None: ...   # Revisar | Sospechoso
    def quarantine(self, ref: str) -> None: ...                  # quitar de bandeja + etiqueta, reversible
    def release(self, ref: str) -> None: ...                     # deshacer cuarentena
    def connection_status(self) -> ConnectionStatus: ...         # connected | revoked | error
```

Implementaciones:
1. **`DemoProvider`** (primero): bandeja simulada con phishing, legítimo e inyección de prompt. Es la única disponible en el despliegue público.
2. **`GmailProvider`** (segundo): OAuth con permisos mínimos, solo local con usuarios de prueba.
3. **`MicrosoftProvider`**: solo si Gmail funciona de punta a punta (corte: sábado 12:00, hora de Panamá).

Reglas que la interfaz impone:
- No existe operación de borrar ni de enviar correos.
- `Message` lleva el contenido solo en memoria; el almacén guarda veredicto, señales, hash de referencia y estado, nunca cuerpos ni adjuntos.
- Selección del proveedor por la variable `ATALAYA_MODE` (`demo` | `gmail`).

## Contrato de API (primera versión)
`GET /api/alerts` · `GET /api/alerts/{id}` · `POST /api/alerts/{id}/approve|reject|legit` · `GET /api/coverage` · `POST /api/demo/reset` · `GET /auth/google/login` · `GET /auth/google/callback` · `POST /auth/disconnect`

Alerta: `id`, `message_ref` (hash), `received_at`, `sender_domain`, `risk` (`low|medium|high`), `signals[]`, `explanation`, `status` (`new|labeled|pending_approval|quarantined|dismissed`), `actions[]`.

## Alternativas consideradas
- **Integrar solo Gmail, sin interfaz:** más rápido hoy, pero cierra la puerta a Microsoft y obliga a reescribir el núcleo; además no habría modo demo limpio.
- **Integrar ambos desde el inicio:** demasiado alcance para 3 días en solitario.
- **Servicio de terceros que unifique correo:** introduce otro proveedor con acceso al correo; peor para privacidad.

## Consecuencias
- (+) El modo demo y las pruebas automáticas usan la misma ruta que Gmail, así que lo que se demuestra es el flujo real.
- (+) Añadir Microsoft es una implementación nueva, sin tocar el núcleo.
- (−) Un poco más de estructura inicial (aceptable: es una sola interfaz pequeña).
- (−) La interfaz debe mantenerse mínima; si Microsoft necesita algo distinto, se revisa este ADR.

## Seguimiento
Revisar al terminar el recorrido de punta a punta (viernes noche) y en el corte de Microsoft (sábado 12:00).
