# Informações do Banco de Dados - ScriptFlow

## ✅ Correção Realizada: Banco de Dados Unificado

### Problema Anterior:
- **Dois bancos SQLite**: `scriptflow.db` (raiz) e `instance/scriptflow.db`
- **Configuração incorreta**: Código apontava para `sqlite:///scriptflow.db` 
- **Banco real**: Flask usava `instance/scriptflow.db` por padrão
- **Inconsistência**: Dados reais em `instance/`, configuração apontava para raiz

### Solução Implementada:

1. **Configuração Corrigida**:
   - ✅ `scriptflow.py`: Atualizado para `sqlite:///instance/scriptflow.db`
   - ✅ `scriptflow_with_templates.py`: Atualizado para `sqlite:///instance/scriptflow.db`

2. **Banco Consolidado**:
   - ✅ **Removido**: `scriptflow.db` (raiz) - continha apenas jobs do APScheduler
   - ✅ **Mantido**: `instance/scriptflow.db` - contém todos os dados reais
   - ✅ **Dados preservados**: Usuários, scripts, schedules, execuções

### Estrutura Atual:

```
/task_app/
├── instance/
│   └── scriptflow.db        ← ÚNICO BANCO DE DADOS (SEMPRE AQUI!)
├── scriptflow.py            ← Config: sqlite:///scriptflow.db + app.instance_relative_config = True
└── scriptflow_with_templates.py ← Config: sqlite:///scriptflow.db + app.instance_relative_config = True
```

### ⚠️ REGRA FUNDAMENTAL:
**NUNCA** criar bancos na raiz! **SEMPRE** usar `instance/scriptflow.db`
- ✅ Configuração: `sqlite:///scriptflow.db` + `app.instance_relative_config = True`
- ❌ **NUNCA**: Caminhos absolutos que possam criar bancos na raiz

### Vantagens da Correção:

- ✅ **Eliminação de confusão**: Apenas um banco de dados
- ✅ **Consistência**: Código e realidade alinhados
- ✅ **Segurança**: Diretório `instance/` é padrão Flask para dados
- ✅ **Manutenção**: Mais fácil backup e migração
- ✅ **Performance**: Sem riscos de dados divididos

### Informações Técnicas:

- **Localização**: `/Users/cmorafre/Development/projects/task_app/instance/scriptflow.db`
- **Tamanho**: ~36KB
- **Conteúdo**: 1 usuário, 3 scripts, schedules e execuções
- **Engine**: SQLite 3
- **Acesso**: Apenas via aplicação Flask

### Backup e Manutenção:

```bash
# Backup do banco
cp instance/scriptflow.db instance/scriptflow_backup_$(date +%Y%m%d).db

# Verificar integridade
sqlite3 instance/scriptflow.db "PRAGMA integrity_check;"

# Ver tabelas
sqlite3 instance/scriptflow.db ".tables"
```

---
**Data da Correção**: 18/08/2025  
**Status**: ✅ Resolvido - Banco único configurado corretamente