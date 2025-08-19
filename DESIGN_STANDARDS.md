# PADRÕES DE DESIGN - ScriptFlow

## ⚠️ IMPORTANTE: SEMPRE MANTER CONSISTÊNCIA VISUAL

### 🔘 BOTÕES
- **Border-radius**: 6px (SEMPRE)
- **Font-weight**: 600 (SEMPRE)
- **Transition**: all 0.3s ease (SEMPRE)
- **Border**: 2px solid (para ações principais)
- **Padding padrão**: 0.4rem 0.8rem
- **Font-size padrão**: 0.9rem
- **Margin entre botões**: 3px

### 📦 CARDS E CONTAINERS
- **Border-radius**: 8px (SEMPRE)
- **Box-shadow**: 0 2px 4px rgba(0,0,0,0.1)
- **Border**: none

### 🏷️ BADGES E ALERTS
- **Border-radius**: 8px (SEMPRE)
- **Font-weight**: 600
- **Padding**: 0.5em 0.8em

### 📝 FORM ELEMENTS
- **Border-radius**: 6px (SEMPRE)
- **Border**: 1px solid padrão Bootstrap

### 🎨 CORES PADRÃO
- **Primary**: #0d6efd
- **Success**: #28a745
- **Warning**: #ffc107
- **Danger**: #dc3545
- **Secondary**: #6c757d
- **Info**: #17a2b8

### 🎯 STATUS RUNNING
- **Background**: linear-gradient(45deg, #ff6b00, #ff8c00)
- **Color**: white
- **Animation**: pulse 1.5s infinite
- **Icon**: rotating arrow-clockwise

### ✨ EFEITOS HOVER
- **Transform**: translateY(-2px)
- **Box-shadow**: 0 4px 12px rgba(cor-principal, 0.4)
- **Cores**: ligeiramente mais escuras

## 🚫 NUNCA FAZER
- Botões com border-radius diferentes na mesma página
- Cards com cantos diferentes
- Botões sem transition
- Cores inconsistentes para a mesma ação
- Font-weights diferentes para elementos similares

## ✅ SEMPRE VERIFICAR
1. Todos os botões têm border-radius: 6px
2. Todos os cards têm border-radius: 8px
3. Cores consistentes entre páginas
4. Efeitos hover padronizados
5. Espaçamentos uniformes