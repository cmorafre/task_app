# 🚀 Como Fazer Deploy do ScriptFlow no Ubuntu

Este documento explica de forma simples e direta como instalar o ScriptFlow em um servidor Ubuntu usando os scripts automatizados.

## 📋 Pré-requisitos

- Servidor Ubuntu 20.04+ ou 22.04+
- Acesso root (sudo)
- Conexão com internet

## 🎯 Escolha Sua Forma de Deploy

### **🔥 Opção 1: Deploy Automático do GitHub (RECOMENDADO)**

Esta é a forma mais fácil e rápida. O script baixa tudo automaticamente do GitHub.

#### **Passo 1: Publique o Projeto no GitHub**
1. Crie um repositório no GitHub (público ou privado)
2. Faça upload de todos os arquivos do ScriptFlow
3. Anote a URL do repositório (ex: `https://github.com/usuario/scriptflow.git`)

#### **Passo 2: Execute o Deploy**

**Método A - Uma Linha (se repositório for público):**
```bash
# Substitua SEU-USUARIO pelo seu usuário do GitHub
curl -sSL https://raw.githubusercontent.com/SEU-USUARIO/scriptflow/main/deploy/quick_deploy.sh | sudo bash
```

**Método B - Download e Configuração:**
```bash
# 1. Baixar o script
wget https://raw.githubusercontent.com/SEU-USUARIO/scriptflow/main/deploy/quick_deploy.sh

# 2. Editar configurações
nano quick_deploy.sh

# 3. Alterar esta linha:
# GITHUB_REPO="https://github.com/SEU-USUARIO/scriptflow.git"

# 4. Executar
sudo chmod +x quick_deploy.sh
sudo ./quick_deploy.sh
```

#### **O que acontece automaticamente:**
- ✅ Instala todas as dependências
- ✅ Baixa o projeto do GitHub
- ✅ Configura usuário e ambiente
- ✅ Instala Python e bibliotecas
- ✅ Configura banco de dados
- ✅ Configura Nginx e systemd
- ✅ Testa tudo e informa o resultado

---

### **📦 Opção 2: Deploy com Arquivos Locais**

Use esta opção se não quiser usar GitHub ou se tiver arquivos customizados.

#### **Passo 1: Preparar Arquivos**
No seu computador, compacte os arquivos:
```bash
tar -czf scriptflow.tar.gz *.py *.txt templates/ static/ uploads/ logs/ instance/ deploy/
```

#### **Passo 2: Enviar para o Servidor**
```bash
# Substitua 'usuario' e 'seu-servidor' pelos valores corretos
scp scriptflow.tar.gz usuario@seu-servidor:/tmp/
```

#### **Passo 3: Instalar no Servidor**
```bash
# Conectar no servidor via SSH
ssh usuario@seu-servidor

# Descompactar arquivos
cd /tmp
tar -xzf scriptflow.tar.gz

# Executar instalação
sudo ./deploy/deploy_ubuntu.sh
```

---

### **🔧 Opção 3: Clone Manual do Git**

Se preferir fazer clone manual primeiro:

```bash
# 1. Clonar repositório
git clone https://github.com/SEU-USUARIO/scriptflow.git
cd scriptflow

# 2. Executar deploy
sudo ./deploy/deploy_ubuntu.sh
```

---

## 🎉 Após a Instalação

### **Acessar a Aplicação**
1. Abra o navegador
2. Acesse: `http://SEU-SERVIDOR-IP`
3. **Login padrão:**
   - **Usuário:** `admin`
   - **Senha:** `admin123`

### **Verificar Status**
```bash
# Status do serviço
sudo systemctl status scriptflow

# Logs em tempo real
sudo journalctl -u scriptflow -f

# Status do Nginx
sudo systemctl status nginx
```

### **Comandos Úteis**
```bash
# Reiniciar aplicação
sudo systemctl restart scriptflow

# Parar aplicação
sudo systemctl stop scriptflow

# Iniciar aplicação
sudo systemctl start scriptflow

# Ver logs dos últimos minutos
sudo journalctl -u scriptflow -n 50
```

---

## 🔧 Personalização e Configuração

### **Alterar Configurações**
Edite o arquivo de configuração:
```bash
sudo nano /opt/scriptflow/.env
```

**Principais configurações:**
- `SECRET_KEY`: Chave de segurança (altere em produção)
- `DOMAIN`: Seu domínio ou IP
- `MAX_CONCURRENT_SCRIPTS`: Máximo de scripts simultâneos
- `SCRIPT_TIMEOUT`: Timeout dos scripts em segundos

### **Configurar Domínio Personalizado**
```bash
# Editar configuração do Nginx
sudo nano /etc/nginx/sites-available/scriptflow

# Alterar linha:
# server_name SEU-DOMINIO.com;

# Reiniciar Nginx
sudo systemctl restart nginx
```

### **Configurar SSL/HTTPS**
```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx

# Obter certificado (substitua pelo seu domínio)
sudo certbot --nginx -d seu-dominio.com

# Verificar renovação automática
sudo certbot renew --dry-run
```

---

## 🛠️ Resolução de Problemas

### **Aplicação não inicia**
```bash
# Ver logs detalhados
sudo journalctl -u scriptflow -n 100

# Verificar permissões
sudo chown -R scriptflow:scriptflow /opt/scriptflow

# Testar manualmente
sudo su - scriptflow
cd /opt/scriptflow
source venv/bin/activate
python scriptflow.py
```

### **Não consegue acessar pelo navegador**
```bash
# Verificar se está rodando
sudo netstat -tulpn | grep 5000

# Verificar firewall
sudo ufw status

# Testar localmente
curl http://localhost
```

### **Problemas com uploads**
```bash
# Verificar permissões
sudo chmod 755 /opt/scriptflow/uploads
sudo chown scriptflow:scriptflow /opt/scriptflow/uploads
```

### **Scripts não executam**
```bash
# Verificar Python
sudo su - scriptflow
cd /opt/scriptflow
source venv/bin/activate
python --version

# Testar Python
python -c "print('Python funcionando')"
```

---

## 📊 Monitoramento e Manutenção

### **Backup Automático**
O script já configura backup automático diário:
```bash
# Ver backups
ls -la /opt/backups/scriptflow/

# Executar backup manual
sudo /opt/backup_scriptflow.sh
```

### **Atualizar Aplicação**
```bash
# Parar serviço
sudo systemctl stop scriptflow

# Fazer backup
sudo cp -r /opt/scriptflow /opt/scriptflow_backup_$(date +%Y%m%d)

# Baixar nova versão (GitHub)
cd /tmp
git clone https://github.com/SEU-USUARIO/scriptflow.git scriptflow_new
sudo cp -r scriptflow_new/* /opt/scriptflow/
sudo chown -R scriptflow:scriptflow /opt/scriptflow

# Atualizar dependências
sudo su - scriptflow
cd /opt/scriptflow
source venv/bin/activate
pip install -r requirements.txt

# Reiniciar
sudo systemctl start scriptflow
```

### **Ver Uso de Recursos**
```bash
# CPU e memória
htop

# Espaço em disco
df -h

# Logs de sistema
sudo journalctl -f
```

---

## 🔐 Segurança Recomendada

### **Alterar Senha Padrão**
1. Acesse a aplicação
2. Vá em **Settings > Users**
3. Altere a senha do usuário `admin`

### **Configurar Firewall**
```bash
# Verificar regras
sudo ufw status

# Permitir apenas portas necessárias
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### **Atualizar Sistema**
```bash
# Atualizações de segurança
sudo apt update && sudo apt upgrade -y

# Reiniciar se necessário
sudo reboot
```

---

## ❓ Perguntas Frequentes

### **Q: O script funciona em outras distribuições Linux?**
A: O script foi testado no Ubuntu 20.04+ e 22.04+. Pode funcionar em Debian, mas não é garantido.

### **Q: Posso usar PostgreSQL ao invés de SQLite?**
A: Sim, edite o arquivo `.env` e altere a `DATABASE_URL` para PostgreSQL.

### **Q: Como fazer backup manual?**
A: Execute `sudo /opt/backup_scriptflow.sh` ou copie os diretórios `/opt/scriptflow/instance` e `/opt/scriptflow/uploads`.

### **Q: Posso executar na porta 80 diretamente?**
A: Não recomendado. Use Nginx como proxy reverso (já configurado) para melhor segurança e performance.

### **Q: Como ver quais scripts estão executando?**
A: Acesse a aplicação web ou execute `ps aux | grep python`.

---

## 📞 Ajuda e Suporte

### **Logs Importantes:**
- **Aplicação:** `sudo journalctl -u scriptflow -f`
- **Nginx:** `sudo tail -f /var/log/nginx/scriptflow_error.log`
- **Sistema:** `sudo tail -f /var/log/syslog`

### **Teste de Conectividade:**
```bash
# Teste local
curl http://localhost

# Teste específico
curl -I http://localhost/health

# Teste com domínio
curl -I http://seu-dominio.com
```

### **Reinstalação Completa:**
```bash
# Remover tudo
sudo systemctl stop scriptflow
sudo rm -rf /opt/scriptflow
sudo userdel scriptflow
sudo rm /etc/systemd/system/scriptflow.service
sudo rm /etc/nginx/sites-available/scriptflow
sudo rm /etc/nginx/sites-enabled/scriptflow

# Executar script novamente
sudo ./deploy/deploy_ubuntu.sh
```

---

## ✅ Checklist Final

Após a instalação, verifique:

- [ ] ✅ Aplicação acessível via navegador
- [ ] ✅ Login com admin/admin123 funciona
- [ ] ✅ Upload de script .py funciona
- [ ] ✅ Execução de script funciona
- [ ] ✅ Logs aparecem na interface
- [ ] ✅ Serviço reinicia automaticamente (`sudo reboot` + teste)
- [ ] ✅ Senha padrão foi alterada
- [ ] ✅ Domínio configurado (se aplicável)
- [ ] ✅ SSL configurado (se aplicável)
- [ ] ✅ Firewall ativo e configurado
- [ ] ✅ Backup funcionando

---

🎉 **Parabéns! Seu ScriptFlow está rodando em produção!**

**Próximos passos sugeridos:**
1. Altere a senha padrão
2. Configure seu domínio
3. Configure SSL/HTTPS
4. Faça upload de seus primeiros scripts
5. Configure agendamentos automáticos

**Happy Automating!** 🚀