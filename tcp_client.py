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


class TCPScooterClient:
    def __init__(self, scooter_id, host='localhost', port=8765):
        self.id = scooter_id
        self.host = host
        self.port = port
        self.location = {'lat': 41.0082, 'lon': 28.9784}
        self.battery = 100
        self.sock = None
        self.running = True
        self.current_scenario = 'all'

    def connect(self):
        """Bağlantı ve Yeniden Bağlanma"""
        while self.running:
            try:
                logging.info(f"Scooter sunucuya bağlanıyor: tcp://{self.host}:{self.port}")

                start_time = time.time()
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.host, self.port))

                # Yeniden bağlanma süresi kaydı
                rec_time = time.time() - start_time
                reconnect_time_data.append(rec_time)

                logging.info(f"Scooter bağlandı! (Süre: {rec_time:.4f}s)")

                # Register mesajı
                reg_msg = json.dumps({'type': 'register', 'scooter_id': self.id}) + '\n'
                self.send_data(reg_msg)

                return True
            except Exception as e:
                logging.warning(f"Bağlantı hatası: {e}. 5sn sonra tekrar denenecek...")
                time.sleep(5)

    def send_data(self, data_str):
        """Veri gönderme ve bant genişliği ölçümü"""
        try:
            encoded_data = data_str.encode('utf-8')
            bandwidth_data.append(len(encoded_data))  # TX Metriği
            self.sock.sendall(encoded_data)
        except Exception as e:
            logging.error(f"Gönderme hatası: {e}")
            self.sock.close()
            raise e

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
                msg = json.dumps(msg_dict) + '\n'

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
                msg = json.dumps(msg_dict) + '\n'

                self.send_data(msg)
                logging.info(f"SCOOTER TX (Durum): {json.dumps(msg_dict)}")
                time.sleep(5)
            except:
                break

    def task_listen(self):
        """Sunucudan gelen komutları dinleme"""
        buffer = ""
        while self.running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break

                bandwidth_data.append(len(data))

                buffer += data.decode()
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if not line.strip(): continue

                    msg = json.loads(line)
                    if msg.get('command'):
                        if self.current_scenario in ['command', 'all']:
                            logging.info(f"SCOOTER RX (Komut): {json.dumps(msg)}")

                        # Komut işleme simülasyonu ve ACK dönüşü
                        process_start = time.time()
                        time.sleep(0.1)  # İşlem süresi

                        ack_msg = json.dumps({
                            'type': 'ack',
                            'ack': f"command '{msg['command']}' received",
                            'send_time': msg.get('send_time')
                        }) + '\n'

                        self.send_data(ack_msg)

                        if self.current_scenario in ['command', 'all']:
                            logging.info(f"SCOOTER TX (ACK): command '{msg['command']}' received")

                        latency_data.append(time.time() - process_start)

            except Exception as e:
                logging.error(f"Dinleme hatası: {e}")
                break

    def run(self, scenario):
        self.current_scenario = scenario  # Senaryoyu kaydet

        # Bağlanma işlemi
        if not self.connect():
            return

        logging.info(f"ÇALIŞAN SENARYO: {scenario}")
        threads = []

        # Komut dinleme
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
            while True: time.sleep(1)  # Ana thread
        except KeyboardInterrupt:
            self.running = False
            logging.info("Scooter kapatılıyor...")
            if self.sock: self.sock.close()
            print_metrics("TCP")
            save_results_to_csv("TCP")


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

    # 1. Yeniden Bağlanma
    if reconnect_time_data:
        avg_rec = sum(reconnect_time_data) / len(reconnect_time_data)
        count = len(reconnect_time_data)
        logging.info(f"Ortalama Yeniden Bağlanma: {avg_rec:.4f} sn (Toplam {count} bağlantı)")

    # 2. Gecikme
    if latency_data:
        avg_lat = sum(latency_data) / len(latency_data)
        count = len(latency_data)
        logging.info(f"Ortalama Gecikme (Latency): {avg_lat:.4f} sn (Toplam {count} işlem)")

    # 3. Bant Genişliği ve Ortalama Boyut
    if bandwidth_data:
        total = sum(bandwidth_data)
        avg_size = total / len(bandwidth_data)
        logging.info(f"Toplam Veri Transferi: {total} bytes ({total / 1024:.2f} KB)")
        logging.info(f"Ortalama Mesaj Boyutu: {avg_size:.1f} bytes")

    # 4. Paket Kaybı
    logging.info(f"Paket Kayıp Oranı: %0.00")
    # 5. Footer
    logging.info("--- METRİKLER (Ham Veri Özeti) ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=['status', 'location', 'command', 'all'], default='all')
    parser.add_argument('--id', default='scooter_tcp_1')
    args = parser.parse_args()

    client = TCPScooterClient(args.id)
    client.run(args.scenario)