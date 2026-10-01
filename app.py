"""Demo super simple: web con un botón que llama a OpenAI + una llamada
automática cada minuto. Todo instrumentado con OpenLLMetry (Traceloop SDK),
que envía la telemetría por OTLP al OpenTelemetry Collector."""
import logging
import os
import random
import threading
import time

from flask import Flask, jsonify
from openai import OpenAI
from traceloop.sdk import Traceloop
from traceloop.sdk.decorators import workflow

# OpenLLMetry: trazas, métricas y logs (TRACELOOP_LOGGING_ENABLED=true) por OTLP/HTTP hacia el collector
Traceloop.init(
    app_name=os.getenv("OTEL_SERVICE_NAME", "demo-python-openllmetry"),
    api_endpoint=os.getenv("TRACELOOP_BASE_URL", "http://localhost:4318"),
    disable_batch=True,
)

# Traceloop deja en el logger raíz solo el handler OTLP; agregamos la consola para ver los logs en docker
consola = logging.StreamHandler()
consola.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logging.getLogger().addHandler(consola)
logging.getLogger().setLevel(logging.INFO)
log = logging.getLogger("demo")

MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-nano")
INTERVAL_SECONDS = int(os.getenv("INTERVAL_SECONDS", "60"))
TEMAS = ["observabilidad", "OpenTelemetry", "Kubernetes", "Python", "la nube", "el café", "los gatos"]

client = OpenAI()  # lee OPENAI_API_KEY del entorno
app = Flask(__name__)


@workflow(name="dato_curioso")
def pedir_dato_curioso(origen: str) -> str:
    tema = random.choice(TEMAS)
    respuesta = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "Respondes en español con una sola frase corta."},
            {"role": "user", "content": f"Dime un dato curioso sobre {tema}."},
        ],
    )
    texto = respuesta.choices[0].message.content
    log.info("[%s] %s -> %s", origen, tema, texto)
    return texto


def llamada_automatica():
    while True:
        try:
            pedir_dato_curioso("automatico")
        except Exception:
            log.exception("Falló la llamada automática a OpenAI")
        time.sleep(INTERVAL_SECONDS)


PAGINA = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Demo OpenLLMetry</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 640px; margin: 40px auto; padding: 0 16px; }
    button { font-size: 1.1rem; padding: 10px 20px; cursor: pointer; }
    li { margin: 8px 0; }
    .error { color: #b00020; }
  </style>
</head>
<body>
  <h1>Demo OpenLLMetry → Dynatrace</h1>
  <p>Modelo: <b>__MODEL__</b>. Además del botón, la app llama a OpenAI sola cada __INTERVAL__ s.</p>
  <button id="btn">Generar tráfico</button>
  <ul id="resultados"></ul>
  <script>
    const btn = document.getElementById("btn");
    btn.onclick = async () => {
      btn.disabled = true;
      const li = document.createElement("li");
      try {
        const r = await fetch("/generar", { method: "POST" });
        const data = await r.json();
        li.textContent = data.ok ? data.respuesta : "Error: " + data.error;
        if (!data.ok) li.className = "error";
      } catch (e) {
        li.textContent = "Error: " + e;
        li.className = "error";
      }
      document.getElementById("resultados").prepend(li);
      btn.disabled = false;
    };
  </script>
</body>
</html>
"""


@app.get("/")
def index():
    return PAGINA.replace("__MODEL__", MODEL).replace("__INTERVAL__", str(INTERVAL_SECONDS))


@app.post("/generar")
def generar():
    try:
        return jsonify(ok=True, respuesta=pedir_dato_curioso("boton"))
    except Exception as e:
        log.exception("Falló la llamada a OpenAI desde el botón")
        return jsonify(ok=False, error=str(e)), 500


if __name__ == "__main__":
    threading.Thread(target=llamada_automatica, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
