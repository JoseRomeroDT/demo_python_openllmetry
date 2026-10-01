#!/usr/bin/env bash
# Valida las variables, levanta app + collector y muestra la URL de la web.
set -e
cd "$(dirname "$0")"

# Alternativa a los Codespaces secrets: un archivo .env (cp .env.example .env)
if [ -f .env ]; then
  set -a; . ./.env; set +a
fi

for v in DT_TENANT_URL DT_API_TOKEN OPENAI_API_KEY; do
  if [ -z "${!v}" ]; then
    echo "ERROR: falta la variable $v. Revisa el paso 4 del README."
    exit 1
  fi
done

# La API OTLP vive en el dominio "live", no en "apps": se corrige si pegaste la URL de la UI
DT_TENANT_URL="${DT_TENANT_URL%/}"
DT_TENANT_URL="${DT_TENANT_URL/.sprint.apps./.sprint.}"
DT_TENANT_URL="${DT_TENANT_URL/.apps./.live.}"
export DT_TENANT_URL

# Platform token (dt0s16.) va con "Bearer"; access token clásico (dt0c01.) con "Api-Token"
case "$DT_API_TOKEN" in
  dt0c01.*) DT_AUTH_SCHEME="Api-Token" ;;
  *)        DT_AUTH_SCHEME="Bearer" ;;
esac
export DT_AUTH_SCHEME

echo "Enviando telemetría a: ${DT_TENANT_URL}/api/v2/otlp (Authorization: ${DT_AUTH_SCHEME})"
docker compose up --build -d

if [ -n "$CODESPACE_NAME" ]; then
  URL="https://${CODESPACE_NAME}-8000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
else
  URL="http://localhost:8000"
fi

echo ""
echo "=============================================================="
echo " Demo levantada"
echo "   Web (botón Generar tráfico): $URL"
echo ""
echo " Ver logs:"
echo "   docker compose logs -f app"
echo "   docker compose logs -f otel-collector"
echo " Detener:"
echo "   docker compose down"
echo "=============================================================="
