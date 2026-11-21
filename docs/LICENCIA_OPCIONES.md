# Opciones de licencia para Atalaya

> **No se eligió ninguna.** Hoy el repositorio **no tiene archivo `LICENSE`**: por defecto eso significa «todos los derechos reservados» y nadie puede legalmente usar, copiar ni modificar el código. La decisión es de la persona autora. Esto es una comparación general, **no asesoría legal**.

## Comparación breve
| Opción | Qué permite | Qué exige | Para un proyecto que podría volverse comercial |
|---|---|---|---|
| **MIT** | Usar, copiar, modificar y vender, incluso en productos cerrados | Conservar el aviso de copyright y la licencia | Máxima adopción; **cualquiera, incluida una empresa grande, puede venderlo sin devolver nada** |
| **Apache-2.0** | Igual que MIT, más una concesión expresa de patentes | Aviso, indicar cambios | Como MIT, con más seguridad jurídica por las patentes; algo más larga |
| **AGPL-3.0** | Usar y modificar | Quien ofrezca el programa **como servicio en red** debe publicar su código modificado bajo AGPL | Protege el negocio de servicio alojado (nadie puede ofrecer una versión cerrada), pero algunas empresas la evitan; si quieres vender licencias cerradas, solo tú puedes (como autor único) |
| **Sin licencia / todos los derechos reservados** | Solo ver el repositorio si es público; nadie puede reutilizarlo | Pedirte permiso | Máximo control; **reduce la confianza** y puede chocar con que el repositorio sea revisable por el jurado y el Marketplace |

## Cosas del contexto que pesan
- El hackatón exige un repositorio **que se pueda revisar** (enlace público). Revisar no es lo mismo que tener permiso de reutilizar.
- Dojo pregunta por la licencia que se le da sobre el proyecto: está en [PREGUNTAS_ORGANIZADORES.md](PREGUNTAS_ORGANIZADORES.md) (#11) y **sin respuesta**. Conviene aclararlo antes de elegir, porque una licencia abierta no se puede retirar de las copias ya publicadas.
- Las dependencias (FastAPI, pydantic, cryptography, etc.) tienen licencias permisivas habituales; antes de publicar conviene confirmarlo con una herramienta de licencias (por ejemplo `pip-licenses`). No se hizo en esta redacción.
- Si el negocio fuera el servicio alojado (opción A de [NEGOCIO_Y_PROBLEMA.md](NEGOCIO_Y_PROBLEMA.md)), la protección frente a copias importa más; si fuera el kit autoalojado o el motor para otros desarrolladores (B y C), importa más la adopción.

## Recomendación razonada
**Para el hackatón: Apache-2.0** (o MIT si prefieres lo más corto). Razones:
1. El jurado y el Marketplace ven un repositorio que cualquiera puede evaluar y probar sin pedir permiso, sin comprometer la entrega.
2. Es compatible con vender el servicio o soporte después: la licencia aplica a este código, y tú sigues siendo el único autor.
3. El código es una base modesta; el valor comercial real (marca, datos, operación, listas de marcas verificadas) no está en el código fuente.

**Alternativa si la prioridad es proteger el negocio alojado:** AGPL-3.0. Cuesta algo de adopción, a cambio de impedir que otra empresa ofrezca una copia cerrada como servicio.

**Evitar** «sin licencia» si el repositorio va a ser público: transmite que se puede usar y, legalmente, no se puede.

## Pasos cuando decidas
1. Elegir una opción y confirmar la respuesta de Dojo sobre licencia (#11).
2. Añadir `LICENSE` en la raíz con el texto oficial (de choosealicense.com o spdx.org) y tu nombre y año.
3. Mencionarla en el `README.md` y comprobar que las licencias de las dependencias son compatibles.


---

## Decisión (21 nov 2026)
Se eligió **AGPL-3.0**. Motivos de la persona dueña del proyecto: el producto se publica automáticamente en el Marketplace del Dojo y quiere poder venderlo (por ejemplo, vender una licencia comercial a quien lo quiera usar en un producto cerrado) sin que otra persona lo copie y lo ofrezca como servicio cerrado. Notas:
- Es **AGPL**, no la GPL común: la GPL no cubre el uso como servicio en red; la AGPL sí.
- Una licencia **no impide** que alguien copie el código; da el **derecho legal** de reclamar si lo hace incumpliendo la licencia. Hay que notarlo y actuar.
- Siendo titular único de los derechos, el equipo puede ofrecer el código a la vez bajo AGPL y bajo una licencia comercial distinta (doble licencia).
- Pendiente: la pregunta a los organizadores «¿qué licencia le doy a Dojo sobre mi proyecto?» (`docs/PREGUNTAS_ORGANIZADORES.md`, #11) sigue sin respuesta por escrito. No es una decisión legal asesorada por una persona abogada.

- Borrador del contrato de licencia comercial para el kit autoalojado (para revisión por una persona abogada): [CONTRATO_LICENCIA_COMERCIAL_BORRADOR.md](CONTRATO_LICENCIA_COMERCIAL_BORRADOR.md).
