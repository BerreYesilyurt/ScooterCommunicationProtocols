import paho.mqtt.client as mqtt
import json
import time
import threading
import logging
import csv  # <-- 1. EKLENDİ

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

latency_data = []  # RTT Verileri
bandwidth_data = []  # Bant Genişliği Verileri

def save_server_results():
    """Sunucu kapandığında verileri CSV'ye yazar."""
    filename = "results_mqtt_server.csv"

    global latency_data, bandwidth_data

    if not latency_data and not bandwidth_data:
        logging.warning("Hiç veri toplanmadı, yine de boş dosya oluşturuluyor.")

    # Veri uzunluklarını eşitleme
    max_len = max(len(latency_data), len(bandwidth_data)) if (latency_data or bandwidth_data) else 0

    rows = []
    for i in range(max_len):
        lat = latency_data[i] if i < len(latency_data) else None
        bw = bandwidth_data[i] if i < len(bandwidth_data) else None
        rows.append([lat, bw])

    try:
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Latency_RTT", "Bandwidth"])
            writer.writerows(rows)
        logging.info(f"✅ SONUÇLAR BAŞARIYLA KAYDEDİLDİ: {filename}")
        import os
        logging.info(f"Dosya Yolu: {os.path.abspath(filename)}")
    except Exception as e:
        logging.error(f"❌ CSV Kayıt hatası: {e}")


class MQTTServer:
    def __init__(self, broker='localhost', port=1883):
        self.broker = broker
        self.port = port
        # Callback API V2 kullanımı
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.known_clients = set()
        self.running = True

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            logging.info(f"MQTT Broker'a Bağlandı (Port: {self.port})")
            #tüm scooter topiclerini dinleme
            client.subscribe("scooter/+/+")
        else:
            logging.error(f"Bağlantı hatası: {reason_code}")

    def on_message(self, client, userdata, msg):
        try:
            payload_len = len(msg.payload)
            bandwidth_data.append(payload_len)

            payload_str = msg.payload.decode()
            data = json.loads(payload_str)

            # Topic'ten ID'yi çeker
            topic_parts = msg.topic.split('/')
            if len(topic_parts) >= 2:
                scooter_id = topic_parts[1]
                self.known_clients.add(scooter_id)
            else:
                scooter_id = "unknown"

            msg_type = data.get('type')

            if msg_type == 'register':
                logging.info(f"SERVER RX (Register) <- {scooter_id}")

            elif msg_type == 'location':
                logging.info(f"SERVER RX (Konum) <- {scooter_id}")

            elif msg_type == 'status':
                logging.info(f"SERVER RX (Durum) <- {scooter_id}")

            elif msg_type == 'ack':
                # RTT Hesaplama
                send_time = data.get('send_time', 0)
                if send_time:
                    rtt = time.time() - send_time
                    latency_data.append(rtt)
                    logging.info(f"SERVER RX (ACK) <- {scooter_id} | RTT: {rtt:.6f}s")

        except Exception as e:
            logging.error(f"Mesaj işleme hatası: {e}")

    def broadcast_commands(self):
        """Her 15 saniyede bir bilinen scooterlara komut atar"""
        while self.running:
            time.sleep(15)
            if not self.known_clients: continue

            cmd_dict = {
                "command": "unlock",
                "scooter_id": "server",
                "send_time": time.time()
            }
            cmd_json = json.dumps(cmd_dict)

            for s_id in list(self.known_clients):
                topic = f"scooter/{s_id}/command"
                try:
                    self.client.publish(topic, cmd_json)
                    bandwidth_data.append(len(cmd_json))
                    logging.info(f"SERVER TX (Komut) -> {s_id} (Topic: {topic})")
                except:
                    pass

    def start(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()

            logging.info("MQTT Sunucusu Servisi Başlatıldı (Kapatmak için CTRL+C)")

            t_broadcast = threading.Thread(target=self.broadcast_commands, daemon=True)
            t_broadcast.start()

            while self.running:
                time.sleep(1)

        except KeyboardInterrupt:
            logging.info("Kullanıcı tarafından durduruldu.")
        finally:
            self.running = False
            self.client.loop_stop()
            self.client.disconnect()
            logging.info("MQTT bağlantısı kesildi.")


if __name__ == "__main__":
    srv = MQTTServer()
    try:
        srv.start()
    except KeyboardInterrupt:
        pass
    finally:
        logging.info("Program sonlanıyor, veriler kaydediliyor...")
        save_server_results()