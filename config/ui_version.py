"""
UI Version Management
Controla qual versão da interface será exibida
"""

import os
from flask import session, request

class UIVersionManager:
    """Gerencia a versão da UI que será exibida"""
    
    DEFAULT_VERSION = 'v1'  # Layout Bootstrap atual
    MODERN_VERSION = 'v2'   # Layout ShadcnUI moderno
    
    @classmethod
    def get_ui_version(cls):
        """
        Determina qual versão da UI usar baseado em:
        1. Parâmetro na URL (?ui=v2)  
        2. Sessão do usuário
        3. Variável de ambiente
        4. Padrão (v1)
        """
        
        # 1. URL parameter tem prioridade máxima
        if request and request.args.get('ui') in ['v1', 'v2']:
            ui_version = request.args.get('ui')
            if session:
                session['ui_version'] = ui_version
            return ui_version
        
        # 2. Sessão do usuário
        if session and 'ui_version' in session:
            return session['ui_version']
        
        # 3. Variável de ambiente (para deploy)
        env_version = os.environ.get('UI_VERSION', '').lower()
        if env_version in ['v1', 'v2']:
            return env_version
            
        # 4. Padrão
        return cls.DEFAULT_VERSION
    
    @classmethod
    def get_template_path(cls, template_name):
        """
        Retorna o caminho correto do template baseado na versão
        
        Args:
            template_name (str): Nome do template (ex: 'dashboard.html')
            
        Returns:
            str: Caminho completo (ex: 'v2/dashboard.html')
        """
        ui_version = cls.get_ui_version()
        return f"{ui_version}/{template_name}"
    
    @classmethod 
    def is_modern_ui(cls):
        """Verifica se está usando a UI moderna (v2)"""
        return cls.get_ui_version() == cls.MODERN_VERSION
    
    @classmethod
    def toggle_version(cls):
        """Alterna entre v1 e v2"""
        current = cls.get_ui_version()
        new_version = cls.MODERN_VERSION if current == cls.DEFAULT_VERSION else cls.DEFAULT_VERSION
        if session:
            session['ui_version'] = new_version
        return new_version
    
    @classmethod
    def get_ui_display_info(cls):
        """Retorna informações para exibição no template"""
        current_version = cls.get_ui_version()
        is_v2 = current_version == cls.MODERN_VERSION
        
        return {
            'current_version': current_version,
            'current_label': 'v2 (Modern)' if is_v2 else 'v1 (Bootstrap)',
            'current_icon': 'bi-stars' if is_v2 else 'bi-bootstrap',
            'is_modern': is_v2,
            'switch_to_version': cls.DEFAULT_VERSION if is_v2 else cls.MODERN_VERSION,
            'switch_to_label': 'Switch to v1 (Bootstrap)' if is_v2 else 'Switch to v2 (Modern)',
            'switch_to_icon': 'bi-bootstrap' if is_v2 else 'bi-stars'
        }