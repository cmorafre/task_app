# 🚀 ScriptFlow - Guia de Deploy no Ubuntu

Este guia detalha como instalar e configurar o ScriptFlow em um servidor Ubuntu para produção.

## 📋 Pré-requisitos

- Ubuntu 20.04+ ou 22.04+
- Acesso root ou sudo
- Conexão com internet

## 🔧 Passo a Passo Completo

### 1. Atualizar o Sistema

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Instalar Dependências do Sistema

```bash
# Instalar Python 3.9+ e pip
sudo apt install python3 python3-pip python3-venv python3-dev -y

# Instalar Nginx (servidor web)
sudo apt install nginx -y

# Instalar supervisor ou systemd (para gerenciar o processo)
sudo apt install supervisor -y

# Instalar Git (se necessário)
sudo apt install git -y

# Verificar versões instaladas
python3 --version
pip3 --version
nginx -v
```

### 3. Criar Usuário para a Aplicação

```bash
# Criar usuário dedicado para a aplicação
sudo adduser --system --group --home /opt/scriptflow scriptflow

# Criar diretório da aplicação
sudo mkdir -p /opt/scriptflow
sudo chown scriptflow:scriptflow /opt/scriptflow
```

### 4. Fazer Upload dos Arquivos

## 🚀 Opções de Deploy

### **Opção A: Deploy Automático do GitHub (Recomendado)**

1. **Publique seu projeto no GitHub**
2. **Configure o script** `deploy/quick_deploy.sh`:
   ```bash
   # Edite a linha:
   GITHUB_REPO="https://github.com/SEU-USUARIO/scriptflow.git"
   ```
3. **Execute no servidor Ubuntu**:
   ```bash
   # Baixar e executar em uma linha
   curl -sSL https://raw.githubusercontent.com/SEU-USUARIO/scriptflow/main/deploy/quick_deploy.sh | sudo bash
   
   # OU baixar, editar e executar
   wget https://raw.githubusercontent.com/SEU-USUARIO/scriptflow/main/deploy/quick_deploy.sh
   nano quick_deploy.sh  # Editar GITHUB_REPO
   sudo chmod +x quick_deploy.sh
   sudo ./quick_deploy.sh
   ```

### **Opção B: Deploy Manual com Arquivos Locais**

**Via SCP/SFTP:**
```bash
# No seu computador local
tar -czf scriptflow.tar.gz *.py *.txt templates/ static/ uploads/ logs/ instance/ deploy/

# Enviar para o servidor
scp scriptflow.tar.gz user@seu-servidor:/tmp/

# No servidor Ubuntu
cd /tmp
tar -xzf scriptflow.tar.gz
sudo ./deploy/deploy_ubuntu.sh
```

**Via Git Clone Manual:**
```bash
# No servidor Ubuntu
git clone https://github.com/seu-usuario/scriptflow.git /tmp/scriptflow
cd /tmp/scriptflow
sudo ./deploy/deploy_ubuntu.sh
```

### 5. Configurar Python Virtual Environment

```bash
# Mudar para usuário scriptflow
sudo su - scriptflow
cd /opt/scriptflow

# Criar ambiente virtual
python3 -m venv venv

# Ativar ambiente virtual
source venv/bin/activate

# Atualizar pip
pip install --upgrade pip

# Instalar dependências
pip install -r requirements.txt

# Verificar instalação
python -c "import flask; print('Flask instalado com sucesso')"
```

### 6. Configurar Variáveis de Ambiente

```bash
# Criar arquivo de configuração
sudo nano /opt/scriptflow/.env
```

**Conteúdo do arquivo .env:**
```bash
# Configurações de Produção
SECRET_KEY=sua-chave-secreta-super-forte-aqui-2024
DATABASE_URL=sqlite:///instance/scriptflow.db
UPLOAD_FOLDER=uploads
PYTHON_EXECUTABLE=/opt/scriptflow/venv/bin/python
FLASK_ENV=production

# Configurações de Email (opcional)
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USERNAME=seu-email@gmail.com
# SMTP_PASSWORD=sua-senha-app

# Configurações de Execução
MAX_CONCURRENT_SCRIPTS=10
SCRIPT_TIMEOUT=300
```

### 7. Inicializar Banco de Dados

```bash
# Ativar ambiente virtual
source /opt/scriptflow/venv/bin/activate

# Criar diretórios necessários
mkdir -p /opt/scriptflow/instance
mkdir -p /opt/scriptflow/uploads
mkdir -p /opt/scriptflow/logs

# Inicializar banco de dados
cd /opt/scriptflow
python scriptflow.py &
# Aguardar alguns segundos
sleep 5
# Parar o processo
pkill -f scriptflow.py

# Verificar se banco foi criado
ls -la instance/
```

### 8. Configurar Systemd Service

```bash
sudo nano /etc/systemd/system/scriptflow.service
```

**Conteúdo do arquivo scriptflow.service:**
```ini
[Unit]
Description=ScriptFlow - Script Automation Platform
After=network.target

[Service]
Type=simple
User=scriptflow
Group=scriptflow
WorkingDirectory=/opt/scriptflow
Environment=PATH=/opt/scriptflow/venv/bin
EnvironmentFile=/opt/scriptflow/.env
ExecStart=/opt/scriptflow/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 2 --timeout 300 scriptflow:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### 9. Configurar Nginx

```bash
# Backup da configuração padrão
sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup

# Criar configuração do ScriptFlow
sudo nano /etc/nginx/sites-available/scriptflow
```

**Conteúdo do arquivo scriptflow:**
```nginx
server {
    listen 80;
    server_name seu-dominio.com;  # Substituir pelo seu domínio ou IP
    
    # Logs
    access_log /var/log/nginx/scriptflow_access.log;
    error_log /var/log/nginx/scriptflow_error.log;
    
    # Upload file size limit
    client_max_body_size 50M;
    
    # Static files
    location /static {
        alias /opt/scriptflow/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Main application
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (se necessário no futuro)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

### 10. Ativar Configurações

```bash
# Habilitar site do ScriptFlow
sudo ln -s /etc/nginx/sites-available/scriptflow /etc/nginx/sites-enabled/

# Desabilitar site padrão
sudo rm /etc/nginx/sites-enabled/default

# Testar configuração do Nginx
sudo nginx -t

# Recarregar Nginx
sudo systemctl reload nginx

# Habilitar e iniciar ScriptFlow
sudo systemctl daemon-reload
sudo systemctl enable scriptflow
sudo systemctl start scriptflow

# Verificar status
sudo systemctl status scriptflow
sudo systemctl status nginx
```

### 11. Configurar Firewall (UFW)

```bash
# Habilitar UFW
sudo ufw enable

# Permitir SSH
sudo ufw allow ssh

# Permitir HTTP e HTTPS
sudo ufw allow 'Nginx Full'

# Verificar status
sudo ufw status
```

### 12. Configurar SSL com Let's Encrypt (Opcional mas Recomendado)

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obter certificado SSL
sudo certbot --nginx -d seu-dominio.com

# Verificar renovação automática
sudo certbot renew --dry-run
```

## 📊 Verificação da Instalação

### Testar a Aplicação

```bash
# Verificar se os serviços estão rodando
sudo systemctl status scriptflow
sudo systemctl status nginx

# Testar conexão local
curl -I http://localhost

# Verificar logs em tempo real
sudo journalctl -u scriptflow -f

# Verificar logs do Nginx
sudo tail -f /var/log/nginx/scriptflow_access.log
sudo tail -f /var/log/nginx/scriptflow_error.log
```

### Acessar a Aplicação

1. Abra o navegador
2. Acesse: `http://seu-servidor-ip` ou `https://seu-dominio.com`
3. Login padrão:
   - **Usuário**: `admin`
   - **Senha**: `admin123`

## 🔧 Comandos Úteis de Manutenção

### Gerenciar o Serviço

```bash
# Parar ScriptFlow
sudo systemctl stop scriptflow

# Iniciar ScriptFlow
sudo systemctl start scriptflow

# Reiniciar ScriptFlow
sudo systemctl restart scriptflow

# Ver logs do serviço
sudo journalctl -u scriptflow -n 50

# Ver status detalhado
sudo systemctl status scriptflow -l
```

### Atualizar a Aplicação

```bash
# Parar serviço
sudo systemctl stop scriptflow

# Fazer backup
sudo cp -r /opt/scriptflow /opt/scriptflow_backup_$(date +%Y%m%d)

# Atualizar arquivos (upload novos arquivos)
sudo su - scriptflow
cd /opt/scriptflow
source venv/bin/activate
pip install -r requirements.txt

# Reiniciar serviço
sudo systemctl start scriptflow
```

### Monitoramento

```bash
# Ver processos relacionados
ps aux | grep scriptflow

# Ver uso de recursos
htop

# Ver espaço em disco
df -h

# Ver logs de aplicação
tail -f /opt/scriptflow/logs/app.log  # se configurado
```

## 🔐 Segurança Adicional

### 1. Alterar Senha Padrão

1. Acesse a aplicação via browser
2. Vá em **Settings > Users**
3. Altere a senha do usuário `admin`

### 2. Configurar Backup Automático

```bash
# Criar script de backup
sudo nano /opt/backup_scriptflow.sh
```

**Conteúdo do script:**
```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/scriptflow"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup do banco de dados
cp /opt/scriptflow/instance/scriptflow.db $BACKUP_DIR/scriptflow_db_$DATE.db

# Backup dos scripts
tar -czf $BACKUP_DIR/scripts_$DATE.tar.gz /opt/scriptflow/uploads/

# Manter apenas últimos 7 backups
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup concluído: $DATE"
```

```bash
# Tornar executável
sudo chmod +x /opt/backup_scriptflow.sh

# Adicionar ao crontab para backup diário
sudo crontab -e
# Adicionar linha: 0 2 * * * /opt/backup_scriptflow.sh
```

## 🚨 Solução de Problemas

### Aplicação não inicia

```bash
# Verificar logs
sudo journalctl -u scriptflow -n 50

# Verificar permissões
ls -la /opt/scriptflow/
sudo chown -R scriptflow:scriptflow /opt/scriptflow/

# Testar manualmente
sudo su - scriptflow
cd /opt/scriptflow
source venv/bin/activate
python scriptflow.py
```

### Nginx não consegue acessar a aplicação

```bash
# Verificar se o ScriptFlow está rodando na porta 5000
netstat -tulpn | grep 5000

# Testar conexão direta
curl http://127.0.0.1:5000

# Verificar configuração do Nginx
sudo nginx -t
```

### Uploads não funcionam

```bash
# Verificar permissões do diretório uploads
ls -la /opt/scriptflow/uploads/
sudo chown -R scriptflow:scriptflow /opt/scriptflow/uploads/
sudo chmod 755 /opt/scriptflow/uploads/
```

## ✅ Checklist Final

- [ ] Aplicação acessível via browser
- [ ] Login com admin/admin123 funciona
- [ ] Upload de script funciona
- [ ] Execução de script funciona
- [ ] Logs aparecem corretamente
- [ ] Serviço reinicia automaticamente
- [ ] SSL configurado (se aplicável)
- [ ] Firewall configurado
- [ ] Backup configurado
- [ ] Senha padrão alterada

## 📞 Suporte

Se encontrar problemas durante a instalação:

1. Verifique os logs: `sudo journalctl -u scriptflow -f`
2. Teste a aplicação manualmente: `python scriptflow.py`
3. Verifique conectividade: `curl http://localhost:5000`

**🎉 Parabéns! Seu ScriptFlow está rodando em produção!**