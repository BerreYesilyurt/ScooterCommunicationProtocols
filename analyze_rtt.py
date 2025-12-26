import pandas as pd
import glob
import os
import numpy as np

def analyze_server_rtt():
    # Klasördeki 'results_*_server.csv' formatındaki tüm dosyaları bul
    # Örn: results_websocket_server.csv, results_tcp_server.csv
    files = glob.glob("results_*_server.csv")

    if not files:
        print("UYARI: Hiçbir sunucu sonuç dosyası (results_..._server.csv) bulunamadı.")
        print("Lütfen önce simülasyonları 'server' modunda çalıştırıp veri toplayın.")
        return

    results_summary = []

    print("-" * 85)
    print(
        f"{'PROTOKOL':<15} | {'ORTALAMA (s)':<12} | {'MİN (s)':<10} | {'MAX (s)':<10} | {'JITTER (std)':<12} | {'VERİ ADEDİ':<10}")
    print("-" * 85)

    for file in files:
        try:
            # Dosya adı formatı
            protocol_name = file.replace("results_", "").replace("_server.csv", "").upper()

            df = pd.read_csv(file)
            col_name = None
            for col in df.columns:
                if "Latency" in col:
                    col_name = col
                    break

            if col_name and not df[col_name].isnull().all():
                rtt_data = df[col_name].dropna()  # Boş verileri at

                avg_rtt = rtt_data.mean()
                min_rtt = rtt_data.min()
                max_rtt = rtt_data.max()

                # Jitter (Gecikme Değişimi): Genelde standart sapma (std) ile ifade edilir
                jitter = rtt_data.std()

                count = len(rtt_data)

                print(
                    f"{protocol_name:<15} | {avg_rtt:.6f}     | {min_rtt:.6f}   | {max_rtt:.6f}   | {jitter:.6f}     | {count:<10}")

                results_summary.append({
                    'Protokol': protocol_name,
                    'Avg': avg_rtt,
                    'Jitter': jitter
                })
            else:
                print(f"{protocol_name:<15} | VERİ YOK / HATALI SÜTUN")

        except Exception as e:
            print(f"Hata ({file}): {e}")

    print("-" * 85)

    # --- SONUÇ YORUMU ---
    if results_summary:
        best_protocol = min(results_summary, key=lambda x: x['Avg'])
        most_stable = min(results_summary, key=lambda x: x['Jitter'])

        print(f"\n🏆 EN HIZLI PROTOKOL (Düşük RTT): {best_protocol['Protokol']} ({best_protocol['Avg']:.6f} s)")
        print(f"⚖️  EN KARARLI PROTOKOL (Düşük Jitter): {most_stable['Protokol']} ({most_stable['Jitter']:.6f} s)")


if __name__ == "__main__":
    # Pandas görüntüleme ayarları
    pd.set_option('display.float_format', lambda x: '%.6f' % x)
    analyze_server_rtt()