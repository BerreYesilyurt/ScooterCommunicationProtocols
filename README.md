# IoT Scooter İletişim Protokollerinin Performans Analizi

Bu proje, IoT tabanlı elektrikli scooter yönetim sistemlerinde kullanılan **WebSocket**, **TCP**, **UDP** ve **MQTT** protokollerinin performanslarını karşılaştırmalı olarak analiz etmek amacıyla geliştirilmiştir. 

Her protokol için özel simülasyon ortamları oluşturulmuş; komut iletimi, konum takibi ve durum izleme senaryoları altında gecikme (latency), bant genişliği (bandwidth) ve bağlantı kararlılığı test edilmiştir.


## 🚀 Özellikler & Protokol Mimarileri
Proje aşağıdaki protokollerin istemci-sunucu mimarisini simüle eder:

* **WebSocket:** `asyncio` tabanlı asenkron, tam çift yönlü iletişim.
* **TCP:** `socket` ve `threading` ile bağlantı odaklı, güvenilir akış (stream).
* **UDP:** `socket` ile bağlantısız (connectionless) ve hızlı veri aktarımı.
* **MQTT:** `paho-mqtt` kütüphanesi ve `Mosquitto Broker` aracılığıyla Yayınla/Abone Ol (Pub/Sub) yapısı.

---

## 🛠️ Kurulum ve Gereksinimler

Projeyi çalıştırmadan önce aşağıdaki yazılımların sisteminizde kurulu olduğundan emin olun:

1.  **Python 3.8+**
2.  **Eclipse Mosquitto Broker** (Sadece MQTT protokolü için gereklidir)

### Kütüphane Bağımlılıklarının Yüklenmesi
Proje dizininde bir terminal açın ve gerekli Python kütüphanelerini yükleyin:

```bash
pip install -r requirements.txt

⚙️ Nasıl Çalıştırılır?
Simülasyonu çalıştırmak için önce Sunucu (Server), ardından İstemci (Scooter/Client) başlatılmalıdır.

1. Adım: MQTT Broker (Sadece MQTT testi için)
MQTT protokolünü test edecekseniz, Mosquitto servisinin arka planda çalıştığından emin olun. Manuel başlatmak için terminale şu komutu girebilirsiniz:

Bash

mosquitto -v
(Varsayılan port: 1883)

2. Adım: Sunucuyu Başlatma
Test etmek istediğiniz protokolün sunucu dosyasını terminalde çalıştırın. Sunucular başlatıldığında istemcileri dinlemeye başlar ve periyodik komut (örn: unlock) yayınlar.




Bash

# WebSocket Sunucusu için:
python server_websocket.py

# TCP Sunucusu için:
python server_tcp.py

# UDP Sunucusu için:
python server_udp.py

# MQTT Sunucusu için:
python server_mqtt.py
(Not: Dosya isimleri projenizdeki isimlendirmeye göre server.py veya server_tcp.py şeklinde olabilir, lütfen ilgili .py dosyasını seçin.)

3. Adım: İstemciyi (Scooter) Başlatma
İstemci simülasyonu, farklı veri türlerini test etmek için argparse kütüphanesi ile senaryo tabanlı çalışmaktadır. Aşağıdaki parametreleri kullanarak scooter'ı başlatabilirsiniz:

Kullanılabilir Senaryolar (--scenario):


status: Sadece pil seviyesi, hız ve kilit durumu gönderir.



location: Sadece coğrafi konum verisi gönderir.



command: Sunucudan gelen komutları dinler ve ACK döndürür.



all: Tüm senaryoları eş zamanlı (asyncio.gather) çalıştırır .

Örnek Çalıştırma Komutları:

Bash

# WebSocket İstemcisi - Tüm özellikler aktif (Önerilen)
python client_websocket.py --scenario all

# TCP İstemcisi - Sadece Konum takibi
python client_tcp.py --scenario location

# MQTT İstemcisi - Sadece Durum bilgisi
python client_mqtt.py --scenario status
📊 Proje Yapısı
.
├── server_websocket.py    # WebSocket Sunucu Kodları [cite: 118]
├── client_websocket.py    # WebSocket İstemci Kodları [cite: 124]
├── server_tcp.py          # TCP Sunucu Kodları [cite: 146]
├── client_tcp.py          # TCP İstemci Kodları [cite: 153]
├── server_udp.py          # UDP Sunucu Kodları [cite: 163]
├── client_udp.py          # UDP İstemci Kodları [cite: 169]
├── server_mqtt.py         # MQTT Sunucu Kodları [cite: 179]
├── client_mqtt.py         # MQTT İstemci Kodları [cite: 183]
├── requirements.txt       # Kütüphane listesi
├── README.md              # Proje dokümantasyonu
└── results/               # Test sonuçları (CSV) ve grafik çıktıları (PNG)
📈 Performans Metrikleri & Çıktılar
Simülasyon tamamlandığında, konsol ekranında ve results klasöründe aşağıdaki veriler raporlanır:


RTT (Round Trip Time): Sunucudan gelen komuta scooter'ın verdiği cevap süresi (Gecikme).

Bant Genişliği: Kullanılan veri boyutu (Byte cinsinden mesaj yükü).
Reconnection Time: Bağlantı koptuğunda sistemin tekrar ayağa kalkma süresi.
