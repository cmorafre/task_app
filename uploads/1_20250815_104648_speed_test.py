
import speedtest
import pandas as pd
from datetime import datetime
import os

LOG_FILE = '/Users/cmorafre/Development/speed_log.xlsx'

def measure_and_save_speed():
    """
    Mede as velocidades de download e upload da internet e salva em um arquivo Excel.
    """
    st = speedtest.Speedtest()
    st.get_best_server()

    download_speed = st.download() / 1_000_000  # Convert to Mbps
    upload_speed = st.upload() / 1_000_000  # Convert to Mbps
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"Velocidade de Download: {download_speed:.2f} Mbps")
    print(f"Velocidade de Upload: {upload_speed:.2f} Mbps")

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

    print(f"Resultado salvo em {LOG_FILE}")

if __name__ == "__main__":
    measure_and_save_speed()
