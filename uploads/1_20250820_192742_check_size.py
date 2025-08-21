from pathlib import Path

def check_total_size(folder_path):
    """Verifica tamanho total dos arquivos PNG"""
    total_size = 0
    png_files = list(Path(folder_path).glob("*.png"))
    
    for png_file in png_files:
        total_size += png_file.stat().st_size
    
    size_gb = total_size / (1024**3)
    size_mb = total_size / (1024**2)
    
    print(f"📊 Total de arquivos: {len(png_files)}")
    print(f"📊 Tamanho total: {size_gb:.2f} GB ({size_mb:.0f} MB)")
    
    if size_gb > 25:
        print("⚠️  Excede o limite gratuito de 25GB")
        return False
    else:
        print("✅ Dentro do limite gratuito")
        return True

# Verificar antes do upload
check_total_size("/Users/cmorafre/Downloads/imagens_mapas")