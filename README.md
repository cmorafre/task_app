# ScriptFlow - Automation Made Simple

Sistema simples de automação de scripts Python e Batch.

## 🚀 Como Executar

Execute apenas um comando:

```bash
python3 scriptflow.py
```

A aplicação irá:
- ✅ Detectar automaticamente uma porta livre
- ✅ Criar o banco de dados SQLite
- ✅ Criar usuário admin padrão
- ✅ Iniciar o servidor web

## 📍 Acesso

- **URL**: `http://localhost:[porta-detectada]`
- **Usuário**: `admin`
- **Senha**: `admin123`

## 📋 Funcionalidades

- 📁 Upload de scripts Python (.py) e Batch (.bat)
- ▶️ Execução manual de scripts
- 📊 Dashboard com estatísticas
- 📝 Logs detalhados de execuções
- 🎨 Interface responsiva Bootstrap

## 🛠️ Requisitos

```bash
pip install flask flask-sqlalchemy flask-login python-dotenv
```

## 📁 Estrutura

```
task_app/
├── scriptflow.py          # ← EXECUTAR ESTE ARQUIVO
├── uploads/              # Scripts enviados
├── logs/                 # Logs da aplicação
├── scriptflow.db         # Banco SQLite (criado automaticamente)
└── docs/                 # Documentação
```

## ✨ Características

- 🔧 **Autocontido**: Todos os templates e configurações inclusos
- 🚀 **Zero configuração**: Funciona imediatamente
- 🔍 **Auto-detecção**: Encontra porta livre automaticamente
- 📱 **Responsivo**: Interface Bootstrap adaptativa
- 🔐 **Seguro**: Execução isolada de scripts

---

**Desenvolvido conforme especificações dos documentos PRD, Architecture e UX.**