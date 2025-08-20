#!/bin/bash

# ScriptFlow - Deploy Rápido do GitHub
# Este script faz clone do GitHub e executa a instalação automaticamente

set -e

# CONFIGURAÇÕES - ALTERE AQUI
GITHUB_REPO="https://github.com/SEU-USUARIO/scriptflow.git"  # ⚠️ ALTERE AQUI
GITHUB_BRANCH="main"
DOMAIN="localhost"  # Altere para seu domínio

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Verificar se está executando como root
if [ "$EUID" -ne 0 ]; then
    print_error "Execute como root: sudo $0"
    exit 1
fi

print_status "🚀 ScriptFlow - Deploy Rápido do GitHub"

# Verificar se GitHub repo está configurado
if [[ "$GITHUB_REPO" == *"SEU-USUARIO"* ]]; then
    print_error "❌ Configure o GITHUB_REPO no início do script!"
    echo "Edite a linha: GITHUB_REPO=\"https://github.com/SEU-USUARIO/scriptflow.git\""
    exit 1
fi

print_status "📦 Instalando dependências básicas..."
apt update
apt install -y git curl wget

print_status "📥 Clonando projeto do GitHub..."
cd /tmp
rm -rf scriptflow_deploy
git clone -b "$GITHUB_BRANCH" "$GITHUB_REPO" scriptflow_deploy

if [ ! -f "/tmp/scriptflow_deploy/deploy/deploy_ubuntu.sh" ]; then
    print_error "Script de deploy não encontrado no repositório!"
    print_error "Certifique-se que o repositório contém: deploy/deploy_ubuntu.sh"
    exit 1
fi

print_status "🔧 Configurando deploy script..."
cd /tmp/scriptflow_deploy

# Configurar variáveis no script principal
sed -i "s|GITHUB_REPO=\"\"|GITHUB_REPO=\"$GITHUB_REPO\"|" deploy/deploy_ubuntu.sh
sed -i "s|DOMAIN=\"localhost\"|DOMAIN=\"$DOMAIN\"|" deploy/deploy_ubuntu.sh

print_status "🚀 Iniciando instalação completa..."
chmod +x deploy/deploy_ubuntu.sh
./deploy/deploy_ubuntu.sh

print_success "🎉 Deploy concluído!"
print_status "🌐 Acesse: http://$DOMAIN"
print_status "👤 Login: admin / admin123"

# Limpar arquivos temporários
cd /
rm -rf /tmp/scriptflow_deploy