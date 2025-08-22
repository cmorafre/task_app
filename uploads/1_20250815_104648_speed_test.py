import speedtest
import pandas as pd
from datetime import datetime
import os
import time

LOG_FILE = '/Users/cmorafre/Development/speed_log.xlsx'

def measure_and_save_speed():
    """
    Mede as velocidades de download e upload da internet e salva em um arquivo Excel.
    """
    try:
        print("Inicializando speedtest...")
        # Configurações mais robustas para evitar erro 403
        st = speedtest.Speedtest(secure=True)
        
        print("Configurando User-Agent...")
        # Adicionar headers customizados para evitar bloqueio
        st._opener.addheaders = [
            ('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'),
            ('Accept', 'application/json, text/plain, */*'),
            ('Accept-Language', 'pt-BR,pt;q=0.9,en;q=0.8'),
            ('Accept-Encoding', 'gzip, deflate, br'),
            ('DNT', '1'),
            ('Connection', 'keep-alive'),
            ('Upgrade-Insecure-Requests', '1'),
        ]
        
        print("Obtendo melhor servidor...")
        # Adicionar delay para evitar rate limiting
        time.sleep(2)
        st.get_best_server()

        print("Medindo velocidade de download...")
        download_speed = st.download() / 1_000_000  # Convert to Mbps
        
        print("Medindo velocidade de upload...")
        upload_speed = st.upload() / 1_000_000  # Convert to Mbps
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        print(f"✅ Velocidade de Download: {download_speed:.2f} Mbps")
        print(f"✅ Velocidade de Upload: {upload_speed:.2f} Mbps")

        # Save to Excel
        new_data = pd.DataFrame({
            'Timestamp': [timestamp],
            'Download (Mbps)': [f"{download_speed:.2f}"],
            'Upload (Mbps)': [f"{upload_speed:.2f}"]
        })

        if os.path.isfile(LOG_FILE):
            with pd.ExcelWriter(LOG_FILE, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
                # Get the last row of the existing sheet to append after it
                workbook = writer.book
                sheet = workbook.active
                startrow = sheet.max_row
                new_data.to_excel(writer, index=False, header=False, startrow=startrow)
        else:
            new_data.to_excel(LOG_FILE, index=False)

        print(f"✅ Resultado salvo em {LOG_FILE}")
        
    except speedtest.ConfigRetrievalError as e:
        print(f"❌ Erro de configuração do speedtest: {e}")
        print("💡 Possíveis causas:")
        print("   - Bloqueio por rate limiting")
        print("   - Problemas de conectividade")
        print("   - Servidores speedtest indisponíveis")
        print("🔄 Tentativa alternativa...")
        
        # Tentar com configuração mais simples
        try:
            print("Tentando configuração alternativa...")
            st = speedtest.Speedtest()
            servers = st.get_servers([])  # Buscar servidores manualmente
            st.get_best_server(servers)
            
            download_speed = st.download() / 1_000_000
            upload_speed = st.upload() / 1_000_000
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"✅ Download (alternativo): {download_speed:.2f} Mbps")
            print(f"✅ Upload (alternativo): {upload_speed:.2f} Mbps")
            
            # Save result mesmo com método alternativo
            new_data = pd.DataFrame({
                'Timestamp': [timestamp],
                'Download (Mbps)': [f"{download_speed:.2f}"],
                'Upload (Mbps)': [f"{upload_speed:.2f}"]
            })
            
            if os.path.isfile(LOG_FILE):
                with pd.ExcelWriter(LOG_FILE, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
                    workbook = writer.book
                    sheet = workbook.active
                    startrow = sheet.max_row
                    new_data.to_excel(writer, index=False, header=False, startrow=startrow)
            else:
                new_data.to_excel(LOG_FILE, index=False)
                
            print(f"✅ Resultado salvo em {LOG_FILE}")
            
        except Exception as alt_e:
            print(f"❌ Método alternativo também falhou: {alt_e}")
            
            # Salvar erro como log
            error_data = pd.DataFrame({
                'Timestamp': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                'Download (Mbps)': ['ERRO'],
                'Upload (Mbps)': [str(alt_e)[:50]]
            })
            
            if os.path.isfile(LOG_FILE):
                with pd.ExcelWriter(LOG_FILE, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
                    workbook = writer.book
                    sheet = workbook.active
                    startrow = sheet.max_row
                    error_data.to_excel(writer, index=False, header=False, startrow=startrow)
            else:
                error_data.to_excel(LOG_FILE, index=False)
            
            raise
            
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        # Salvar erro como log
        error_data = pd.DataFrame({
            'Timestamp': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            'Download (Mbps)': ['ERRO'],
            'Upload (Mbps)': [str(e)[:50]]
        })
        
        if os.path.isfile(LOG_FILE):
            with pd.ExcelWriter(LOG_FILE, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
                workbook = writer.book
                sheet = workbook.active
                startrow = sheet.max_row
                error_data.to_excel(writer, index=False, header=False, startrow=startrow)
        else:
            error_data.to_excel(LOG_FILE, index=False)
        
        raise

if __name__ == "__main__":
    measure_and_save_speed()
