# demo_python_openllmetry

App web muy simple que llama a ChatGPT (modelo `gpt-4.1-nano`) cada vez que presionas un botón,
y además sola cada 1 minuto. Está instrumentada con [OpenLLMetry](https://github.com/traceloop/openllmetry)
y envía trazas, métricas y logs a **Dynatrace** a través de un **OpenTelemetry Collector**.
Todo corre en **GitHub Codespaces**.

![Arquitectura](docs/arquitectura.drawio.png)

Solo necesitas 3 valores, que se pasan como variables de entorno:

| Variable | Qué es | Dónde se usa |
|---|---|---|
| `OPENAI_API_KEY` | API key de OpenAI (`sk-...`) | app |
| `DT_TENANT_URL` | URL de tu tenant Dynatrace | collector |
| `DT_API_TOKEN` | Access token de Dynatrace (`dt0c01...`) | collector |

![Pasos](docs/pasos.drawio.png)

---

## Paso 1. Crea la API key de OpenAI

1. Entra a <https://platform.openai.com/api-keys>.
2. Haz clic en **Create new secret key**, ponle un nombre (ej. `demo-openllmetry`) y clic en **Create secret key**.
3. Copia la key (empieza con `sk-`). **Solo se muestra una vez.**
4. Revisa que la cuenta tenga saldo en <https://platform.openai.com/settings/organization/billing>.
   Sin saldo, OpenAI responde error `429`.

👉 Este valor es tu `OPENAI_API_KEY`.

## Paso 2. Copia la URL de tu tenant Dynatrace

1. Abre Dynatrace en el navegador.
2. Copia la dirección hasta `.com`, por ejemplo `https://abc12345.apps.dynatrace.com`.

Puedes usarla tal cual: `start.sh` la convierte sola a la URL de la API (`https://abc12345.live.dynatrace.com`).
Si usas Dynatrace Managed, el formato es `https://<tu-dominio>/e/<id-del-entorno>`.

👉 Este valor es tu `DT_TENANT_URL`.

## Paso 3. Crea el token de Dynatrace

1. En Dynatrace presiona `Ctrl + K`, busca **Access Tokens** y ábrela.
2. Haz clic en **Generate new token** y ponle un nombre (ej. `demo-openllmetry`).
3. En **Scopes**, busca y marca estos 3:

   | Scope en la UI | Nombre técnico |
   |---|---|
   | Ingest OpenTelemetry traces | `openTelemetryTrace.ingest` |
   | Ingest metrics | `metrics.ingest` |
   | Ingest logs | `logs.ingest` |

4. Haz clic en **Generate token** y copia el token (empieza con `dt0c01.`). **Solo se muestra una vez.**

> Tiene que ser un **Access token** (API token clásico). Un *platform token* (`dt0s16.`) no sirve aquí.

👉 Este valor es tu `DT_API_TOKEN`.

## Paso 4. Guarda los 3 valores como secrets de Codespaces

1. En GitHub abre este repo → **Settings**.
2. En el menú izquierdo: **Secrets and variables** → **Codespaces**.
3. Haz clic en **New repository secret** y crea estos 3 (uno a la vez):

   | Name | Secret |
   |---|---|
   | `OPENAI_API_KEY` | la key del paso 1 |
   | `DT_TENANT_URL` | la URL del paso 2 |
   | `DT_API_TOKEN` | el token del paso 3 |

Codespaces los entrega como variables de entorno cada vez que abres el codespace.

## Paso 5. Abre el Codespace

1. En la página del repo: botón verde **Code** → pestaña **Codespaces** → **Create codespace on main**.
2. Espera a que termine de prepararse (la primera vez tarda unos minutos).

> Si el codespace ya existía antes de crear los secrets, reinícialo para que los vea.

## Paso 6. Levanta el servicio

En la terminal del codespace ejecuta:

```bash
./start.sh
```

El script revisa las 3 variables, levanta la app y el collector, y al final te muestra la URL de la web.

## Paso 7. Genera tráfico

1. Abre la URL que mostró `start.sh` (o en la pestaña **PORTS**, puerto **8000**, clic en el globo).
2. Presiona **Generar tráfico**. Cada clic es una llamada a ChatGPT y la respuesta aparece debajo del botón.

Aunque no presiones nada, la app llama a ChatGPT sola cada minuto.

## Paso 8. Mira los datos en Dynatrace

Espera 1 o 2 minutos y luego:

- App **Distributed Tracing**: busca el servicio `demo-python-openllmetry`. Cada traza
  `dato_curioso.workflow` tiene un span `openai.chat` con el modelo, los tokens, el prompt y la respuesta.
- O en un **Notebook**, esta consulta DQL:

```dql
fetch spans, from: now()-30m
| filter service.name == "demo-python-openllmetry" and isNotNull(gen_ai.request.model)
| fields timestamp, span.name, gen_ai.request.model, gen_ai.usage.input_tokens, gen_ai.usage.output_tokens, duration
| sort timestamp desc
```

## Para detenerlo

```bash
docker compose down
```

## Si algo falla

| Problema | Qué hacer |
|---|---|
| `start.sh` dice `ERROR: falta la variable ...` | Revisa el paso 4 y reinicia el codespace |
| El botón muestra error `401` | La `OPENAI_API_KEY` está mal copiada |
| El botón muestra error `429` | La cuenta de OpenAI no tiene saldo |
| `docker compose logs otel-collector` muestra `401` o `403` | Token de Dynatrace incorrecto o le falta un scope (paso 3) |
| `docker compose logs otel-collector` muestra `404` | La URL del tenant está mal (paso 2) |
