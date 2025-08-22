import pdfplumber
import re

def debug_pdf_extraction(caminho_pdf: str):
    """
    Script de debug para entender como o PDF está sendo lido
    """
    print("=== DEBUG: Análise do PDF ===")
    
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            print(f"PDF carregado com sucesso!")
            print(f"Número de páginas: {len(pdf.pages)}")
            
            for i, pagina in enumerate(pdf.pages):
                print(f"\n--- PÁGINA {i+1} ---")
                
                # Tenta extrair o texto
                texto = pagina.extract_text()
                
                if texto:
                    print(f"Texto extraído com sucesso!")
                    print(f"Tamanho do texto: {len(texto)} caracteres")
                    
                    # Mostra as primeiras linhas
                    linhas = texto.split('\n')
                    print(f"Total de linhas: {len(linhas)}")
                    
                    print("\n=== PRIMEIRAS 10 LINHAS ===")
                    for j, linha in enumerate(linhas[:10]):
                        print(f"Linha {j+1}: '{linha}'")
                    
                    # Procura por padrões de unidade
                    print("\n=== LINHAS COM PADRÃO DE UNIDADE ===")
                    for j, linha in enumerate(linhas):
                        if re.match(r'^\d{4}\s*PL', linha.strip()):
                            print(f"Linha {j+1}: '{linha.strip()}'")
                            
                            # Mostra as próximas 3 linhas também
                            for k in range(1, 4):
                                if j+k < len(linhas):
                                    print(f"  +{k}: '{linhas[j+k].strip()}'")
                            print("-" * 50)
                    
                    # Tenta também extrair como tabela
                    print("\n=== TENTANDO EXTRAIR COMO TABELA ===")
                    tabelas = pagina.extract_tables()
                    if tabelas:
                        print(f"Encontradas {len(tabelas)} tabelas")
                        for t_idx, tabela in enumerate(tabelas):
                            print(f"Tabela {t_idx+1}: {len(tabela)} linhas")
                            if len(tabela) > 0:
                                print(f"Primeira linha: {tabela[0]}")
                    else:
                        print("Nenhuma tabela encontrada")
                        
                else:
                    print("Nenhum texto extraído!")
                    
                # Verifica se há imagens que podem estar atrapalhando
                if hasattr(pagina, 'images'):
                    print(f"Imagens na página: {len(pagina.images)}")
                
                if i >= 2:  # Só analisa as primeiras 3 páginas para não poluir
                    print("\n... (limitando análise às primeiras 3 páginas)")
                    break
                    
    except Exception as e:
        print(f"ERRO: {e}")
        print("Verifique se:")
        print("1. O arquivo existe")
        print("2. O arquivo não está corrompido")
        print("3. Você tem permissão para ler o arquivo")

def test_regex_patterns():
    """
    Testa padrões regex com texto de exemplo
    """
    print("\n=== TESTE DE PADRÕES REGEX ===")
    
    # Texto de exemplo baseado no que vemos no PDF
    texto_exemplo = """0453 PL CLIVIA DA SILVA OLIVEIRA Proprietário RUA DOS TINGUIS - QD 3 LT 24 00168806269 0
ADIMPLENCIA (+34662564377) RESIDENCIAL PORTAL DO LAGO - ETAPA 2 -
SANTA BÁRBARA DE GOIÁS - GO - 75398000
0966 PL JUNEY DOS REIS SOUSA Proprietário ALAMEDA DO LAGO - QD 24 LT 22 04143717123 0
ADIMPLENCIA RESIDENCIAL PORTAL DO LAGO - ETAPA 2 -
Santa Bárbara de Goiás - GO - 75398-000"""
    
    linhas = texto_exemplo.split('\n')
    
    print("Texto de exemplo:")
    for i, linha in enumerate(linhas):
        print(f"{i+1}: '{linha}'")
    
    print("\nTestando padrões:")
    
    # Testa diferentes padrões
    padroes = [
        r'^\d{4}\s*PL',
        r'^\d{4}\s+PL[^\s]*',
        r'^(\d{4}\s+PL[^\s]*)\s+(.+)',
    ]
    
    for i, padrao in enumerate(padroes):
        print(f"\nPadrão {i+1}: {padrao}")
        for j, linha in enumerate(linhas):
            match = re.match(padrao, linha.strip())
            if match:
                print(f"  Linha {j+1} matched: {match.groups() if match.groups() else match.group()}")

if __name__ == "__main__":
    import sys
    
    # Teste os padrões primeiro
    test_regex_patterns()
    
    # Depois analisa o PDF se fornecido
    if len(sys.argv) > 1:
        caminho_pdf = sys.argv[1]
        debug_pdf_extraction(caminho_pdf)
    else:
        print("\n" + "="*50)
        print("Para analisar seu PDF, execute:")
        print("python debug_pdf.py caminho_do_seu_arquivo.pdf")
        print("="*50)