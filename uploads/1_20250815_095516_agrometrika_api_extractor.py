import requests
import time
import pandas as pd
from datetime import datetime
import logging
from typing import Dict, List, Optional, Tuple

# EXTRATOR DE DADOS - API AGROMÉTRIKA
# ===================================
# 
# Script simplificado para extração de dados da API Agrométrika
# RelatorioId configurado: "21d23caa-8dc9-4717-9d0a-6e28653915dc"
#
# Funcionalidades:
# • Autenticação automática na API
# • Extração paginada de dados
# • Salvamento em formato Excel (.xlsx)
# • Suporte à estrutura de dados da Agrométrika
#
# Dependências: requests, pandas, openpyxl
#
# USO SIMPLES:
#   python agrometrika_api_extractor.py
#
# RESULTADO:
#   Arquivo Excel salvo com timestamp: agrometrika_data_YYYYMMDD_HHMMSS.xlsx

class AgrometrikaAPI:
    """
    Classe para interação com a API da Agrométrika
    """
    
    def __init__(self, default_report_id: str = None):
        self.base_url = "https://sistema.agrometrikaweb.com.br/APIv2"
        self.auth_id = "c8db5f5b-103d-417d-a193-df252004b88b"
        self.auth_key = "TjTDQMqHcNk8hUpbEmnR8MbIU2ZdqtaFIW8PPOhBpU9lUA9ozC2jMC2hhlTXWmq"
        self.token = None
        # ID do relatório específico identificado (pode ser definido diretamente)
        self.default_report_id = default_report_id or "21d23caa-8dc9-4717-9d0a-6e28653915dc"
        
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('agrometrika_extraction.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def authenticate(self) -> bool:
        """
        Realiza autenticação na API e obtém o token
        Returns: True se autenticação foi bem-sucedida, False caso contrário
        """
        url = f"{self.base_url}/Autenticacao"
        payload = {
            "ID": self.auth_id,
            "Chave": self.auth_key
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            self.logger.info("Iniciando autenticação na API...")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("Autenticado", False):
                    self.token = data.get("Token")
                    self.logger.info("Autenticação realizada com sucesso!")
                    return True
                else:
                    self.logger.error("Falha na autenticação: Token não recebido")
                    return False
            else:
                self.logger.error(f"Erro na autenticação. Status: {response.status_code}")
                self.logger.error(f"Resposta: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erro de conexão durante autenticação: {str(e)}")
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Retorna headers com token de autenticação
        """
        if not self.token:
            raise ValueError("Token não disponível. Execute authenticate() primeiro.")
        
        return {
            "Content-Type": "application/json",
            "X-Authentication-Token": self.token
        }
    
    def get_custom_reports(self) -> Optional[List[Dict]]:
        """
        Obtém lista de relatórios personalizados disponíveis
        Returns: Lista de relatórios ou None em caso de erro
        """
        url = f"{self.base_url}/Relatorios/Personalizado"
        
        try:
            self.logger.info("Obtendo lista de relatórios personalizados...")
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"Encontrados {len(data)} relatórios personalizados")
                return data
            else:
                self.logger.error(f"Erro ao obter relatórios. Status: {response.status_code}")
                self.logger.error(f"Resposta: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erro de conexão ao obter relatórios: {str(e)}")
            return None
    
    def extract_report_data(self, report_id: str = None, delay_between_pages: int = 2) -> Tuple[List[Dict], bool]:
        """
        Extrai dados de um relatório específico, página por página
        Se report_id não for fornecido, usa automaticamente o único relatório disponível
        
        Args:
            report_id: ID do relatório personalizado (opcional - usa o único disponível se None)
            delay_between_pages: Delay em segundos entre requisições de páginas
            
        Returns: Tupla com (lista de dados, sucesso)
        """
        # Se report_id não foi fornecido, usar o default_report_id ou buscar automaticamente
        if report_id is None:
            if self.default_report_id:
                self.logger.info(f"🎯 Usando relatório padrão configurado: {self.default_report_id}")
                report_id = self.default_report_id
            else:
                self.logger.info("🔍 Report ID não fornecido, buscando relatório disponível...")
                reports = self.get_custom_reports()
                if not reports:
                    self.logger.error("❌ Nenhum relatório personalizado encontrado")
                    return [], False
                
                if len(reports) > 1:
                    self.logger.warning(f"⚠️ Encontrados {len(reports)} relatórios, usando o primeiro")
                
                # Verificar se a resposta tem estrutura aninhada da Agrométrika
                reports_list = None
                if isinstance(reports, dict) and "Relatorios" in reports:
                    self.logger.info("🎯 Estrutura Agrométrika detectada - chave 'Relatorios'")
                    reports_list = reports["Relatorios"]
                elif isinstance(reports, list):
                    reports_list = reports
                else:
                    self.logger.error("❌ Estrutura de resposta não reconhecida")
                    return [], False
                
                if not reports_list or len(reports_list) == 0:
                    self.logger.error("❌ Lista de relatórios está vazia")
                    return [], False
                
                # Extrair ID do primeiro (e provavelmente único) relatório
                report = reports_list[0]
                # Usar a mesma ordem de prioridade do quick_test_script.py
                report_id = report.get('RelatorioId') or report.get('id') or report.get('RelatorioPersonalizadoId')
                report_name = report.get('Nome') or report.get('nome') or report.get('NomeRelatorio', 'Relatório')
                
                if not report_id:
                    self.logger.error("❌ Não foi possível extrair o ID do relatório")
                    return [], False
                
                self.logger.info(f"📊 Usando relatório: {report_name} (ID: {report_id})")
        
        # Continuar com a extração normal...
        all_data = []
        current_page = 1
        total_pages = None
        
        self.logger.info(f"Iniciando extração do relatório ID: {report_id}")
        
        while True:
            url = f"{self.base_url}/Relatorios/Personalizado/{report_id}"
            params = {"numPagina": current_page}
            
            try:
                self.logger.info(f"Extraindo página {current_page}" + 
                               (f" de {total_pages}" if total_pages else ""))
                
                response = requests.get(
                    url, 
                    headers=self._get_headers(), 
                    params=params, 
                    timeout=60
                )
                
                if response.status_code == 200:
                    # Extrair dados da resposta
                    page_data = response.json()
                    
                    # Processar dados baseado na estrutura da Agrométrika
                    records_count = 0
                    if isinstance(page_data, list):
                        # Lista direta de dados
                        all_data.extend(page_data)
                        records_count = len(page_data)
                    elif isinstance(page_data, dict):
                        # Verificar se tem estrutura aninhada da Agrométrika
                        if 'Dados' in page_data and isinstance(page_data['Dados'], list):
                            # Estrutura: {'Dados': [...], 'Salvo': true, ...}
                            dados = page_data['Dados']
                            all_data.extend(dados)
                            records_count = len(dados)
                            self.logger.info(f"Estrutura Agrométrika detectada - Salvo: {page_data.get('Salvo')}")
                        else:
                            # Estrutura desconhecida, adicionar como objeto único
                            all_data.append(page_data)
                            records_count = 1
                    
                    # Extrair informações de paginação do header
                    headers = response.headers
                    total_pages_header = headers.get('Total-Paginas')
                    next_page_header = headers.get('Proxima-Pagina')
                    
                    if total_pages_header:
                        total_pages = int(total_pages_header)
                    
                    self.logger.info(f"Página {current_page} extraída com sucesso. "
                                   f"Registros nesta página: {records_count}")
                    
                    # Verificar se há próxima página
                    if not next_page_header or current_page >= (total_pages or float('inf')):
                        self.logger.info("Última página atingida. Extração concluída.")
                        break
                    
                    # Aguardar antes da próxima requisição (IMPORTANTE conforme instruções)
                    if delay_between_pages > 0:
                        self.logger.info(f"Aguardando {delay_between_pages} segundos antes da próxima página...")
                        time.sleep(delay_between_pages)
                    
                    current_page += 1
                    
                else:
                    self.logger.error(f"Erro ao extrair página {current_page}. Status: {response.status_code}")
                    self.logger.error(f"Resposta: {response.text}")
                    return all_data, False
                    
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Erro de conexão na página {current_page}: {str(e)}")
                return all_data, False
        
        self.logger.info(f"Extração concluída! Total de registros: {len(all_data)}")
        return all_data, True
    
    def save_data_to_excel(self, data: List[Dict], filename: str = None) -> str:
        """
        Salva dados em arquivo Excel (.xlsx)
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"agrometrika_data_{timestamp}.xlsx"
        
        try:
            if data:
                df = pd.DataFrame(data)
                
                # Salvar em Excel com formatação básica
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Dados_Agrometrika', index=False)
                    
                    # Obter a planilha para formatação adicional
                    worksheet = writer.sheets['Dados_Agrometrika']
                    
                    # Ajustar largura das colunas automaticamente
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        
                        adjusted_width = min(max_length + 2, 50)  # Máximo 50 caracteres
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                
                self.logger.info(f"Dados salvos em Excel: {filename}")
                return filename
            else:
                self.logger.warning("Nenhum dado para salvar")
                return None
                
        except Exception as e:
            self.logger.error(f"Erro ao salvar arquivo Excel: {str(e)}")
            raise


def main():
    """
    Função principal para extração de dados da API Agrométrika
    """
    print("🚀 EXTRAÇÃO DE DADOS - API AGROMÉTRIKA")
    print("=" * 50)
    
    # Inicializar API com relatório específico identificado
    api = AgrometrikaAPI(default_report_id="21d23caa-8dc9-4717-9d0a-6e28653915dc")
    
    # Passo 1: Autenticar
    print("🔐 Autenticando na API...")
    if not api.authenticate():
        print("❌ Falha na autenticação. Verifique as credenciais.")
        return
    print("✅ Autenticação realizada com sucesso!")
    
    # Passo 2: Extrair dados do relatório configurado
    print(f"\n🔄 Extraindo dados do relatório: {api.default_report_id}")
    data, success = api.extract_report_data(delay_between_pages=3)
    
    if success and data:
        print(f"\n🎉 Extração concluída com sucesso!")
        print(f"📈 Total de registros extraídos: {len(data)}")
        
        # Passo 3: Salvar dados em Excel
        try:
            excel_file = api.save_data_to_excel(data)
            
            print(f"\n💾 Arquivo salvo:")
            print(f"   📊 Excel: {excel_file}")
            
            # Mostrar preview dos dados
            print(f"\n👀 Preview dos dados (primeiros 3 registros):")
            for i, record in enumerate(data[:3], 1):
                print(f"   {i}. {record}")
                if len(str(record)) > 200:  # Truncar se muito longo
                    break
            
            print(f"\n✅ Processo concluído com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro ao salvar arquivo: {str(e)}")
    
    elif success and not data:
        print("\n⚠️  Extração concluída, mas nenhum dado foi encontrado.")
    else:
        print("\n❌ Falha na extração dos dados. Verifique os logs para mais detalhes.")


if __name__ == "__main__":
    main()