# ADR 0011 — Área (departamento) de cada buzón

- **Fecha:** 2026-11-21
- **Estado:** aceptada (decisión del usuario: el análisis se agrupa por área, no por persona).

## Contexto
La analítica por buzón se llenaba con muchas personas. El prototipo agrupaba por departamento. Hacía falta saber a qué área pertenece cada buzón.

## Decisión
1. **Lista fija** en `app/departments.py`: Gerencia/Dirección, Finanzas, Recursos Humanos, Ventas y Compras, Operaciones y Logística, IT y Sistemas y «Sin área» (por defecto). El servidor valida con coincidencia exacta (422 si el valor no está); no hay áreas libres.
2. **Dónde vive:** columna `department` en `mailboxes` e `invites` (valor por defecto «Sin área»); migración automática y repetible (`Database._migrate`) para bases anteriores. La alerta copia el área de su buzón al analizarse (`Alert.department`) y se guarda cifrada con el resto de la alerta. Las alertas guardadas antes se muestran como «Sin área» y toman el área del buzón al cargarse.
3. **Quién la asigna:** la administración, al crear la invitación (`POST /api/invites` con `department`) y después con `PATCH /api/mailboxes/{id}/department`. El supervisor recibe 403 (filtro de roles del servidor), hace falta el encabezado anti-CSRF, un buzón desconocido da 404 y cada cambio queda en la auditoría (`mailbox_department_changed`). La página de invitación puede decir «Tu administración te asignó al área X» (texto con `textContent`).
4. **Privacidad:** el área es un dato de la **organización** (a qué área pertenece un buzón), no del correo: no se guarda nada nuevo de los mensajes. No hay datos personales nuevos más allá de la etiqueta del buzón que ya existía.
5. **Analítica:** se agrupa por área (tarjetas y tabla comparativa) con conteos de las alertas guardadas; el directorio «Usuarios Conectados» sigue siendo por persona. Filtro global por área en la cabecera (Panel, Analítica y Usuarios). El informe PDF de la organización pasa de «Estado por buzón» a «Estado por área»; el CSV del historial lleva la columna `area`.
6. **Demo:** 14 empleados en las 6 áreas (los 3 de antes más 11), 57 correos en 7 días, todo determinista; la campaña del phishing bancario sigue siendo de 2 buzones (los demás remitentes son únicos).

## Consecuencias / riesgos
- La demo crece: de ≈0,5 MB y 35 ms a ≈1,0 MB y 118 ms por copia (medido con `psutil` sobre 12 copias, sin servidor). Con el tope de 200 copias son ≈200 MB, por debajo de los 512 MB, pero la carga de arranque por visitante se triplica: vigilar con la medición de carga.
- Cambiar el área reescribe el área de las alertas de ese buzón (no es un historial por fecha): el área es «la de hoy».
- Si la organización necesita otras áreas, se cambia la lista en el código (una decisión consciente, no un campo libre).
