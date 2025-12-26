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
    filename = "results_tcp_server.csv"

    global latency_data, bandwidth_data

    # Veri yoksa bile dosyayı oluşturmak için kontrol
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


class TCPServer:
    def __init__(self, port=8765):
        self.port = port
        self.clients = {}
        self.running = True

    def broadcast_commands(self):
        while self.running:
            time.sleep(15)
            if not self.clients: continue

            try:
                cmd = json.dumps({
                    "command": "unlock",
                    "send_time": time.time()
                }) + '\n'

                for s_id, client_sock in list(self.clients.items()):
                    try:
                        encoded_cmd = cmd.encode()
                        client_sock.sendall(encoded_cmd)
                        bandwidth_data.append(len(encoded_cmd))
                        logging.info(f"SERVER TX (Komut) -> {s_id}")
                    except:
                        pass
            except Exception as e:
                logging.error(f"Broadcast hatası: {e}")

    def handle_client(self, client_sock, addr):
        scooter_id = None
        buffer = ""
        try:
            while self.running:
                try:
                    client_sock.settimeout(1.0)  # Bloklanmayı önlemek için
                    data = client_sock.recv(4096)
                except socket.timeout:
                    continue
                except OSError:
                    break

                if not data: break

                bandwidth_data.append(len(data))
                buffer += data.decode()

                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if not line.strip(): continue

                    try:
                        msg = json.loads(line)
                        if msg['type'] == 'register':
                            scooter_id = msg['scooter_id']
                            self.clients[scooter_id] = client_sock
                            logging.info(f"Yeni Scooter Kaydedildi: {scooter_id}")

                        elif msg['type'] == 'ack':
                            # RTT Hesaplama
                            send_time = msg.get('send_time', 0)
                            if send_time:
                                rtt = time.time() - send_time
                                latency_data.append(rtt)
                                logging.info(f"SERVER RX (ACK) <- {scooter_id} | RTT: {rtt:.6f}s")

                        elif msg['type'] == 'location':
                            logging.info(f"SERVER RX (Konum) <- {scooter_id}")

                        elif msg['type'] == 'status':
                            logging.info(f"SERVER RX (Durum) <- {scooter_id}")
                    except json.JSONDecodeError:
                        pass

        except Exception as e:
            logging.error(f"Hata: {e}")
        finally:
            if scooter_id and scooter_id in self.clients:
                del self.clients[scooter_id]
            try:
                client_sock.close()
            except:
                pass

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', self.port))
        server.listen(5)
        server.settimeout(1.0)

        t_broadcast = threading.Thread(target=self.broadcast_commands, daemon=True)
        t_broadcast.start()

        logging.info(f"TCP Sunucusu Başlatılıyor: {self.port}")

        try:
            while self.running:
                try:
                    client, addr = server.accept()
                    threading.Thread(target=self.handle_client, args=(client, addr), daemon=True).start()
                except socket.timeout:
                    continue
                except OSError:
                    break
        except KeyboardInterrupt:
            logging.info("Kullanıcı tarafından durduruldu.")
        finally:
            self.running = False
            server.close()
            logging.info("Sunucu kapatıldı.")


if __name__ == "__main__":
    srv = TCPServer()
    try:
        srv.start()
    except KeyboardInterrupt:
        pass
    finally:
        logging.info("Program sonlanıyor, veriler kaydediliyor...")
        save_server_results()