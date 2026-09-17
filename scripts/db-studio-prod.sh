#!/bin/bash
# Abre Prisma Studio conectado ao banco de producao via SSH tunnel
# Uso: ./scripts/db-studio-prod.sh

PORT=15432
REMOTE_IP="10.0.1.16"
SERVER="wesley@169.58.29.233"
DB_PASS="lrLB9lkKeIcKOnGfiLZi0hYLlQWkTXpyTDl94VuXnHXZaNpTAd4L31jy46k3T91n"

echo "Abrindo tunnel SSH..."
ssh -L ${PORT}:${REMOTE_IP}:5432 ${SERVER} -N -f 2>/dev/null

if ! lsof -i :${PORT} > /dev/null 2>&1; then
  echo "Erro: tunnel nao abriu. Verifique a conexao SSH."
  exit 1
fi

echo "Tunnel ativo na porta ${PORT}"
echo "Abrindo Prisma Studio em http://localhost:5555"
echo ""

DATABASE_URL="postgresql://postgres:${DB_PASS}@localhost:${PORT}/postgres" npx prisma studio

# Limpar tunnel ao fechar
echo "Fechando tunnel..."
pkill -f "ssh -L ${PORT}:${REMOTE_IP}:5432"
