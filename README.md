# demo_python_openllmetry

Demo super simple de una app Python que llama a la API de OpenAI (ChatGPT), instrumentada con
[OpenLLMetry](https://github.com/traceloop/openllmetry), que envía su telemetría a **Dynatrace**
a través de un **OpenTelemetry Collector**. Está pensada para levantarse en **GitHub Codespaces**.

```
 Navegador ──► app (Flask :8000) ──────────────► API de OpenAI (gpt-4.1-nano)
                 │  OpenLLMetry (traceloop-sdk)
                 │  OTLP/HTTP :4318
                 ▼
          otel-collector (distribución Dynatrace)
                 │  OTLP/HTTP + Authorization: Api-Token
                 ▼
          Dynatrace  https://<tenant>/api/v2/otlp
```

## Qué hace

- Una web con un botón **"Generar tráfico"**: cada clic hace una llamada a OpenAI y pide un dato curioso.
- Además, la app llama sola a OpenAI **cada 1 minuto**, así siempre hay datos en Dynatrace.
- OpenLLMetry instrumenta automáticamente el SDK de OpenAI y envía:
  - **Trazas**: un span `dato_curioso.workflow` con un hijo `openai.chat` que trae los atributos
    `gen_ai.*` (modelo, proveedor, tokens de entrada y salida, prompt y respuesta).
  - **Métricas**: `gen_ai.client.token.usage`, `gen_ai.client.operation.duration`, etc. (en temporalidad delta).
  - **Logs** de la app, correlacionados con la traza (`trace_id`).

| Archivo | Para qué |
|---|---|
| `app.py` | App Flask + OpenAI + OpenLLMetry (todo en un archivo) |
| `otel-collector-config.yaml` | Config del collector: recibe OTLP y lo exporta a Dynatrace |
| `docker-compose.yml` | Levanta `app` y `otel-collector` |
| `start.sh` | Valida las variables, levanta todo y te muestra la URL |
| `.devcontainer/devcontainer.json` | Codespace con Python 3.12 + Docker |

## 1. Lo que necesitas

### Token de Dynatrace: tipo y scopes

Usa un **Access token** (API token clásico, empieza por `dt0c01.`).
**No** sirve un *platform token* (`dt0s16.`) para este endpoint.

Créalo en Dynatrace: **Access Tokens** (busca la app *Access Tokens*) → **Generate new token**,
y marca estos 3 scopes:

| Scope (API) | Nombre en la UI | Para qué |
|---|---|---|
| `openTelemetryTrace.ingest` | Ingest OpenTelemetry traces | Trazas |
| `metrics.ingest` | Ingest metrics | Métricas |
| `logs.ingest` | Ingest logs | Logs |

### URL del tenant

Es la URL de tu entorno **sin** `/` al final y **sin** `/api/v2/otlp` (eso lo agrega el collector):

| Tipo de entorno | Formato de `DT_TENANT_URL` |
|---|---|
| SaaS | `https://<env-id>.live.dynatrace.com` |
| Sprint (labs) | `https://<env-id>.sprint.dynatracelabs.com` |
| Managed | `https://<tu-dominio>/e/<env-id>` |

> Ojo: la API usa el dominio **`.live.`**, no el **`.apps.`** que ves en el navegador.
> Si pegas la URL `.apps.`, `start.sh` la corrige sola.

### API key de OpenAI

Créala en <https://platform.openai.com/api-keys>. La cuenta necesita saldo/créditos de API
(si no, OpenAI responde `429 insufficient_quota`).

## 2. Configura las variables de entorno

La app necesita 3 variables: `DT_TENANT_URL`, `DT_API_TOKEN` y `OPENAI_API_KEY`.

### Opción A (recomendada): Codespaces secrets

1. En GitHub, ve al repo → **Settings** → **Secrets and variables** → **Codespaces** → **New repository secret**.
2. Crea los 3 secrets: `DT_TENANT_URL`, `DT_API_TOKEN`, `OPENAI_API_KEY`.

Codespaces los inyecta como variables de entorno al iniciar el codespace. También puedes
crearlos a nivel de usuario en <https://github.com/settings/codespaces> (dándole acceso a este repo).
Como el `devcontainer.json` los declara como *recommended secrets*, si creas el codespace con
**Code → Codespaces → ⋯ → New with options**, GitHub te los pide en esa pantalla.

> Si creas o cambias un secret con el codespace ya abierto, no lo verá hasta que lo reinicies
> (o usa la opción B).

### Opción B: archivo `.env` dentro del codespace

```bash
cp .env.example .env
# edita .env y pon tus valores
```

`.env` está en `.gitignore`. Si existe, sus valores tienen prioridad sobre los secrets.

## 3. Crea el codespace

En el repo: **Code** → **Codespaces** → **Create codespace on main**.
La primera vez tarda un par de minutos (instala Python 3.12 y Docker dentro del codespace).

## 4. Levanta la demo

En la terminal del codespace:

```bash
./start.sh
```

El script valida las variables, construye la imagen de la app, levanta app + collector con
`docker compose` y te imprime la URL de la web. También puedes abrirla desde la pestaña
**PORTS** → puerto **8000** → icono del globo.

## 5. Genera tráfico

Abre la web y presiona **Generar tráfico** las veces que quieras. Cada clic es una llamada a
OpenAI y debajo del botón aparece la respuesta. Sin hacer nada, la app igual llama a OpenAI cada minuto.

Para comprobar que el collector está enviando:

```bash
docker compose logs -f otel-collector
```

Deberías ver líneas como `Traces ... "spans": 2` sin errores después.

## 6. Mira la telemetría en Dynatrace

Espera 1 o 2 minutos y luego:

- **Distributed Tracing**: filtra por servicio `demo-python-openllmetry` y abre una traza
  `dato_curioso.workflow` → `openai.chat`. En los atributos del span vas a ver el modelo,
  los tokens, el prompt y la respuesta.
- **AI Observability** (si está habilitada en tu tenant): tokens, latencia y modelos.
- **Notebooks**: prueba estas consultas DQL.

Últimas llamadas a OpenAI:

```dql
fetch spans, from: now()-30m
| filter service.name == "demo-python-openllmetry" and isNotNull(gen_ai.request.model)
| fields timestamp, span.name, gen_ai.request.model, gen_ai.usage.input_tokens, gen_ai.usage.output_tokens, duration, trace.id
| sort timestamp desc
```

Llamadas, errores, latencia y tokens por modelo:

```dql
fetch spans, from: now()-1h
| filter service.name == "demo-python-openllmetry" and isNotNull(gen_ai.request.model)
| summarize llamadas = count(), errores = countIf(span.status_code == "error"), p95_ms = percentile(duration, 95) / 1ms, input_tokens = sum(gen_ai.usage.input_tokens), output_tokens = sum(gen_ai.usage.output_tokens), by: {gen_ai.request.model}
```

Logs de la app (correlacionados con la traza):

```dql
fetch logs, from: now()-30m
| filter service.name == "demo-python-openllmetry"
| fields timestamp, loglevel, content, trace_id
| sort timestamp desc
```

## Comandos útiles

```bash
docker compose logs -f app              # ver las llamadas a OpenAI
docker compose logs -f otel-collector   # ver lo que se envía a Dynatrace
docker compose down                     # detener todo
OPENAI_MODEL=gpt-5-nano ./start.sh      # probar otro modelo
INTERVAL_SECONDS=30 ./start.sh          # cambiar la frecuencia de la llamada automática
```

## Problemas comunes

| Síntoma | Causa probable |
|---|---|
| `ERROR: falta la variable ...` | Los secrets no llegaron al codespace: reinícialo o usa el `.env` |
| Collector con `401` o `403` | Token incorrecto o le falta algún scope |
| Collector con `404` | URL del tenant mal (revisa `.live.` vs `.apps.`, o `/e/<env-id>` en Managed) |
| Botón muestra `401` | `OPENAI_API_KEY` inválida |
| Botón muestra `429` | La cuenta de OpenAI no tiene saldo o llegó al límite |
| Collector sin errores pero no ves nada | Espera 1 o 2 minutos y revisa el rango de tiempo en Dynatrace |

## Notas

- **Modelo**: por defecto `gpt-4.1-nano`, el modelo de chat más barato de OpenAI que no es de
  razonamiento (a la fecha, USD 0.10 por millón de tokens de entrada y 0.40 por millón de salida).
  `gpt-5-nano` cobra menos por la entrada, pero es un modelo de razonamiento y factura tokens
  ocultos como salida, así que para respuestas cortas suele salir más caro y lento.
  Con una llamada por minuto el costo es de centavos de dólar al día.
- **Contenido de los prompts**: OpenLLMetry guarda el prompt y la respuesta en los atributos del
  span. Para no enviarlos, agrega `TRACELOOP_TRACE_CONTENT=false` al servicio `app` en `docker-compose.yml`.
- **Por qué un collector**: la app solo conoce `http://otel-collector:4318`; el token de Dynatrace
  vive únicamente en el collector. El collector además convierte las métricas a temporalidad delta,
  que es la que acepta Dynatrace.
