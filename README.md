# IoT Scooter İletişim Protokollerinin Performans Analizi

Bu proje, IoT tabanlı elektrikli scooter yönetim sistemlerinde kullanılan **WebSocket**, **TCP**, **UDP** ve **MQTT** protokollerinin performanslarını karşılaştırmalı olarak analiz etmek amacıyla geliştirilmiştir. 

Her protokol için özel simülasyon ortamları oluşturulmuş; komut iletimi, konum takibi ve durum izleme senaryoları altında gecikme (latency), bant genişliği (bandwidth) ve bağlantı kararlılığı test edilmiştir.

## 👥 Hazırlayanlar
* **Berre Yeşilyurt** - 502431006
* **Mustafa Sungur Polater** - 502431003

---

## 🚀 Özellikler & Protokol Mimarileri
Proje aşağıdaki protokollerin istemci-sunucu mimarisini simüle eder:

* **WebSocket:** `asyncio` tabanlı asenkron, tam çift yönlü iletişim.
* **TCP:** `socket` ve `threading` ile bağlantı odaklı, güvenilir akış (stream).
* **UDP:** `socket` ile bağlantısız (connectionless) ve hızlı veri aktarımı.
* **MQTT:** `paho-mqtt` kütüphanesi ve `Mosquitto Broker` aracılığıyla Yayınla/Abone Ol (Pub/Sub) yapısı.

---

## 🛠️ Kurulum ve Gereksinimler

Projeyi çalıştırmadan önce aşağıdaki yazılımların sisteminizde kurulu olduğundan emin olun:

1.  **Python 3.8+**: [İndir](https://www.python.org/downloads/)
2.  **Eclipse Mosquitto Broker** (Sadece MQTT protokolü için gereklidir): [İndir](https://mosquitto.org/download/)

### Kütüphane Bağımlılıklarının Yüklenmesi
Proje dizininde bir terminal açın ve gerekli Python kütüphanelerini yükleyin:

```bash
pip install -r requirements.txt
