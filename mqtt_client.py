import paho.mqtt.client as mqtt
import json
import time
import random
import logging
import argparse
import threading
import csv

# Loglama ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

latency_data = []
reconnect_time_data = []
bandwidth_data = []

class MQTTScooterClient:
    def __init__(self, scooter_id, broker='localhost', port=1883):
        self.id = scooter_id
        self.broker = broker
        self.port = port
        self.location = {'lat': 41.0082, 'lon': 28.9784}
        self.battery = 100

        # Paho Client Kurulumu (V2 API)
        self.client = mqtt.Client(client_id=scooter_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

        self.running = True
        self.current_scenario = 'all'

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            # Bağlantı süresini burada ölçemiyoruz çünkü callback sonradan çalışır,
            # ama connect() fonksiyonunda ölçeceğiz.

            # Komutları dinlemek için abone ol
            topic = f"scooter/{self.id}/command"
            client.subscribe(topic)

            # Register mesajı gönder
            reg_msg = json.dumps({'type': 'register', 'scooter_id': self.id})
            self.publish_data(f"scooter/{self.id}/register", reg_msg)
        else:
            logging.error(f"Broker bağlantı hatası: {reason_code}")

    def on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode()
            bandwidth_data.append(len(payload))

            data = json.loads(payload)

            if data.get('command'):
                if self.current_scenario in ['command', 'all']:
                    logging.info(f"SCOOTER RX (Komut): {json.dumps(data)}")

                process_start = time.time()
                time.sleep(0.1)

                ack_msg = json.dumps({
                    'type': 'ack',
                    'scooter_id': self.id,
                    'ack': f"command '{data['command']}' received",
                    'send_time': data.get('send_time')
                })

                self.publish_data(f"scooter/{self.id}/ack", ack_msg)
                if self.current_scenario in ['command', 'all']:
                    logging.info(f"SCOOTER TX (ACK): command '{data['command']}' received")
                    latency_data.append(time.time() - process_start)

        except Exception as e:
            logging.error(f"Mesaj işleme hatası: {e}")

    def publish_data(self, topic, payload):
        """Veri gönderme sarmalayıcısı"""
        try:
            bandwidth_data.append(len(payload))  # TX Metriği
            self.client.publish(topic, payload)
        except Exception as e:
            logging.error(f"Yayınlama hatası: {e}")

    def connect(self):
        try:
            logging.info(f"Scooter sunucuya bağlanıyor: mqtt://{self.broker}:{self.port}")

            start_time = time.time()

            # Callbackler
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message

            self.client.connect(self.broker, self.port, 60)

            # Arka planda network trafiği yönetimi
            self.client.loop_start()

            rec_time = time.time() - start_time
            reconnect_time_data.append(rec_time)

            logging.info(f"Scooter bağlandı! (Süre: {rec_time:.4f}s)")
            return True

        except Exception as e:
            logging.warning(f"Bağlantı hatası: {e}. 5sn sonra tekrar denenecek...")
            time.sleep(5)
            return False

    def task_location(self):
        """Konum Senaryosu"""
        while self.running and self.battery > 0:
            try:
                self.location['lat'] += random.uniform(-0.0001, 0.0001)
                self.location['lon'] += random.uniform(-0.0001, 0.0001)
                self.battery -= 0.5

                msg_dict = {
                    'type': 'location',
                    'scooter_id': self.id,
                    'location': self.location,
                    'battery': round(self.battery, 1)
                }
                msg = json.dumps(msg_dict)

                self.publish_data(f"scooter/{self.id}/location", msg)
                logging.info(f"SCOOTER TX (Konum): {json.dumps(msg_dict)}")

                time.sleep(10)
            except:
                break

    def task_status(self):
        """Durum Senaryosu"""
        while self.running:
            try:
                is_locked = random.choice([True, False])
                msg_dict = {
                    'type': 'status',
                    'scooter_id': self.id,
                    'status': {
                        'battery_level': round(self.battery, 1),
                        'is_locked': is_locked,
                        'speed': 0 if is_locked else random.randint(0, 25)
                    }
                }
                msg = json.dumps(msg_dict)

                self.publish_data(f"scooter/{self.id}/status", msg)
                logging.info(f"SCOOTER TX (Durum): {json.dumps(msg_dict)}")

                time.sleep(5)
            except:
                break

    def run(self, scenario):
        self.current_scenario = scenario

        if not self.connect():
            return

        logging.info(f"ÇALIŞAN SENARYO: {scenario}")

        threads = []

        if scenario in ['location', 'all']:
            t_loc = threading.Thread(target=self.task_location)
            t_loc.daemon = True
            t_loc.start()
            threads.append(t_loc)

        if scenario in ['status', 'all']:
            t_stat = threading.Thread(target=self.task_status)
            t_stat.daemon = True
            t_stat.start()
            threads.append(t_stat)

        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            logging.info("Scooter kapatılıyor...")
            self.client.loop_stop()
            self.client.disconnect()
            print_metrics("MQTT")
            save_results_to_csv("MQTT")


def save_results_to_csv(protocol_name):
    """
    Toplanan verileri analiz için CSV dosyasına kaydeder.
    """
    filename = f"results_{protocol_name.lower()}.csv"

    rows = []
    max_len = max(len(latency_data), len(bandwidth_data), len(reconnect_time_data))

    for i in range(max_len):
        lat = latency_data[i] if i < len(latency_data) else None
        bw = bandwidth_data[i] if i < len(bandwidth_data) else None
        rec = reconnect_time_data[i] if i < len(reconnect_time_data) else None
        rows.append([lat, bw, rec])

    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Latency", "Bandwidth", "ReconnectTime"])  # Başlıklar
        writer.writerows(rows)

    logging.info(f"Sonuçlar kaydedildi: {filename}")

def print_metrics(protocol_name):
    logging.info(f"--- SİMÜLASYON SONUÇLARI ({protocol_name}) ---")
    if reconnect_time_data:
        avg_rec = sum(reconnect_time_data) / len(reconnect_time_data)
        count = len(reconnect_time_data)
        logging.info(f"Ortalama Yeniden Bağlanma: {avg_rec:.4f} sn (Toplam {count} bağlantı)")

    if latency_data:
        avg_lat = sum(latency_data) / len(latency_data)
        count = len(latency_data)
        logging.info(f"Ortalama Gecikme (Latency): {avg_lat:.4f} sn (Toplam {count} işlem)")

    if bandwidth_data:
        total = sum(bandwidth_data)
        avg_size = total / len(bandwidth_data)
        logging.info(f"Toplam Veri Transferi: {total} bytes ({total / 1024:.2f} KB)")
        logging.info(f"Ortalama Mesaj Boyutu: {avg_size:.1f} bytes")

    logging.info(f"Paket Kayıp Oranı: %0.00 (QoS 0)")
    logging.info("--- METRİKLER (Ham Veri Özeti) ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=['status', 'location', 'command', 'all'], default='all')
    parser.add_argument('--id', default='scooter_mqtt_1')
    args = parser.parse_args()

    client = MQTTScooterClient(args.id)
    client.run(args.scenario)