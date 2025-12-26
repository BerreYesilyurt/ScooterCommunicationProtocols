import socket
import json
import threading
import time
import logging
import csv

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

latency_data = []
bandwidth_data = []

def save_server_results():
    """Sunucu kapandığında verileri CSV'ye yazar."""
    filename = "results_udp_server.csv"

    global latency_data, bandwidth_data

    # Veri yoksa uyarı ver
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


class UDPServer:
    def __init__(self, port=8766):
        self.port = port
        self.sock = None
        self.known_clients = {}  # {scooter_id: (ip, port)}
        self.running = True

    def broadcast_commands(self):
        """Periyodik Unlock komutu gönderir"""
        while self.running:
            time.sleep(15)  # 15 saniyede bir komut
            if not self.known_clients: continue

            try:
                cmd = json.dumps({
                    "command": "unlock",
                    "scooter_id": "broadcast",
                    "send_time": time.time()
                })

                # Kayıtlı tüm scooterlara gönder
                for s_id, addr in list(self.known_clients.items()):
                    try:
                        encoded_cmd = cmd.encode()
                        self.sock.sendto(encoded_cmd, addr)
                        bandwidth_data.append(len(encoded_cmd))
                        logging.info(f"SERVER TX (Komut) -> {s_id} ({addr})")
                    except Exception as e:
                        logging.error(f"Komut gönderme hatası: {e}")
            except Exception as e:
                logging.error(f"Broadcast döngü hatası: {e}")

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', self.port))
        self.sock.settimeout(1.0)  # CTRL+C yakalamak için timeout

        # Komut thread'ini başlatır
        t_broadcast = threading.Thread(target=self.broadcast_commands, daemon=True)
        t_broadcast.start()

        logging.info(f"UDP Sunucusu Başlatıldı: {self.port} (Kapatmak için CTRL+C)")

        try:
            while self.running:
                try:
                    data, addr = self.sock.recvfrom(4096)

                    bandwidth_data.append(len(data))
                    try:
                        msg = json.loads(data.decode())
                    except json.JSONDecodeError:
                        continue

                    scooter_id = msg.get('scooter_id', 'unknown')

                    # Scooter ID 'unknown' değilse listeye kaydet/güncelle
                    if scooter_id != 'unknown':
                        if scooter_id not in self.known_clients:
                            self.known_clients[scooter_id] = addr
                            logging.info(f"Yeni Scooter Kaydedildi (UDP): {scooter_id} @ {addr}")
                        else:
                            # Adres değişmiş olabilir (NAT vs), güncelle
                            self.known_clients[scooter_id] = addr

                    # Mesaj Tiplerine Göre Loglama
                    msg_type = msg.get('type')
                    if msg_type == 'register':
                        logging.info(f"SERVER RX (Register) <- {scooter_id}")

                    elif msg_type == 'ack':
                        # RTT Hesaplama
                        send_time = msg.get('send_time', 0)
                        if send_time:
                            rtt = time.time() - send_time
                            latency_data.append(rtt)
                            logging.info(f"SERVER RX (ACK) <- {scooter_id} | RTT: {rtt:.6f}s")

                    elif msg_type == 'location':
                        logging.info(f"SERVER RX (Konum) <- {scooter_id}")

                    elif msg_type == 'status':
                        logging.info(f"SERVER RX (Durum) <- {scooter_id}")

                except socket.timeout:
                    continue
                except Exception as e:
                    logging.error(f"Hata: {e}")

        except KeyboardInterrupt:
            logging.info("Kullanıcı tarafından durduruldu.")
        finally:
            self.running = False
            if self.sock:
                self.sock.close()
            logging.info("UDP soketi kapatıldı.")


if __name__ == "__main__":
    srv = UDPServer()
    try:
        srv.start()
    except KeyboardInterrupt:
        pass
    finally:
        logging.info("Program sonlanıyor, veriler kaydediliyor...")
        save_server_results()