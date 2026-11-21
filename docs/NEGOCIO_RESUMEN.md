# Resumen de negocio (una página)

> **Estado honesto:** no hay clientes, no hay entrevistas hechas y no hay ingresos. Todo lo de modelo, precio y costos es **hipótesis sin validar**. Las cifras del problema vienen de notas de prensa que citan estudios de empresas que venden seguridad; **abrir cada fuente antes de citarla** (esta redacción copió las cifras de [EVIDENCIA_PUBLICA.md](EVIDENCIA_PUBLICA.md) sin reabrirlas). Si la encuesta ([ENCUESTA_DOJO.md](ENCUESTA_DOJO.md)) o entrevistas aportan respuestas, añadirlas aquí con el número exacto.

## 1. A quién se vende
Organizaciones pequeñas con **5 a 100 buzones** que usan Gmail/Google Workspace y no tienen un equipo de seguridad: **colegios, clínicas, pymes y universidades** (Panamá y la región).
- **Quien paga:** la persona responsable de TI o la dirección. **Usuario final:** cada empleado cuyo buzón se vigila.
- **Por qué 5–100:** es el rango para el que el panel está diseñado y probado (con 200 buzones, sondear y agrupar tarda menos de 5 s en prueba). Es una decisión de diseño, no un estudio de mercado.
- El tamaño del mercado (número de organizaciones en Panamá) **no está calculado**: falta una fuente oficial.

## 2. El problema (cifras con fuente y advertencia)
| Dato | Fuente | Advertencia |
|---|---|---|
| 43 % de las pymes de LATAM fue víctima de phishing el año anterior (Kaspersky, 2025) | [El Mundo (SV)](https://diario.elmundo.sv/economia/un-43-de-pymes-de-america-latina-sufrio-phishing-el-ano-pasado-denuncian-expertos) | Estudio de un proveedor de seguridad, citado por prensa |
| 57 % reportó más ciberataques que antes; el phishing, el más reportado (Kaspersky, 2025) | [Valora Analitik](https://www.valoraanalitik.com/el-57-de-las-pymes-en-latinoamerica-reporta-un-incremento-de-ciberataques/) | Percepción de las personas encuestadas |
| 31 % de las pymes reportó pérdidas económicas tras ciberataques | [Diario Correo](https://diariocorreo.pe/tecnologia/ciberataques-afectan-a-las-pymes-31-reporta-perdidas-economicas-en-latinoamerica-noticia/) | Mismo estudio; verificar |
| 73 % de las **empresas** de LATAM fue objetivo de phishing en 2025 (ESET) | [Mercado (AR)](https://mercado.com.ar/tecnologia/eset-el-73-de-empresas-latinoamericanas-fue-objetivo-de-phishing-en-2025) | Empresas de todos los tamaños; mide **objetivo**, no daño |
| El phishing es el principal ataque que registra el CSIRT Panamá (AIG) | [Panamá América](https://www.panamaamerica.com.pa/tecnologia/phishing-es-el-principal-ataque-informatico-que-se-registra-en-el-pais-1260704) | Confirmar la cifra exacta en el CSIRT |
| Sector bancario panameño: ~125 millones de dólares en intentos o sospechas de fraude en 2025 | [La Estrella de Panamá](https://www.laestrella.com.pa/economia/ciberataques-en-panama-sector-bancario-reporta-125-millones-en-fraudes-FM20865635) | Sector financiero, no pymes |

**No mezclar** las cifras entre sí (preguntas distintas; otra encuesta de Kaspersky da 24 % de incidentes). **No decir** «ataques exitosos» a partir de intentos (la AIG aclaró que su «500 %» son intentos de intrusión). **No afirmar** que *nuestros* clientes tienen el problema ni que pagarían: solo conversaciones reales lo confirman.

## 3. Modelo de ingresos y precio — HIPÓTESIS
- **Modelo:** suscripción mensual **por buzón protegido**, con prueba gratuita. Alternativas anotadas en [NEGOCIO_Y_PROBLEMA.md](NEGOCIO_Y_PROBLEMA.md): servicio alojado (A), kit autoalojado (B), motor de análisis para otros desarrolladores (C).
- **Precio:** **no hay precio definido.** Decisión pendiente de la persona autora. Para decidirlo hace falta (a) medir el costo real de IA por correo y (b) comparar con precios **verificados** de la competencia. La encuesta pregunta el rango de pago razonable (US$0 a más de US$10 por buzón/mes): es una muestra pequeña y no representativa.
- **Marketplace de Dojo:** el creador se queda con el 85 % de cada venta (confirmado en el kickoff, según [PREGUNTAS_ORGANIZADORES.md](PREGUNTAS_ORGANIZADORES.md)); **cómo se entrega y cobra el producto sigue sin respuesta por escrito.**

## 4. Costos principales
| Costo | Estado |
|---|---|
| **IA por correo analizado** (modelo configurable, por defecto `claude-haiku-5-5`) | **Sin medir.** La IA real nunca se ha probado con saldo; se envían como máximo 200 caracteres de asunto y 1 500 de texto enmascarado por correo |
| **Google:** verificación de la aplicación para uso público (alcance de Gmail) y posible evaluación de seguridad | No iniciada. Hoy: modo de pruebas, máximo 100 usuarios y tokens de 7 días |
| Alojamiento | La demo usa un plan gratuito que se duerme; un servicio real necesitaría plan de pago y base de datos persistente |
| Soporte, privacidad y cumplimiento legal | Sin cuantificar; borradores en [POLITICA_PRIVACIDAD.md](POLITICA_PRIVACIDAD.md) y [TERMINOS_DE_USO.md](TERMINOS_DE_USO.md) |

## 5. Competencia (de [COMPETENCIA.md](COMPETENCIA.md); sin verificación en vivo)
- **Incluido en el proveedor:** Google Workspace, Microsoft Defender para Office 365.
- **Pasarelas:** Proofpoint, Mimecast, Barracuda (cambio de registros MX).
- **Seguridad por API con IA:** Abnormal, Check Point Harmony Email, IRONSCALES, Sublime.
- **Entrenamiento:** KnowBe4, Cofense.
- **Diferencia que Atalaya apuesta:** español, veredicto explicado con señales verificables, privacidad por diseño (no guarda cuerpos), instalación sencilla, vista por organización y campañas. **No** promete detectar más que ellos. Falta verificar funciones y precios en sus sitios oficiales.

## 6. Riesgos
| Riesgo | Mitigación / estado |
|---|---|
| **Demanda no validada:** sin clientes ni entrevistas | Encuesta y entrevistas; hasta entonces, todo es hipótesis |
| **Detección limitada:** sin adjuntos, sin reputación de enlaces, 21/24 y 3/24 en corpus sintético | Declararlo; decisión humana siempre; medir con correos reales |
| **Verificación de Google** lenta o costosa | Modo kit autoalojado (B) evitaría custodiar cuentas de terceros |
| **Solo Gmail:** parte del mercado usa Microsoft 365 | No construido; la pregunta está en la encuesta |
| **Competidores grandes** (Google/Microsoft ya incluyen filtros) | Nicho: español y organizaciones pequeñas; no competir en detección |
| **Privacidad y ley** (datos personales en correos) | Minimización, cifrado, textos legales por revisar con una persona abogada |
| **Costo de IA** sin medir | Medir antes de fijar precio; la explicación degrada a plantilla si la IA falla |
| **Dependencia de una persona** (proyecto de una persona) | Alcance congelado, documentación y ADR |
