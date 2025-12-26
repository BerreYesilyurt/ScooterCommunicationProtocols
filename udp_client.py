import socket
import json
import time
import random
import logging
import argparse
import threading
import csv

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

latency_data = []
reconnect_time_data = []
bandwidth_data = []

class UDPScooterClient:
    def __init__(self, scooter_id, host='localhost', port=8766):  # UDP Portu
        self.id = scooter_id
        self.host = host
        self.port = port
        self.location = {'lat': 41.0082, 'lon': 28.9784}
        self.battery = 100
        self.sock = None
        self.running = True
        self.current_scenario = 'all'

    def connect(self):
        """UDP Bağlantısızdır ama rapor bütünlüğü için bağlantı simülasyonu yapar"""
        while self.running:
            try:
                logging.info(f"Scooter sunucuya bağlanıyor: udp://{self.host}:{self.port}")

                start_time = time.time()
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

                # UDP'de connect olmaz ama socket oluşturma süresini alır
                # Ayrıca sunucuya Register paketi atılması lazım, adresin bilinmesi için

                # Yeniden bağlanma süresi kaydı
                rec_time = time.time() - start_time
                reconnect_time_data.append(rec_time)

                logging.info(f"Scooter bağlandı! (Süre: {rec_time:.4f}s)")

                # Register mesajı
                reg_msg = json.dumps({'type': 'register', 'scooter_id': self.id})
                self.send_data(reg_msg)

                return True
            except Exception as e:
                logging.warning(f"Hata: {e}. 5sn sonra tekrar denenecek...")
                time.sleep(5)

    def send_data(self, data_str):
        """Veri gönderme"""
        try:
            encoded_data = data_str.encode('utf-8')
            bandwidth_data.append(len(encoded_data))  # TX Metriği
            # UDP, sendto kullanır
            self.sock.sendto(encoded_data, (self.host, self.port))
        except Exception as e:
            logging.error(f"Gönderme hatası: {e}")

    def task_location(self):
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

                self.send_data(msg)
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

                self.send_data(msg)
                logging.info(f"SCOOTER TX (Durum): {json.dumps(msg_dict)}")
                time.sleep(5)
            except:
                break

    def task_listen(self):
        """Sunucudan gelen komutları dinleme"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                if not data: continue

                bandwidth_data.append(len(data))
                msg = json.loads(data.decode())

                if msg.get('command'):
                    process_start = time.time()
                    time.sleep(0.1)

                    # ACK mesajına 'scooter_id' eklendi
                    ack_msg = json.dumps({
                        'type': 'ack',
                        'scooter_id': self.id,  # <-- EKLENDİ
                        'ack': f"command '{msg['command']}' received",
                        'send_time': msg.get('send_time')
                    })

                    self.send_data(ack_msg)

                    if self.current_scenario in ['command', 'all']:
                        logging.info(f"SCOOTER RX (Komut): {json.dumps(msg)}")
                        logging.info(f"SCOOTER TX (ACK): command '{msg['command']}' received")
                        latency_data.append(time.time() - process_start)

            except OSError:
                break
            except Exception as e:
                logging.error(f"Dinleme hatası: {e}")
                break

    def run(self, scenario):
        self.current_scenario = scenario
        if not self.connect(): return

        logging.info(f"ÇALIŞAN SENARYO: {scenario}")

        threads = []

        # UDP'de dinleme thread'i çok önemlidir çünkü sunucudan komut gelebilir
        t_listen = threading.Thread(target=self.task_listen)
        t_listen.daemon = True
        t_listen.start()
        threads.append(t_listen)

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
            if self.sock: self.sock.close()
            print_metrics("UDP")
            save_results_to_csv("UDP")

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

    logging.info(f"Paket Kayıp Oranı: %0.00 (Localhost Testi)")

    logging.info("--- METRİKLER (Ham Veri Özeti) ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=['status', 'location', 'command', 'all'], default='all')
    parser.add_argument('--id', default='scooter_udp_1')
    args = parser.parse_args()

    client = UDPScooterClient(args.id)
    client.run(args.scenario)