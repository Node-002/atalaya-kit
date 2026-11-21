# ADR 0004 — Panel de organización, campañas y rol de supervisor

- **Fecha:** 2026-11-20
- **Estado:** aceptada. Implementada en la demo y en el modo conectado (uso local).

## Contexto
El modelo de negocio confirmado es **una organización con varios buzones** (empleados o usuarios) y una persona administradora que los gestiona (ADR 0003). El panel era una lista única de alertas; con varios buzones no se veía quién estaba cubierto, ni que el mismo ataque llegaba a varias personas. Además, quien supervisa (dirección, auditoría) debe poder **ver** sin poder **actuar**. Campañas y supervisor no estaban en el alcance; la persona dueña del proyecto los autorizó de forma explícita el 20 nov 2026.

## Decisión
1. **Pestañas** `Resumen`, `Correos`, `Buzones`, `Historial`. Los avisos de seguridad siguen visibles sobre las pestañas.
2. **Resumen por buzón:** tarjeta con cobertura, contadores por grupo y último chequeo; tocarla filtra «Correos» por ese buzón. El motivo de cada alerta es una frase (la señal de más peso); el detalle técnico queda plegado.
3. **Campañas.** El código calcula dos huellas (hash) por alerta al analizar: la del **remitente** y la de **dominio + asunto normalizado**. Alertas de riesgo medio o alto de **≥2 buzones** que comparten alguna huella forman una campaña. No se guarda remitente, asunto ni cuerpo: solo los hashes. La acción única «Poner en cuarentena en los N buzones» llama a la misma lógica que la individual: si alguna alerta exige motivo y no se escribió, **no se toca ninguna** (422); hay una entrada de auditoría por alerta; es reversible (cada correo se saca de cuarentena con su acción individual); nunca borra ni envía.
4. **Supervisor de solo lectura.** `ATALAYA_SUPERVISOR_EMAILS` (misma validación ASCII que los administradores, mismo inicio de sesión con Google, misma identidad enmascarada). Una cuenta en ambas listas es administradora. El **servidor** responde 403 a cualquier método de escritura en `/api/` para el supervisor (middleware), además de ocultar los botones. Ve el panel, el historial, los informes y el **reporte de la organización** (`/api/org-report`: resumen, decisiones con quién y cuándo, actividad). Atalaya no envía correos: el reporte se ve o se descarga.
4b. **Solo en la demo** (sin cuentas), un botón alterna entre administración y supervisor mediante una cookie, para enseñar la vista de solo lectura; el servidor también la hace cumplir. No existe fuera de la demo.

## Consecuencias
- Reglas de detección, pesos y umbrales intactos.
- Las alertas guardadas antes de este cambio no tienen huellas y simplemente no forman campañas.
- Límite: una campaña con remitente y asunto distintos en cada buzón no se agrupa (se prefiere no agrupar a agrupar mal).
- Un solo rol de lectura; sin permisos por buzón ni jerarquías.

## Revisión de seguridad y escala (20 nov 2026)
- Pruebas nuevas (`app/tests/test_panel_security.py`): todo endpoint del panel exige sesión (401 sin datos en el error), CSRF antes que cualquier otra cosa, motivo con tope de 500, 404 genéricos, reportes en `text/plain` con `nosniff`/`no-store`, y ningún `innerHTML` en el JS.
- Escala (50 a 200 buzones): el estado de conexión de cada buzón se guarda 60 s en modo Gmail (antes, una llamada de red por buzón en cada refresco); el Resumen ordena lo urgente primero, busca por nombre o cuenta, filtra «solo los que necesitan atención» y pagina de 24 en 24; la lista de buzones busca y pagina; cada grupo de correos muestra 40 y ofrece «Mostrar más». Con 200 buzones, sondear y agrupar campañas tarda menos de 5 s (prueba). Una campaña de 100 buzones se aísla con un solo clic.
