# Instalar Atalaya en tu organización (kit autoalojado)

> English version: [INSTALLATION.en.md](INSTALLATION.en.md). Los mensajes de arranque del kit y del verificador salen en inglés con `ATALAYA_LANG=en`.

> **Estado honesto.** Esta guía se escribió leyendo la documentación oficial de Google y probando el kit **solo en Python** (pruebas automáticas y un arranque local con datos falsos). **No se ha probado con una organización de Google Workspace real, ni con Docker en un servidor real, ni con Google Cloud.** Los pasos de Google Cloud siguen la documentación pública a 21 nov 2026; si tu pantalla se ve distinta, la interfaz cambió: sigue el sentido del paso y avísanos. Lo que no se pudo confirmar está marcado con ⚠️ y listado en la [sección 10](#10-lo-que-no-está-verificado).

## 0. Qué es esto y qué te llevas

Atalaya vigila el correo de tu organización y pide aprobación humana antes de actuar (nunca borra ni envía correos). En el **kit autoalojado** *tú* instalas tu propia copia en *tu* servidor, con *tu* aplicación de Google y *tus* claves. **Nosotros nunca vemos tus correos, tus tokens ni tus claves.**

Por qué así y no como servicio en la nube: [ADR 0012](adr/0012-kit-autoalojado-en-lugar-de-servicio-alojado.md).

## 1. Requisitos

| Qué | Detalle |
|---|---|
| Una cuenta de **Google Workspace** con una **organización** | Necesitas poder crear un proyecto de Google Cloud dentro de esa organización y, para el paso de «aplicación interna», permisos de administración. Con Gmail personal (`@gmail.com`) no existe el tipo «Interno»: ver el [modo de evaluación](#modo-evaluación-en-15-minutos-en-localhost). |
| Un servidor o equipo con **Docker** y **Docker Compose v2** | Linux recomendado (cualquier VPS pequeño sirve: 1 CPU y 1 GB de memoria alcanzan para decenas de buzones; cifra **no medida** en una organización real). |
| Un **dominio con HTTPS** | Para uso real: `https://atalaya.tuorganizacion.org` apuntando al servidor. El kit incluye Caddy, que consigue el certificado solo (puertos 80 y 443 abiertos). Para evaluar sin dominio: `http://localhost:8000`. |
| El reloj del servidor sincronizado (NTP) | Un reloj desfasado hizo fallar un inicio de sesión real. Linux moderno ya lo hace solo. |
| (Opcional) Una clave de Anthropic | Solo si quieres explicaciones redactadas por IA. Está **apagada** por defecto (ver sección 9). |

## Cómo instalar: dos opciones

### Opción A (recomendada): asistente guiado

El asistente `tools/kit/instalar.py` hace las preguntas, genera las claves y los archivos de configuración, arranca Docker Compose, espera a que el panel responda y ejecuta el verificador. Está pensado para que una persona de TI sin experiencia termine en unos 15 minutos. Solo usa la biblioteca estándar de Python (3.9 o superior); **no descarga nada, no instala nada por su cuenta y no envía datos a nadie** (la única red es `/health` en `127.0.0.1`).

**Antes de empezar** necesitas: Docker con Compose v2, Python 3.9+ y el **JSON del cliente OAuth de Google** (secciones 2 y 3 de esta guía; guárdalo **fuera** de la carpeta del kit, por ejemplo en Descargas). Si aún no lo tienes, el asistente te muestra la URI de redirección exacta que debes registrar y puedes repetirlo después.

```bash
tools/kit/instalar.sh            # Linux / macOS
```
```powershell
.\tools\kit\instalar.ps1        # Windows (PowerShell)
```
(o directamente `python3 tools/kit/instalar.py`). Si falta Python, el envoltorio lo explica y no descarga nada. Para inglés: `--lang en` o `ATALAYA_LANG=en`.

Qué hace, paso a paso:
1. **Comprobaciones previas:** Python, `docker` y `docker compose`, que Docker esté en marcha, permiso de escritura, espacio en disco y puertos libres (8000, y 80/443 si usas Caddy). Si falta algo, te dice qué hacer; no lo instala.
2. **Preguntas:** nombre de la organización; modo (*local* para evaluar o *producción* con dominio HTTPS) y **la URI de redirección que debes registrar en Google, resaltada**; correos de administración (y, opcional, de supervisión de solo lectura); ruta del JSON de Google (comprueba que sea de tipo *Aplicación web*, que incluya esa URI y que no esté dentro de una carpeta de repositorio); proxy (el Caddy del kit, o el tuyo y cuántos saltos hay); y la IA, **apagada por defecto** (si la activas, te avisa de que se enviará texto enmascarado a Anthropic y pide la clave sin mostrarla).
3. **Claves:** genera la clave Fernet y el secreto de sesión. **Nunca se muestran** en pantalla ni se pasan como argumentos de ningún programa. Te ofrece guardar una **copia de la clave Fernet** donde tú elijas (mejor en otro medio): sin ella, los tokens y los respaldos son ilegibles.
4. **Archivos:** escribe `.env.kit` (permisos `0600` en Linux/macOS; en Windows usa `icacls`, mejor esfuerzo), crea `secrets/` y copia allí el JSON. Si ya existe una configuración, **no la sobrescribe sin confirmación** y guarda antes una copia con fecha (`.env.kit.bak-AAAAMMDD-HHMMSS`). Con Caddy, pone tu dominio en el `Caddyfile`.
5. **Arranque:** `docker compose build` y `up -d` (con `--profile tls` si usas Caddy), espera a `/health` (hasta 2 minutos) y muestra el resumen: URL, administración, dónde están los respaldos y los comandos de `tools/kit/respaldo.sh`, y los siguientes pasos.
6. **Verificación:** ejecuta `tools/kit/verificar_instalacion.py` y muestra su resultado (el verificador necesita Python 3.11+; con una versión anterior, el asistente lo avisa y lo omite).

Banderas útiles: `--sin-arranque` (solo genera la configuración), `--verificar` (solo verifica una instalación hecha), `--si` (no pregunta nada: usa las banderas `--org --modo --dominio --admin --supervisores --google-json --proxy --saltos --copia-clave` o sus variables de entorno; sirve para automatizar), `--sobrescribir`, `--dir`, `--lang`, `--version`, `--ayuda`. La clave de Anthropic solo se acepta por la variable `ANTHROPIC_API_KEY`, nunca como bandera (los argumentos quedan en el historial y en la lista de procesos). Cualquier fallo termina con código distinto de cero y un mensaje claro, sin trazas de Python.

Sesión de ejemplo (datos ficticios; resumida):

```text
Asistente de instalacion de Atalaya 1.0.0
[1/6] Comprobaciones previas
  OK    Python 3.12
  OK    Docker version 27.x ...
  OK    Docker Compose version v2.x ...
  OK    Espacio en disco: 40 GB libres
  OK    Puerto 8000 libre
[2/6] Preguntas
  Nombre de la organizacion: Mi Organizacion
  Modo (local/produccion/production) [local]: local
  Registra EXACTAMENTE esta URI de redireccion en tu cliente OAuth de Google:
    >>> http://localhost:8000/auth/google/callback <<<
  Correo(s) de administracion, separados por comas: admin@example.org
  Ruta del JSON de credenciales de Google (tipo Aplicacion web): ~/Descargas/client_secret_demo.json
  OK    JSON de Google valido (tipo web, URI de redireccion incluida)
  Activar la explicacion con IA? [s/N]: n
[3/6] Claves y archivos
  OK    Claves generadas (no se muestran)
  OK    .env.kit escrito con permisos restringidos
  Guardar ahora una copia de la clave en una ruta que elijas? [S/n]: s
  Ruta del archivo de copia (de preferencia en otro medio): /media/usb/atalaya-clave.txt
[4/6] Arranque con Docker Compose
  OK    Imagen construida
  OK    Contenedores en marcha
  OK    /health responde (modo gmail)
[5/6] Verificacion de la instalacion
  OK    ... (salida del verificador)
[6/6] Resumen
  Direccion del panel : http://localhost:8000
  Siguientes pasos: abre el panel, inicia sesion y crea la primera invitacion.
Listo.
```

> **Estado honesto.** El asistente se probó con pruebas automáticas y un `docker` **falso** (orquestación, validaciones, que ningún secreto salga por pantalla ni por argumentos, permisos, copia de respaldo). **No se ejecutó contra Docker real ni con una organización de Google Workspace**; el trabajo `kit` del CI lo ejercita con Docker real al subir. Decisiones de diseño: [ADR 0014](adr/0014-asistente-de-instalacion-guiado.md).

### Opción B: manual

Las secciones siguientes (modo evaluación y secciones 2 a 6) son el procedimiento manual completo; sirven también para entender qué automatiza el asistente.

## Modo evaluación en 15 minutos en localhost

Sin dominio y sin servidor: en tu propio equipo con Docker.

1. **Obtén el kit** (descarga el repositorio) y abre una terminal en esa carpeta.
2. **Cliente de Google.** Haz los pasos 3 a 6 de la [sección 2](#2-crear-la-aplicación-de-google-una-vez), con esta diferencia: en la URI de redirección pon `http://localhost:8000/auth/google/callback` (Google permite `http` solo para `localhost`). Si no tienes una organización Workspace, en el paso de público elige **Externo** (modo de pruebas) y agrega tu cuenta como **usuario de prueba**: funciona con Gmail personal, con un tope de 100 usuarios de prueba y autorizaciones que Google **caduca a los 7 días** (dato de nuestras notas previas, ⚠️ confirma en la pantalla «Público»).
3. Guarda el JSON como `secrets/google_client.json` (crea la carpeta `secrets`).
4. Copia `.env.kit.example` a `.env.kit` y cambia: `ATALAYA_BASE_URL=http://localhost:8000`, la clave Fernet, la clave de sesión y `ATALAYA_ADMIN_EMAILS` (sección 4 explica cómo generarlas). Deja `ATALAYA_TRUST_PROXY=0`.
5. `docker compose up -d --build`
6. `python3 tools/kit/verificar_instalacion.py --env-file .env.kit` → todo en `OK` (el aviso de `http://localhost` es normal).
7. Abre **`http://localhost:8000`** (escribe `localhost`, **no** `127.0.0.1`: la app y Google solo aceptan `localhost`). Debes ver la pantalla de inicio de sesión.

Cuando termines: `docker compose down -v` (borra todo, incluidos los datos).

## 2. Crear la aplicación de Google (una vez)

Esto lo hace una persona administradora de Google Workspace de la organización. Las rutas de menú son las que muestra la documentación oficial de Google (fuentes en la [sección 11](#11-fuentes)).

1. **Crear un proyecto.** Entra a [console.cloud.google.com](https://console.cloud.google.com) con tu cuenta de Workspace. Menú **IAM y administración → Crear un proyecto** (en inglés: *IAM & Admin > Create a Project*). Ponle un nombre (por ejemplo «Atalaya») y, en **Ubicación**, elige **tu organización** (no «Sin organización»). *Verás:* el proyecto creado y seleccionado arriba.
2. **Habilitar la API de Gmail.** Menú **APIs y servicios → Biblioteca** (*APIs & Services > Library*), busca «Gmail API» y pulsa **Habilitar** (*Enable*). Equivale a `gcloud services enable gmail.googleapis.com`.
3. **Configurar Google Auth Platform.** La pantalla de consentimiento hoy vive en **Google Auth Platform**, con las secciones **Overview, Branding, Audience, Clients, Data Access** y **Verification Center**. Pulsa **Get started** en *Overview*, completa el nombre de la aplicación y un correo de contacto.
4. **Público (Audience) = Interno.** En *Audience* elige el tipo de usuario **Interno** (*Internal*): limita la autorización a las cuentas de tu organización. Si la opción **Interno** no aparece, el proyecto no pertenece a una organización: vuelve al paso 1. Con «Interno» la documentación de Google dice que **no hace falta verificación** de la aplicación y **no hay lista de usuarios de prueba** (tabla de *production readiness*).
5. **Alcances (Data Access).** Si la pantalla te lo pide, agrega: `https://www.googleapis.com/auth/gmail.modify` (leer y etiquetar; Atalaya **no envía ni borra**, y el código no incluye esas operaciones) y, para el inicio de sesión del panel, `openid` y `.../auth/userinfo.email`. Google clasifica `gmail.modify` como **«restringido»**. ⚠️ Para una aplicación interna no pudimos confirmar en las páginas oficiales leídas si queda exenta de la verificación de alcances restringidos y de la evaluación de seguridad: lo que sí se leyó es que *«Interno: verificación no requerida»*. Una vista previa de resultados de búsqueda de Google dice que los alcances restringidos en apps de uso interno «no requieren más revisión», pero no la leímos en la página completa.
6. **Crear el cliente OAuth (Clients).** En *Clients* → **Create Client** → tipo de aplicación **Web application** (Aplicación web). En **URIs de redireccionamiento autorizados** agrega **exactamente**:
   `https://atalaya.tuorganizacion.org/auth/google/callback`
   (tu dominio real). Debe empezar por `https://`; la única excepción es `http://localhost…` para evaluar. **Es una sola URI**: sirve para el inicio de sesión del panel y para conectar buzones. Cualquier diferencia (`http`/`https`, mayúsculas, barra final) da `redirect_uri_mismatch`.
7. **Descarga el JSON** del cliente (botón de descarga junto al cliente) y guárdalo en el servidor como `secrets/google_client.json`. **Es un secreto**: no lo subas a ningún repositorio ni lo mandes por correo. Debe poder leerlo el usuario del contenedor: `chmod 644 secrets/google_client.json` y `chmod 755 secrets`.
8. ⚠️ **Consola de administración de Google Workspace.** La página de *Audience* avisa de que los alcances restringidos de Gmail «podrían requerir configuración adicional por parte de los administradores de tu organización». Si tu organización bloquea aplicaciones de terceros, la persona administradora debe **permitir esta aplicación** (por ID de cliente) en la Consola de administración (*Seguridad → Control de acceso y datos → Controles de API*). No pudimos verificar el nombre exacto de ese menú; búscalo como «Controles de API / aplicaciones de terceros».

## 3. Preparar el servidor

1. Instala Docker y Docker Compose v2 ([docs.docker.com/engine/install](https://docs.docker.com/engine/install/)).
2. Descarga el kit (clona o descomprime el repositorio) en una carpeta, por ejemplo `/opt/atalaya`.
3. Crea el DNS: un registro A (y AAAA si usas IPv6) de `atalaya.tuorganizacion.org` hacia la IP del servidor. Abre los puertos **80 y 443** en el cortafuegos.
4. Comprueba la hora: `timedatectl` debe decir `System clock synchronized: yes`.

## 4. Claves y configuración

1. Copia el archivo de ejemplo (el real **no va al repositorio**):
   ```bash
   cp .env.kit.example .env.kit && chmod 600 .env.kit
   ```
2. Genera las dos claves (no las pegues en chats ni correos):
   ```bash
   docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(48))"
   docker run --rm python:3.12-slim sh -c "pip install -q cryptography >/dev/null 2>&1 && python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
   ```
   La primera es `ATALAYA_SESSION_SECRET`; la segunda, `ATALAYA_FERNET_KEY`.
3. **Guarda la clave Fernet aparte** (gestor de contraseñas de la organización). **Sin ella, los tokens guardados son ilegibles** y habría que volver a conectar todos los buzones. No la guardes junto a los respaldos.
4. Edita `.env.kit` y reemplaza cada `CAMBIAR_...`: `ATALAYA_BASE_URL` (tu dominio con `https://`), las dos claves y `ATALAYA_ADMIN_EMAILS` (las cuentas de Google que podrán entrar al panel, separadas por comas).
5. **Proxy** (`ATALAYA_TRUST_PROXY`): ver [la explicación](#proxy-inverso-y-limite-de-intentos).

## 5. Arrancar

1. Edita `Caddyfile` y cambia `CAMBIAR_DOMINIO` por tu dominio.
2. ```bash
   docker compose --profile tls up -d --build
   ```
   *Verás:* Docker construye la imagen (unos minutos la primera vez) y levanta `atalaya` y `caddy`.
3. Mira el registro: `docker compose logs -f atalaya`. Si falta algo, **el contenedor se niega a arrancar** y dice qué: «Atalaya (kit) NO arranca: faltan o están mal estos datos…» (ver solución de problemas).
4. En el primer arranque Caddy pide el certificado a Let's Encrypt; tarda unos segundos si el DNS ya apunta bien.

## 6. Verificar la instalación

```bash
python3 tools/kit/verificar_instalacion.py --env-file .env.kit
```
Comprueba (sin imprimir valores): variables obligatorias, `https`, que el JSON de Google sea de tipo *Aplicación web* y su URI de redirección coincida con `ATALAYA_BASE_URL`, que `/health` responda `mode: gmail`, y el desfase del reloj contra Google. Todo debe estar en `OK`; un `AVISO` no impide usar el kit, una `FALLA` sí.

Además, abre `https://atalaya.tuorganizacion.org/health`: debe mostrar `{"status":"ok","mode":"gmail","auth":true}`. Si dice `mode: demo`, estás usando la imagen de la demo pública y no la del kit.

## 7. Conectar el primer buzón

1. Abre `https://atalaya.tuorganizacion.org` → te lleva a `/login`. Elige **Iniciar sesión con Google** con una cuenta de `ATALAYA_ADMIN_EMAILS`. *Verás:* el panel vacío.
2. En el panel, crea una **invitación** (nombre del buzón y área). Te da un enlace **de un solo uso**.
3. La persona dueña del buzón (de tu organización) abre el enlace, lee el aviso de consentimiento, **autoriza con Google** y ve solo una confirmación. No ve el panel.
4. *Verás:* el buzón en el panel, y en Gmail la etiqueta «Sospechoso» cuando haya algo que revisar. Atalaya revisa la bandeja de entrada cada 60 s (los últimos 7 días al conectar).

Los buzones solo pueden ser de cuentas de tu organización (aplicación «Interna»).

## Proxy inverso y límite de intentos

El panel limita los intentos fallidos de inicio de sesión **por dirección IP**. Detrás de un proxy, la IP del cliente llega en la cabecera `X-Forwarded-For`, que el cliente puede falsear. Por eso:

| Situación | `ATALAYA_TRUST_PROXY` | Por qué |
|---|---|---|
| **Detrás de Caddy** (el perfil `tls` de este kit) | **`1`** | Caddy sobrescribe `X-Forwarded-For` con la IP real y Atalaya toma la **última** entrada, la que añadió Caddy (no la primera, que escribe el cliente). |
| Sin proxy (evaluación en `localhost`) | `0` | Con `1` y sin proxy, cualquiera podría falsear su IP y saltarse el límite. |
| Tu propio proxy (nginx, Traefik, un balanceador de la nube) | `1` solo si **siempre** añade la IP real como **última** entrada | ⚠️ Si hay **más de un salto** propio delante (por ejemplo CDN + proxy), la última entrada sería la del salto interno: el límite contaría todo como una sola IP. No hay hoy una variable para saltos múltiples en el modo kit. |

`ATALAYA_TRUSTED_HOPS` **solo afecta a la demo pública** (límites por visitante); en el kit no se usa. La imagen arranca con `--no-proxy-headers`: uvicorn no se fía de las cabeceras de proxy.

## 8. Operación

### Respaldo y restauración
```bash
tools/kit/respaldo.sh respaldos        # crea respaldos/atalaya-AAAAMMDD-HHMMSS.db (con el kit en marcha)
tools/kit/restaurar.sh respaldos/atalaya-AAAAMMDD-HHMMSS.db   # pide escribir SI; reemplaza la base actual
```
- Copia consistente de la base SQLite (API de copia de SQLite + verificación de integridad). **No incluye la clave Fernet.**
- El respaldo guarda veredictos, estados y **tokens de Google cifrados**. Para restaurar necesitas **la misma** `ATALAYA_FERNET_KEY`; con otra, los tokens no se pueden descifrar y hay que reconectar los buzones.
- Programa el respaldo (por ejemplo con `cron`) y copia los archivos a otro lugar. **No se probó restaurar en un servidor real.**

### Actualizar
```bash
tools/kit/respaldo.sh respaldos                   # 1. respaldo antes de tocar nada
git pull                                          # 2. nuevo código (o descarga la versión nueva del kit)
docker compose --profile tls up -d --build        # 3. reconstruye y reinicia (las migraciones de la base son automáticas al arrancar)
python3 tools/kit/verificar_instalacion.py --env-file .env.kit   # 4. todo en OK
docker compose logs --tail 50 atalaya             # 5. sin errores
```
Qué comprobar después: `/health` con `mode: gmail`, que puedes entrar al panel, y que el número de buzones y alertas es el de antes. Para volver atrás: `git checkout <versión anterior>`, reconstruir y, si hace falta, `restaurar.sh` con el respaldo del paso 1. (Si usas imágenes publicadas en lugar de construir, el equivalente es `docker compose pull` y `up -d`; hoy el kit se construye desde el código.)

### Dónde viven los datos
En el volumen `atalaya-data` (`/srv/data/atalaya.db` dentro del contenedor). El sistema de archivos del contenedor es de solo lectura salvo ese volumen y `/tmp`.

## 9. Qué guarda y qué no guarda

Alineado con [POLITICA_PRIVACIDAD.md](POLITICA_PRIVACIDAD.md) (borrador sin revisión legal; con el kit, **tu organización es la responsable del tratamiento**, no Atalaya):

| Guarda (en tu servidor, SQLite) | No guarda |
|---|---|
| Buzón: nombre, dirección y **token de Google cifrado (Fernet)** | **Cuerpos de correo y adjuntos** |
| Alertas (cifradas en reposo): veredicto, señales, **dominio** del remitente, hora, explicación, estado, hash/identificador del mensaje, huellas para campañas, decisiones con quién, cuándo y el motivo escrito | Asunto ni remitente completo en las alertas |
| Área de cada buzón y metadatos técnicos de cabeceras (SPF/DKIM/DMARC, IP de origen, etc., máx. 2 KB por correo, sin direcciones completas) | Contraseñas |
| Invitaciones (hash del enlace), auditoría de inicios de sesión (con IP) | |

El texto de un correo **sí pasa por la memoria del servidor** mientras se analiza; no se escribe en la base ni en los registros.

**IA (opcional, apagada por defecto):** con `ATALAYA_LLM=anthropic` y `ANTHROPIC_API_KEY`, para cada correo se **envía a un proveedor externo (Anthropic)** un texto **enmascarado**: dominio del remitente, asunto (máx. 200 caracteres), dominios de enlaces y hasta 1 500 caracteres de texto. El enmascarado es de mejor esfuerzo, **no una garantía**. Informa a las personas cuyo correo se analiza y revisa las condiciones del proveedor. Esta función **no se ha probado con una cuenta de pago real**. Sin IA, la explicación sale de plantillas y **no se envía nada fuera**.

Con el kit, Atalaya (el proyecto) no recibe nada de tu instalación: ni datos, ni métricas, ni claves.

## 10. Lo que NO está verificado

- ⚠️ **Todo el flujo con una organización Google Workspace real**: crear el proyecto, el tipo «Interno», el cliente web, el inicio de sesión y conectar buzones. No hay organización de prueba. Solo se verificó la parte de Python (arranque, comprobaciones, verificador, pruebas automáticas).
- ⚠️ Que una aplicación **interna** con `gmail.modify` (alcance restringido) quede exenta de la verificación y de la evaluación de seguridad: la tabla oficial dice «Interno: verificación no requerida», pero no se leyó una frase específica sobre alcances restringidos en la documentación completa.
- ⚠️ Si el tope de 100 usuarios se aplica a apps internas: la documentación lee «sin usuarios de prueba» para Interno, pero no lo dice con esas palabras.
- ⚠️ La regla «https obligatorio salvo localhost» para la URI de redirección: la leímos solo en un resumen, no en el texto completo de la página.
- ⚠️ El menú exacto de la Consola de administración para permitir la aplicación.
- **Docker, Compose y Caddy no se ejecutaron en el equipo de desarrollo** (no hay Docker). El trabajo `kit` del CI de GitHub los prueba al subir; hasta entonces es código sin ejecutar. Lo único ejecutado: el arranque en Python, las pruebas, `hadolint` y `actionlint`.
- Respaldo y restauración: la lógica de copia de SQLite se probó, los scripts se revisaron con `bash -n`, pero no se corrieron contra un contenedor.

## 11. Solución de problemas

| Síntoma | Causa y arreglo |
|---|---|
| El contenedor sale al arrancar con «Atalaya (kit) NO arranca…» | Faltan datos; el mensaje nombra cada variable. Corrige `.env.kit` y `docker compose up -d`. Los valores nunca se imprimen. |
| «No existe el archivo GOOGLE_CLIENT_SECRETS_FILE» / «no se puede leer» | El JSON no está en `secrets/google_client.json` o su dueño/permisos impiden leerlo al usuario 10001: `chmod 644`. No cambies `GOOGLE_CLIENT_SECRETS_FILE` (es la ruta dentro del contenedor). |
| «El JSON de Google no incluye la URI de redirección…» | La URI del cliente en Google no coincide con `ATALAYA_BASE_URL` + `/auth/google/callback`. Corrígela en *Clients*, vuelve a descargar el JSON y reinicia. |
| Error 400 `redirect_uri_mismatch` al iniciar sesión | Igual: la URI debe coincidir **carácter por carácter** (`https`, dominio, sin barra final). Los cambios en Google pueden tardar unos minutos. |
| «Acceso bloqueado: esta app no está autorizada» / `access_denied` / `admin_policy_enforced` | (a) La cuenta no es de tu organización o el público no es «Interno». (b) La administración de Workspace bloquea la app: permítela por ID de cliente (paso 8 de la sección 2). (c) En modo Externo de pruebas, la cuenta no está en la lista de usuarios de prueba. |
| `invalid_grant` | El código de autorización expiró o se usó dos veces (repite el inicio de sesión), el **reloj del servidor está desfasado** (ejecuta el verificador), el usuario revocó el acceso, o (modo Externo de pruebas) pasaron 7 días. Si todos los buzones fallan tras restaurar: la clave Fernet no coincide. |
| El inicio de sesión falla justo al volver de Google, a veces | **Reloj desfasado** (un inicio de sesión real falló una vez por 1,4 s). Activa NTP; `verificar_instalacion.py` mide el desfase. La app tolera 30 s al validar el token. |
| El panel no se guarda / «unable to open database file» / «permission denied» en `/srv/data` | El volumen no pertenece al usuario 10001. Con el volumen con nombre del compose no debería pasar; si usas una carpeta del anfitrión: `sudo chown -R 10001 /ruta/data`. |
| El inicio de sesión del panel falla o te bloquea «por demasiados intentos» detrás del proxy | Si `ATALAYA_TRUST_PROXY=0` detrás de Caddy, **todos** los intentos parecen venir de la IP de Caddy y se bloquean juntos: pon `1`. Si es `1` y **no** hay proxy, la IP se puede falsear. Reinicia tras cambiarlo. |
| Cookie/sesión: vuelve siempre a `/login` | Estás entrando por `http` o por un dominio distinto a `ATALAYA_BASE_URL`. Usa siempre la misma dirección `https`. |
| Caddy no consigue el certificado | El DNS no apunta al servidor, o 80/443 cerrados. `docker compose logs caddy`. |
| `/health` dice `mode: demo` | Estás ejecutando la imagen pública de la demo; usa `docker compose` de este kit (etapa `kit`). |

## 12. Desinstalar y revocar

1. **Desconecta cada buzón desde el panel** (revoca el token en Google y borra el registro local).
2. Cada persona puede retirar el acceso en cualquier momento desde su cuenta de Google: **Seguridad → Tus conexiones con apps de terceros → Atalaya → Quitar acceso**.
3. En Google Cloud, elimina el cliente OAuth (*Clients*) o el proyecto entero.
4. En el servidor: `docker compose --profile tls down -v` (**`-v` borra el volumen con la base de datos**: es irreversible; haz antes un respaldo si lo necesitas) y borra la carpeta del kit, `.env.kit` y `secrets/`.
5. Si la clave Fernet o el JSON de Google se filtraron, elimina el cliente en Google (invalida todo) y genera claves nuevas.

## 13. Lista de comprobación

- [ ] Proyecto de Google Cloud dentro de **mi organización**; API de Gmail habilitada.
- [ ] Público = **Interno**; cliente **Aplicación web**; URI `https://…/auth/google/callback` exacta.
- [ ] JSON en `secrets/google_client.json`, **fuera de git**.
- [ ] `.env.kit` completo, `chmod 600`, **fuera de git**; clave Fernet **guardada aparte**.
- [ ] DNS apunta al servidor; 80/443 abiertos; reloj sincronizado.
- [ ] `ATALAYA_TRUST_PROXY=1` con Caddy (0 sin proxy).
- [ ] `verificar_instalacion.py` sin `FALLA`; `/health` = `mode: gmail`, `auth: true`.
- [ ] Primer buzón conectado y alerta de prueba vista.
- [ ] Respaldo programado, copia fuera del servidor, y **restauración probada** en un entorno de prueba.
- [ ] Las personas cuyo correo se analiza están informadas (y la IA sigue apagada o tiene aviso).

## 14. Fuentes

Consultadas el 21 nov 2026 (documentación oficial; el contenido puede cambiar):
- Google Auth Platform (secciones, Internal/External/Personal): https://support.google.com/cloud/answer/15544987
- Preguntas frecuentes de verificación de OAuth: https://support.google.com/cloud/answer/13463817
- Preparación para producción (tabla Interno/Externo): https://developers.google.com/identity/protocols/oauth2/production-readiness/overview
- Alcances de la API de Gmail (`gmail.modify` = restringido): https://developers.google.com/workspace/gmail/api/auth/scopes
- Flujo para aplicaciones web y URIs de redirección: https://developers.google.com/identity/protocols/oauth2/web-server
- Crear un proyecto y habilitar APIs: https://developers.google.com/workspace/guides/create-project y https://developers.google.com/workspace/guides/enable-apis
- Caddy `reverse_proxy` y cabeceras `X-Forwarded-*`: https://caddyserver.com/docs/caddyfile/directives/reverse_proxy (según los resultados de búsqueda de esa documentación, por defecto Caddy no confía en ningún proxy e ignora el `X-Forwarded-For` que envía el cliente; **no se probó en ejecución**)
