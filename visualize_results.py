import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import os

sns.set_theme(style="whitegrid")

# Dosya isimleri
files = {
    'MQTT': 'results_mqtt.csv',
    'TCP': 'results_tcp.csv',
    'UDP': 'results_udp.csv',
    'WebSocket': 'results_websocket.csv'
}

data_frames = []

# --- 1. CSV DOSYALARINI OKUMA ---
print("Veriler yükleniyor...")
for protocol, filename in files.items():
    if os.path.exists(filename):
        try:
            # CSV'yi oku
            df = pd.read_csv(filename)

            # Protokol ismini bir sütun olarak ekle (Gruplama için gerekli)
            df['Protocol'] = protocol

            # Veri temizliği: Boş satırları veya None olanları temizle
            df = df.dropna(subset=['Latency', 'Bandwidth'])

            # Sadece Latency > 0 olanları al (Hatalı ölçümleri elemek için)
            df = df[df['Latency'] > 0]

            data_frames.append(df)
            print(f"✅ {protocol} verileri yüklendi: {len(df)} kayıt.")
        except Exception as e:
            print(f"❌ Hata ({protocol}): {e}")
    else:
        print(f"⚠️ Uyarı: {filename} bulunamadı! Simülasyonu çalıştırdın mı?")

if not data_frames:
    print("Hiçbir veri dosyası bulunamadı. Lütfen önce simülasyonları çalıştırın.")
    exit()

# Tüm verileri tek bir tabloda birleştir
full_data = pd.concat(data_frames, ignore_index=True)

#GRAFİK ÇİZME

fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('IoT Scooter Protokolleri - Gerçek Performans Analizi', fontsize=18, fontweight='bold')

#Ortalama Gecikme (Latency)
sns.barplot(ax=axes[0, 0], x="Protocol", y="Latency", data=full_data, errorbar="sd", palette="viridis")
axes[0, 0].set_title("Ortalama Gecikme (Latency) ve Standart Sapma", fontsize=14)
axes[0, 0].set_ylabel("Saniye (s)")
axes[0, 0].grid(axis='y', linestyle='--', alpha=0.7)

#Mesaj Boyutu / Bant Genişliği
sns.boxplot(ax=axes[0, 1], x="Protocol", y="Bandwidth", data=full_data, palette="rocket")
axes[0, 1].set_title("Bant Genişliği Tüketimi (Mesaj Boyutu)", fontsize=14)
axes[0, 1].set_ylabel("Byte")

#Gecikme Dağılımı
sns.violinplot(ax=axes[1, 0], x="Protocol", y="Latency", data=full_data, palette="mako", inner="quartile")
axes[1, 0].set_title("Gecikme Kararlılığı (Yoğunluk Analizi)", fontsize=14)
axes[1, 0].set_ylabel("Saniye (s)")

#Yeniden Bağlanma Süresi
reconnect_data = full_data[full_data['ReconnectTime'] > 0]

if not reconnect_data.empty:
    sns.barplot(ax=axes[1, 1], x="Protocol", y="ReconnectTime", data=reconnect_data, palette="coolwarm")
    axes[1, 1].set_title("Ortalama Yeniden Bağlanma Süresi", fontsize=14)
    axes[1, 1].set_ylabel("Saniye (s)")
else:
    axes[1, 1].text(0.5, 0.5, "Yeniden Bağlanma Verisi Yok", ha='center', va='center', fontsize=12)

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.savefig("karsilastirma_sonuc.png", dpi=300)  # Grafiği kaydet
print("Grafik 'karsilastirma_sonuc.png' olarak kaydedildi.")
plt.show()

