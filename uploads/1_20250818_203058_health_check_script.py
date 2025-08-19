#!/usr/bin/env python3
"""
Health Check Ultra Rápido - API Agrométrika
==========================================

Verificação de saúde de 10 segundos da API.
Ideal para monitoramento contínuo ou verificação antes de automações.

Uso:
    python health_check.py

Códigos de saída:
    0 = Tudo OK
    1 = Problema detectado
"""

import requests
import sys
from datetime import datetime

def health_check():
    """
    Verificação ultra rápida da API (10 segundos)
    """
    base_url = "https://sistema.agrometrikaweb.com.br/APIv2"
    auth_id = "c8db5f5b-103d-417d-a193-df252004b88b"
    auth_key = "TjTDQMqHcNk8hUpbEmnR8MbIU2ZdqtaFIW8PPOhBpU9lUA9ozC2jMC2hhlTXWmq"
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        # Teste básico de autenticação com timeout baixo
        response = requests.post(
            f"{base_url}/Autenticacao",
            json={"ID": auth_id, "Chave": auth_key},
            headers={"Content-Type": "application/json"},
            timeout=8  # 8 segundos máximo
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("Autenticado", False):
                print(f"✅ {timestamp} - API Agrométrika: SAUDÁVEL")
                return True
            else:
                print(f"❌ {timestamp} - API Agrométrika: FALHA AUTENTICAÇÃO")
                return False
        else:
            print(f"❌ {timestamp} - API Agrométrika: STATUS {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"⏱️ {timestamp} - API Agrométrika: TIMEOUT")
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"🌐 {timestamp} - API Agrométrika: ERRO CONEXÃO")
        return False
        
    except Exception as e:
        print(f"💥 {timestamp} - API Agrométrika: ERRO GERAL")
        return False


if __name__ == "__main__":
    success = health_check()
    sys.exit(0 if success else 1)
