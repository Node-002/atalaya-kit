# Resultados de detección — corpus de correos (20 nov 2026)

> **Actualización (marcas ampliadas):** el corpus pasó de 30 a 48 correos. Las secciones de abajo describen los **30 originales**; la comparación antes/después de la ampliación de marcas está en la última sección.

> Reproducir: `python -m app.evaluate` (tabla) o `python -m app.evaluate --json`. Corpus en `app/tests/fixtures/corpus.json`.
> **Advertencia metodológica:** los 30 correos son **sintéticos** y los escribió el propio desarrollador, que conoce las reglas. No son una muestra representativa del correo real. Se incluyeron a propósito casos difíciles para no inflar los números. Las cifras son **orientativas**, no una medición de rendimiento en producción.

## Composición
14 phishing (incluye 3 difíciles sin señales técnicas) y 16 legítimos (incluye 4 que parecen sospechosos). Un correo cuenta como "marcado" si el riesgo es **medio o alto**.

## Resultados
| Medida | Primera corrida | Tras corregir un defecto |
|---|---|---|
| Phishing detectado | 11/14 (79 %) | 11/14 (79 %) |
| Falsos positivos | 4/16 (25 %) | **3/16 (19 %)** |
| Precisión de "riesgo alto" | 88 % (8 marcados) | 88 % (8 marcados) |

**Defecto encontrado por el corpus (L06):** la regla de dominio parecido marcaba cualquier dominio que *contuviera* "bac" (por ejemplo `backups-empresa`). Ahora las marcas cortas solo cuentan como palabra completa. Además, los subdominios oficiales (`mail.bancogeneral.com`) ya no se marcan como falsos. Ambos tienen pruebas.

## Lo que NO se detecta (limitaciones reconocidas)
| Caso | Qué es | Por qué falla |
|---|---|---|
| P06 | Fraude de factura (cambio de cuenta bancaria), solo respuesta a otro dominio | Una sola señal técnica débil (20 pts) |
| P08 | Fraude del jefe: "haz una transferencia hoy, no se lo digas a nadie" | Sin señales técnicas; es ingeniería social pura |
| P13 | Enlace a un sitio desconocido, sin urgencia y con autenticación correcta | Faltan reputación de enlaces y análisis del texto |

Son casos de **significado**, no de cabeceras. Es donde la explicación con IA y la reputación de enlaces (Safe Browsing) deberían ayudar; **todavía no están integradas ni medidas.**

## Falsos positivos que quedan
| Caso | Qué es | Comentario |
|---|---|---|
| L03 | Boletín con enlace acortado y "ahora mismo" | Marketing legítimo con el mismo estilo que el phishing |
| L08 | Taller sin DKIM con plazo de 24 horas | Límite exacto (30 pts); empresas pequeñas suelen no tener DKIM |
| L14 | Persona real que escribe "ignora las instrucciones anteriores del formulario" | La regla de inyección de prompt es muy estricta (60 pts) y no distingue contexto |

Para estos casos, la **aprobación humana** (nunca se aísla sin tu decisión) y el botón "Es legítimo" son la salvaguarda.

## Qué no se debe afirmar en el pitch
- Que Atalaya "detecta el 79 %" del phishing real: solo se midió sobre este corpus sintético.
- Que no hay falsos positivos.
- Que la IA ya mejora estos números: aún no se probó.

## Dominios que imitan marcas con letras de otros alfabetos (homógrafos)
Añadido el 20 nov por la tarde, **fuera del corpus de 30** (no cambia esas métricas). Cubierto con 10 pruebas dedicadas en `app/tests/test_homograph.py`.

Antes de este cambio, un dominio como `b[a cirílica]ncogeneral.com` o con una vocal acentuada salía como **riesgo bajo**, y un correo con "Banco General" solo en el nombre visible también. Ahora:
- **Letras confundibles** (cirílico y griego frecuentes) y acentos se reducen a su apariencia latina antes de comparar con las marcas; los dominios en punycode (`xn--`) se decodifican.
- **Señales nuevas:** `homograph_domain` (30), `mixed_script_domain` (40, mezcla de alfabetos en una misma parte del dominio) y `display_name_brand` (30, nombre visible de marca con dominio ajeno).
- **También se revisan** la dirección de respuesta y los enlaces, no solo el remitente.
- **No marca** dominios en español legítimos con tildes o ñ, ni subdominios oficiales.

**Limitaciones:** la tabla de confusables es parcial (no es la lista completa de Unicode, UTS #39); la lista de marcas (ahora 22 palabras, ver abajo) está pendiente de verificar con nombres reales; solo se detecta el parecido con marcas de esa lista (un dominio parecido a una marca desconocida no se detecta); y no se evalúan trucos visuales dentro de imágenes del correo.

## Siguiente
1. Medir el efecto de la explicación con IA sobre P06, P08 y P13 (y sobre L03, L08, L14) cuando esté integrada.
2. Ampliar el corpus con correos de las pruebas reales de Gmail y, si es posible, correos de phishing públicos anonimizados.
3. No ajustar las reglas solo para mejorar estos números (riesgo de sobreajuste al corpus propio).

## Ampliación de marcas y errores de escritura (typosquatting)
Se añadieron 19 palabras de marca (Google/Gmail, Microsoft/Outlook/Office365, Netflix, Dropbox, PayPal, Apple/iCloud, Amazon, Facebook, DHL, Banistmo, Banco Nacional de Panamá, Davivienda, Yappy, Tigo, Cable & Wireless) con sus dominios oficiales (los subdominios cuentan como oficiales). Además, las marcas de **6 o más letras** detectan **un error de escritura** en una palabra del dominio (cambiar, quitar, añadir o intercambiar una letra: `goggle`, `googel`, `microsft`; y con cifras: `micros0ft`, `paypa1`). Las marcas cortas (`bac`, `bncr`, `dhl`, `tigo`, `yappy`) siguen exigiendo la palabra completa, y `backups-empresa` sigue sin marcarse. **No se cambiaron pesos ni umbrales:** usa `lookalike_domain` (35), `homograph_domain` (30) y `display_name_brand` (30), medio ≥30, alto ≥60.

Se añadieron 18 correos sintéticos (`.example`): 10 de phishing (P15–P24) y 8 legítimos o parecidos (L17–L24: dominios oficiales, `happy`, `tigre`, «Meta del mes», `googol`).

### Medición (`python -m app.evaluate`)
| Medida | Corpus original (30), antes | Corpus original (30), después | Corpus ampliado (48), código **anterior** | Corpus ampliado (48), código **nuevo** |
|---|---|---|---|---|
| Phishing detectado | 11/14 (79 %) | 11/14 (79 %) | 11/24 (46 %) | **21/24 (88 %)** |
| Falsos positivos | 3/16 (19 %) | 3/16 (19 %) | 3/24 (12 %) | 3/24 (12 %) |
| Precisión de «riesgo alto» | 88 % (8) | 88 % (8) | 88 % (8) | 93 % (14) |

**Lectura honesta:**
- Sobre los 30 originales **no cambia nada** (no empeora ni mejora): esos casos no usaban marcas nuevas.
- La mejora en el corpus ampliado (46 % → 88 %) es **esperable y poco informativa**: los 10 casos nuevos los escribí yo para esta función, y el código viejo no podía detectarlos. No es una estimación del rendimiento real.
- **Falsos positivos nuevos: 0** en el corpus (los mismos 3 de antes: L03, L08, L14). Los 8 legítimos nuevos pasan como riesgo bajo.
- Siguen sin detectarse P06, P08 y P13 (ingeniería social sin señales técnicas).

### Riesgos y límites que quedan
- **Falsos positivos probables fuera del corpus:** un dominio legítimo cuya palabra sea idéntica a una marca corta (`apple-huerto.example`, `tigo-...`) o difiera en una letra de una larga (`amazona`, `outlock`) se marcará. Es un riesgo de diseño, mitigado porque la acción siempre pide aprobación humana.
- No se detecta `rn` en lugar de `m` (`rnicrosoft`), ni la marca pegada a otra palabra (`googleacc`, `paypalsupport`) cuando la marca tiene menos de 8 letras.
- Los dominios oficiales están escritos de memoria y **hay que verificarlos**: si falta uno legítimo (p. ej. un dominio regional de Amazon o Tigo), sus correos se marcarían como falsos.
- «Meta» (Facebook) no se busca como palabra suelta porque en español es corriente; solo `facebook` y «Meta Platforms».


## Revisión de falsos negativos y positivos en dominios y enlaces (20 nov, noche)
Se probaron a mano ~35 casos adversos (subdominios engañosos, arrobas en enlaces, guiones, mayúsculas, puntos finales, puertos). **No cambian las métricas del corpus** (siguen 21/24 detectados y 3/24 falsos positivos, igual que antes de esta revisión); los casos nuevos están en `app/tests/test_brands.py`. No se cambió ningún peso ni umbral.

**Corregido (con pruebas):**
| Problema | Antes | Ahora |
|---|---|---|
| `google.com.` (punto final, válido en DNS) | se marcaba como falso (**falso positivo**) | oficial |
| `bit.ly.`, `bit.ly:80` | acortador **no** detectado | detectado |
| `http://paypal.com@evil.example/` | marcado solo de casualidad; el host real se leía mal | se analiza el host real (lo que hay tras la `@`) y el texto anterior se trata como lo que la persona creería ver |
| `hxxp://…`, `//…` | host mal leído | se reconocen |
| `pay-pal`, `micro-soft`, `net-flix` (guion partiendo la marca) | **no** detectado | detectado |
| `securepaypal`, `googleacc`, `applesupport` (marca + palabra típica de estafa) | **no** detectado | detectado (lista corta de palabras; `amazonas` y `applesauce` no se marcan) |
| Respuesta a `empresa.com` desde `mail.empresa.com` | `reply_to_mismatch` (**falso positivo**, 20 pts) | no se marca; `empresa.com.evil.example` y `notempresa.com` sí |

**Ya funcionaba y quedó con prueba:** `bancogeneral.com.evil.example`, `google.com.pa.evil.example`, mezcla de alfabetos, punycode, mayúsculas, marca solo en la ruta de la URL (no se marca, correcto) y `\` en la URL (el navegador lo trata como `/`).

**No resuelto (decisión documentada, sin cambiar pesos):**
- **Enlaces a una IP** (`http://192.168.1.1/google`) o a dominios sin marca no generan señal. Una señal nueva exigiría un peso nuevo; lo dejo para decidirlo.
- **Correos sin cabecera `Authentication-Results`** no suman puntos de SPF/DKIM/DMARC (solo `dkim=none` explícito). Podría ser un falso negativo; cambiarlo afecta a los pesos y no lo toqué.
- **Nombre visible** con la marca como palabra normal («Apple Pie Bakery», «Amazon Tours») se marca (`display_name_brand`, 30 pts = medio). Es el costo de buscar el nombre de marca como palabra completa.
- **Dominios legítimos de una marca que no estén en la lista** (p. ej. `googleusercontent.com`, `googleapis.com` usados en enlaces) se marcarían como falsos. Lista de oficiales pendiente de verificar.
- `rnicrosoft` (`rn` por `m`) y otros confundibles visuales no se cubren.

## Verificación de dominios oficiales de marcas (21 nov 2026)
Corpus ampliado de **48 a 62 correos** (8 legítimos y 6 de phishing nuevos, `L25`–`L32` y `P25`–`P30`; los falsos usan dominios `.example`). Fuentes y lista completa: `docs/VERIFICACION_MARCAS.md`. No se tocaron pesos ni umbrales.

| Medida | Antes, 48 correos (lista de memoria) | Después, mismos 48 | Lista anterior sobre los 62 | Lista verificada sobre los 62 |
|---|---|---|---|---|
| Phishing detectado | 21/24 (88 %) | 21/24 (88 %) | 25/30 (83 %) | 27/30 (90 %) |
| Falsos positivos | 3/24 (12 %) | 3/24 (12 %) | 7/32 (22 %) | 3/32 (9 %) |
| Precisión de «riesgo alto» | 93 % (14 marcados) | 93 % (14 marcados) | 84 % (19 marcados) | 95 % (19 marcados) |

**Nada empeoró** y los 48 originales no cambian: ninguno usaba dominios que faltaran en la lista. La mejora está en los 14 casos nuevos, que escribí yo mismo para esto: es una prueba de regresión de la lista, **no una medición independiente**.
- **Falsos positivos que desaparecen (L25, L27, L28, L29):** correo legítimo desde `bgeneral.com` (el dominio principal de Banco General, que faltaba), `amazon.com.br`, `paypal-communications.com` y un enlace a `microsoft365.com`. Con la lista de memoria salían como riesgo medio o alto.
- **Detecciones nuevas (P28, P30):** LinkedIn con typo (`linkedln`) y Scotiabank, que antes no estaban. WhatsApp, DocuSign y Bancolombia (P25–P27) ya salían altos por la autenticación fallida y la urgencia; los casos prueban además que ahora se reconoce el parecido con la marca.
- **P29** (enlace `bgeneral-clientes.example` en un correo desde el dominio oficial) solo se detecta por la palabra de marca nueva `bgeneral`; con la lista anterior el correo salía por una razón equivocada (marcaba el remitente legítimo).
- **Límite:** los falsos positivos que quedan (L03, L08, L14) no tienen que ver con marcas. Zoom y Adobe no se añadieron (palabras comunes). Pruebas unitarias nuevas: `app/tests/test_brand_domains.py` (59 casos: oficiales sin marcar, imitaciones, homógrafos y dominios de alojamiento de terceros que no deben ser oficiales).
