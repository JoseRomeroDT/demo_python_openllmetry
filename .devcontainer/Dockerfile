# Debian 12 (bookworm): la imagen 3.12 sin sufijo ya es Debian 13 (trixie), donde el
# feature docker-in-docker no puede instalar moby y la creación del codespace falla
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# El repo de Yarn preinstalado tiene la clave GPG caducada y rompe apt-get update
RUN rm -f /etc/apt/sources.list.d/yarn.list /etc/apt/trusted.gpg.d/yarn*.gpg \
 && apt-get update \
 && rm -rf /var/lib/apt/lists/*
