# HuelaEstafa Guard — guardián de correo para organizaciones

> Dojo AI Hackathon · 20–22 de noviembre de 2026 · Proyecto en solitario

## El problema
El correo es la puerta de entrada de la mayoría de los ataques (phishing, enlaces maliciosos, adjuntos
infectados). Las pymes, colegios y universidades no tienen un equipo de seguridad que revise cada correo,
y los empleados dudan o hacen clic.

## La solución
Un sistema web donde un empleado conecta su correo institucional con "Iniciar sesión con Google"
(sin contraseña) y **da su consentimiento**. A partir de ahí, cada correo nuevo se analiza automáticamente:

1. **Autenticidad del remitente:** SPF/DKIM/DMARC, dominio parecido a una marca, remitente distinto de la dirección de respuesta.
2. **Enlaces:** reglas (acortadores, dominios recién creados) + reputación (Safe Browsing).
3. **Adjuntos:** consulta por hash (VirusTotal); el archivo nunca se sube.
4. **Explicación en español** con IA, basada en hechos calculados por código.
5. **Acción:** etiqueta en la bandeja ("Sospechoso") y alerta al responsable de seguridad.

**Principio central:** el responsable ve alertas, **no el contenido de los correos**.

## Arquitectura
```
Gmail API ──(polling cada minuto)──> Cola de correos nuevos
   → Enmascarar datos personales → Analizadores (autenticación, enlaces, adjuntos, reglas)
   → IA explica (el correo se trata como dato hostil) → Veredicto
   → Etiqueta en Gmail + alerta en el panel (se guarda solo veredicto, señales y un ID)
```

## Stack
- **Backend:** Python + FastAPI
- **Login/correo:** Google OAuth 2.0 + Gmail API (Microsoft Graph como extra futuro)
- **Análisis:** reglas propias, `tldextract`, RDAP/whois, Safe Browsing, VirusTotal (hashes)
- **IA:** Claude API (explicación estructurada)
- **Frontend:** HTML + JS simple con Tailwind
- **Datos:** SQLite; tokens cifrados; sin guardar contenido de correos
- **Deploy:** Render o Railway (HTTPS obligatorio para OAuth)

## Estructura
```
Hackaton/
├── README.md
├── docs/
│   ├── IDEAS.md                 ← análisis de ideas y evolución
│   ├── PLAN.md                  ← plan por días
│   ├── PITCH.md                 ← guion de la demo
│   └── ETICA_LEGAL_SEGURIDAD.md ← ética, leyes, riesgos y verificaciones
├── pitch/archivo/               ← pitch anterior (FacturaCR)
└── app/                         ← código (por crear)
```

## Track objetivo
**Track 02 · AI Operators**: un agente que lleva el proceso de seguridad del correo de principio a fin (detecta, analiza, decide, actúa) con una persona que aprueba lo de alto impacto. Detalles en [docs/REGLAS_Y_TRACKS.md](docs/REGLAS_Y_TRACKS.md).

## Alcance del MVP
Login con Google → lectura automática de correos nuevos → análisis → etiqueta + panel de alertas.
Todo lo demás (Microsoft, cuarentena, capturas) son extras.

## Aviso
Herramienta de apoyo, no garantía. Ver [docs/ETICA_LEGAL_SEGURIDAD.md](docs/ETICA_LEGAL_SEGURIDAD.md).
