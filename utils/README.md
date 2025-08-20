# Utils - ScriptFlow Utilities

Esta pasta contém scripts utilitários organizados por categoria para melhor manutenção do projeto ScriptFlow.

## 📁 Estrutura das Pastas

### 🛠️ `admin_tools/`
Scripts para administração e configuração do sistema:
- **`create_admin.py`** - Utilitário para criar usuários administradores

### 🧪 `testing/`
Scripts para testes e validação do sistema:
- **`test_config.py`** - Testa configurações de Python e dependências
- **`test_python_detection.py`** - Detecta interpretadores Python disponíveis no sistema
- **`test_script.py`** - Script simples de exemplo para testes de execução

### 📂 `deprecated/`
Scripts obsoletos mantidos para referência histórica:
- **`test_logs_improvements.py`** - Documentação de melhorias de logs (implementadas)
- **`test_new_delete_modal.py`** - Documentação de modal de exclusão (implementado)
- **`test_script_management.py`** - Documentação de funcionalidades (implementadas)
- **`test_settings_interface.py`** - Documentação de interface de configurações (implementada)

## 🚀 Como Usar

### Criar Admin User
```bash
cd /path/to/project
python utils/admin_tools/create_admin.py
```

### Testar Configurações
```bash
python utils/testing/test_config.py
python utils/testing/test_python_detection.py
```

### Script de Teste
```bash
python utils/testing/test_script.py
```

## 📝 Notas

- Scripts em `deprecated/` podem ser removidos em futuras versões
- Scripts em `admin_tools/` e `testing/` são mantidos e atualizados conforme necessário
- Esta organização melhora a estrutura do projeto mantendo a raiz limpa