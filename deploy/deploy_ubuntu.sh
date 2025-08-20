#!/bin/bash

# ScriptFlow - Script de Deploy Automatizado para Ubuntu
# Este script automatiza o processo de instalação do ScriptFlow

set -e  # Para no primeiro erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para imprimir mensagens coloridas
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar se está executando como root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "Este script deve ser executado como root (use sudo)"
        exit 1
    fi
}

# Configurações (ALTERE CONFORME NECESSÁRIO)
SCRIPTFLOW_USER="scriptflow"
SCRIPTFLOW_DIR="/opt/scriptflow"
DOMAIN="localhost"  # Altere para seu domínio
SECRET_KEY=$(openssl rand -hex 32)

# GITHUB REPOSITORY (altere se necessário)
GITHUB_REPO=""  # Deixe vazio se não usar GitHub
GITHUB_BRANCH="main"  # Branch a ser clonado

# Arquivo ZIP alternativo (se não usar GitHub)
PROJECT_ZIP_URL=""  # URL para download direto do ZIP

print_status "🚀 Iniciando instalação do ScriptFlow..."

# Verificar root
check_root

# 1. Atualizar sistema
print_status "📦 Atualizando sistema..."
apt update && apt upgrade -y

# 2. Instalar dependências
print_status "📋 Instalando dependências do sistema..."
apt install -y python3 python3-pip python3-venv python3-dev \
               nginx supervisor git curl wget \
               build-essential libssl-dev libffi-dev

# 3. Criar usuário
print_status "👤 Criando usuário scriptflow..."
if ! id "$SCRIPTFLOW_USER" &>/dev/null; then
    adduser --system --group --home "$SCRIPTFLOW_DIR" "$SCRIPTFLOW_USER"
    print_success "Usuário $SCRIPTFLOW_USER criado"
else
    print_warning "Usuário $SCRIPTFLOW_USER já existe"
fi

# 4. Criar diretórios
print_status "📁 Criando estrutura de diretórios..."
mkdir -p "$SCRIPTFLOW_DIR"
mkdir -p "$SCRIPTFLOW_DIR/logs"
mkdir -p "$SCRIPTFLOW_DIR/uploads" 
mkdir -p "$SCRIPTFLOW_DIR/instance"
mkdir -p "/opt/backups/scriptflow"

# 5. Baixar arquivos do projeto
download_project() {
    print_status "📥 Baixando arquivos do projeto..."
    
    if [ -n "$GITHUB_REPO" ]; then
        # Opção 1: Clonar do GitHub
        print_status "📋 Clonando repositório: $GITHUB_REPO"
        git clone -b "$GITHUB_BRANCH" "$GITHUB_REPO" "$SCRIPTFLOW_DIR"
        chown -R "$SCRIPTFLOW_USER:$SCRIPTFLOW_USER" "$SCRIPTFLOW_DIR"
        
    elif [ -n "$PROJECT_ZIP_URL" ]; then
        # Opção 2: Download do ZIP
        print_status "📦 Baixando arquivo ZIP: $PROJECT_ZIP_URL"
        cd /tmp
        wget -O scriptflow.zip "$PROJECT_ZIP_URL"
        unzip -q scriptflow.zip -d /tmp/scriptflow_temp
        
        # Encontrar diretório do projeto (pode estar dentro de subpasta)
        PROJECT_DIR=$(find /tmp/scriptflow_temp -name "scriptflow.py" -type f | head -1 | xargs dirname)
        if [ -z "$PROJECT_DIR" ]; then
            print_error "Arquivo scriptflow.py não encontrado no ZIP baixado!"
            exit 1
        fi
        
        cp -r "$PROJECT_DIR"/* "$SCRIPTFLOW_DIR/"
        rm -rf /tmp/scriptflow_temp /tmp/scriptflow.zip
        chown -R "$SCRIPTFLOW_USER:$SCRIPTFLOW_USER" "$SCRIPTFLOW_DIR"
        
    elif [ -f "./scriptflow.py" ]; then
        # Opção 3: Arquivos já estão no diretório atual
        print_status "📋 Copiando arquivos do diretório atual..."
        cp -r ./* "$SCRIPTFLOW_DIR/"
        chown -R "$SCRIPTFLOW_USER:$SCRIPTFLOW_USER" "$SCRIPTFLOW_DIR"
        
    else
        # Nenhuma opção configurada
        print_error "❌ Nenhuma fonte de arquivos configurada!"
        echo ""
        echo "Opções disponíveis:"
        echo "1. Configure GITHUB_REPO no início do script"
        echo "2. Configure PROJECT_ZIP_URL no início do script"  
        echo "3. Execute o script a partir do diretório que contém scriptflow.py"
        echo ""
        echo "Exemplo para GitHub:"
        echo "  GITHUB_REPO=\"https://github.com/usuario/scriptflow.git\""
        echo ""
        echo "Exemplo para ZIP:"
        echo "  PROJECT_ZIP_URL=\"https://exemplo.com/scriptflow.zip\""
        exit 1
    fi
    
    # Verificar se o download foi bem-sucedido
    if [ ! -f "$SCRIPTFLOW_DIR/scriptflow.py" ]; then
        print_error "Falha ao baixar/copiar arquivos do projeto!"
        exit 1
    fi
    
    print_success "Arquivos do projeto baixados com sucesso"
}

# 6. Baixar/copiar arquivos da aplicação
download_project

# 7. Configurar Python virtual environment
print_status "🐍 Configurando ambiente Python..."
sudo -u "$SCRIPTFLOW_USER" python3 -m venv "$SCRIPTFLOW_DIR/venv"
sudo -u "$SCRIPTFLOW_USER" "$SCRIPTFLOW_DIR/venv/bin/pip" install --upgrade pip
sudo -u "$SCRIPTFLOW_USER" "$SCRIPTFLOW_DIR/venv/bin/pip" install -r "$SCRIPTFLOW_DIR/requirements.txt"

# 8. Criar arquivo .env
print_status "⚙️  Criando configuração..."
cat > "$SCRIPTFLOW_DIR/.env" << EOF
# Configurações de Produção
SECRET_KEY=$SECRET_KEY
DATABASE_URL=sqlite:///instance/scriptflow.db
UPLOAD_FOLDER=uploads
PYTHON_EXECUTABLE=$SCRIPTFLOW_DIR/venv/bin/python
FLASK_ENV=production

# Configurações de Execução
MAX_CONCURRENT_SCRIPTS=10
SCRIPT_TIMEOUT=300

# Log Level
LOG_LEVEL=INFO
EOF

chown "$SCRIPTFLOW_USER:$SCRIPTFLOW_USER" "$SCRIPTFLOW_DIR/.env"
chmod 600 "$SCRIPTFLOW_DIR/.env"

# 9. Inicializar banco de dados
print_status "🗄️  Inicializando banco de dados..."
sudo -u "$SCRIPTFLOW_USER" bash -c "cd $SCRIPTFLOW_DIR && source venv/bin/activate && python -c \"
from scriptflow import app, db, User
from werkzeug.security import generate_password_hash
import os

with app.app_context():
    # Criar tabelas
    db.create_all()
    print('Tabelas criadas com sucesso')
    
    # Criar usuário admin se não existir
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@scriptflow.local',
            password_hash=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print('Usuário admin criado: admin/admin123')
    else:
        print('Usuário admin já existe')
\""

# 10. Configurar systemd service
print_status "🔧 Configurando serviço systemd..."
cp "$SCRIPTFLOW_DIR/deploy/scriptflow.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable scriptflow

# 11. Configurar Nginx
print_status "🌐 Configurando Nginx..."
cp "$SCRIPTFLOW_DIR/deploy/nginx_scriptflow" /etc/nginx/sites-available/scriptflow

# Substituir placeholder do domínio
sed -i "s/server_name _;/server_name $DOMAIN;/" /etc/nginx/sites-available/scriptflow

# Remover site padrão e ativar ScriptFlow
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/scriptflow /etc/nginx/sites-enabled/

# Testar configuração
nginx -t

# 12. Configurar firewall
print_status "🔥 Configurando firewall..."
ufw --force enable
ufw allow ssh
ufw allow 'Nginx Full'

# 13. Criar script de backup
print_status "💾 Configurando backup automático..."
cat > /opt/backup_scriptflow.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/scriptflow"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup do banco de dados
cp /opt/scriptflow/instance/scriptflow.db $BACKUP_DIR/scriptflow_db_$DATE.db

# Backup dos scripts
tar -czf $BACKUP_DIR/scripts_$DATE.tar.gz /opt/scriptflow/uploads/ 2>/dev/null

# Manter apenas últimos 7 backups
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "$(date): Backup concluído" >> /var/log/scriptflow_backup.log
EOF

chmod +x /opt/backup_scriptflow.sh

# Adicionar ao crontab
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/backup_scriptflow.sh") | crontab -

# 14. Iniciar serviços
print_status "🚀 Iniciando serviços..."
systemctl start scriptflow
systemctl restart nginx

# 15. Verificar status
sleep 3
print_status "🔍 Verificando status dos serviços..."

if systemctl is-active --quiet scriptflow; then
    print_success "ScriptFlow está rodando"
else
    print_error "Falha ao iniciar ScriptFlow"
    systemctl status scriptflow --no-pager
fi

if systemctl is-active --quiet nginx; then
    print_success "Nginx está rodando"
else
    print_error "Falha ao iniciar Nginx"
    systemctl status nginx --no-pager
fi

# 16. Testar aplicação
print_status "🧪 Testando aplicação..."
sleep 2

if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|302"; then
    print_success "Aplicação respondendo corretamente"
else
    print_warning "Aplicação pode não estar respondendo corretamente"
fi

# 17. Informações finais
print_success "🎉 Instalação concluída com sucesso!"
echo ""
echo "=================================================="
echo "          SCRIPTFLOW INSTALADO COM SUCESSO       "
echo "=================================================="
echo ""
echo "🌐 Acesso:"
echo "   URL: http://$DOMAIN"
echo "   Login: admin"
echo "   Senha: admin123"
echo ""
echo "📋 Comandos úteis:"
echo "   Status: sudo systemctl status scriptflow"
echo "   Logs: sudo journalctl -u scriptflow -f"
echo "   Reiniciar: sudo systemctl restart scriptflow"
echo ""
echo "🔧 Arquivos importantes:"
echo "   Aplicação: $SCRIPTFLOW_DIR"
echo "   Logs: $SCRIPTFLOW_DIR/logs"
echo "   Backups: /opt/backups/scriptflow"
echo "   Configuração: $SCRIPTFLOW_DIR/.env"
echo ""
echo "⚠️  IMPORTANTE:"
echo "   1. Altere a senha padrão após o primeiro login"
echo "   2. Configure SSL/HTTPS para produção"
echo "   3. Ajuste o domínio na configuração do Nginx"
echo ""

# Verificação final
print_status "📊 Status final dos serviços:"
systemctl status scriptflow --no-pager -l
echo ""
systemctl status nginx --no-pager -l

print_success "Deploy concluído! Acesse http://$DOMAIN para usar o ScriptFlow"