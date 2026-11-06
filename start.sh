#!/bin/bash

# Interrompe o script caso ocorra algum erro
set -e

echo "==> Detectando o GID do grupo Docker no host..."
DOCKER_GID=$(getent group docker | cut -d: -f3)

if [ -z "$DOCKER_GID" ]; then
    echo "Erro: Não foi possível detectar o GID do grupo docker."
    exit 1
fi

if [ ! -f ".zsh_history" ]; then
    echo "Criando o arquivo .zsh_history..."
    touch .zsh_history
fi

echo "Ajustando permissões..."
chmod 666 .zsh_history

echo "==> Atualizando o arquivo .env com DOCKER_GID=$DOCKER_GID..."
echo "DOCKER_GID=$DOCKER_GID" > .env

echo "==> Construindo e subindo os containers com Docker Compose..."
docker compose build --no-cache
docker compose up -d

echo "==> Ambiente pronto!"