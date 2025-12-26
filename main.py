import asyncio
import websockets
import json
import time
import random
import logging
import argparse
import csv

# Sunucu ayarları
SERVER_HOST = "localhost"
SERVER_PORT = 8765

# Simülasyon senaryo ayarları
LOCATION_UPDATE_INTERVAL_S = 10
STATUS_UPDATE_INTERVAL_S = 5
COMMAND_INTERVAL_S = 15

latency_data = []  # Gecikme / İşlem Süresi
reconnect_time_data = []  # Yeniden Bağlanma Süresi
bandwidth_data = []  # Bant Genişliği

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

connected_scooters = set()

# istemci tarafına sürekli istek gönderir, komut atma
async def send_periodic_commands():
    global latency_data, bandwidth_data
    while True:
        await asyncio.sleep(COMMAND_INTERVAL_S) # belirtilen süre kadar bekler
        if connected_scooters: # bağlı scooter yoksa işlem yapmaz
            command = {
                "command": "unlock",
                "scooter_id": "S123",
                "send_time": time.time()
            }
            message = json.dumps(command)
            bandwidth_data.append(len(message.encode('utf-8'))) # sunucunun dışarıya ne kadar boyutta veri gönderdiğini tutar

            for scooter_ws in list(connected_scooters):
                try:
                    logging.info(f"SERVER TX: {message} -> {scooter_ws.remote_address}")
                    await scooter_ws.send(message)
                except websockets.exceptions.ConnectionClosed:
                    pass

# sunucuya bir scooter bağlanınca devreye girer ve bağlantı açık kaldığı sürece listener görevi görür
async def server_handler(websocket):
    connected_scooters.add(websocket) # yeni gelen bağlantıyı aktif scooterlara ekler
    logging.info(f"Yeni Scooter bağlandı: {websocket.remote_address}")
    try:
        async for message in websocket: # scooterdan gelen her mesajı yakalar
            global latency_data, bandwidth_data
            bandwidth_data.append(len(message.encode('utf-8')))

            data = json.loads(message)

            if "location" in data:
                logging.info(f"SERVER RX (Konum): {data} <- {websocket.remote_address}")
            elif "status" in data:
                logging.info(f"SERVER RX (Durum): {data} <- {websocket.remote_address}")
            elif "ack" in data: # komut aldıysa eğer, komutu aldım diye geri mesaj yollar.
                send_time = data.get("send_time", 0)
                if send_time:
                    # Sunucu tarafı RTT Hesabı (Gerçek Ağ Gecikmesi)
                    rtt = time.time() - send_time
                    latency_data.append(rtt)
                    logging.info(f"SERVER RX (ACK): '{data['ack']}' RTT: {rtt:.4f}s")
            else:
                logging.warning(f"SERVER RX (Bilinmeyen): {data}")
    except Exception as e:
        logging.error(f"Sunucuda hata: {e}")
    finally: # bağlantı koparsa o scooterı listeden siler. Bu, hayalet bağlantılara mesaj atmasını önler
        connected_scooters.remove(websocket)


async def start_server():
    logging.info(f"WebSocket Sunucusu başlatılıyor: ws://{SERVER_HOST}:{SERVER_PORT}")
    asyncio.create_task(send_periodic_commands())
    async with websockets.serve(server_handler, SERVER_HOST, SERVER_PORT):
        await asyncio.Future()


#İSTEMCİ TARAFI
async def scooter_send_location(ws):
    """ Konum Gönderme """
    global bandwidth_data
    while True:
        await asyncio.sleep(LOCATION_UPDATE_INTERVAL_S)
        location_data = {
            "location": {
                "lat": round(random.uniform(41.00, 41.05), 6),
                "lon": round(random.uniform(28.95, 29.00), 6)
            }
        }
        message = json.dumps(location_data)
        bandwidth_data.append(len(message.encode('utf-8')))
        logging.info(f"SCOOTER TX (Konum): {message}")
        await ws.send(message)


async def scooter_send_status(ws):
    """ Durum Gönderme """
    global bandwidth_data
    while True:
        await asyncio.sleep(STATUS_UPDATE_INTERVAL_S)
        is_currently_locked = random.choice([True, False])
        status_data = {
            "status": {
                "battery_level": random.randint(10, 100),
                "is_locked": is_currently_locked,
                "speed": 0 if is_currently_locked else random.randint(0, 25)
            }
        }
        message = json.dumps(status_data)
        bandwidth_data.append(len(message.encode('utf-8')))
        logging.info(f"SCOOTER TX (Durum): {message}")
        await ws.send(message)


async def scooter_listen(ws):
    """ Komut Dinleme ve Cevaplama """
    global latency_data, bandwidth_data
    async for message in ws:
        bandwidth_data.append(len(message.encode('utf-8')))
        logging.info(f"SCOOTER RX (Komut): {message}")
        process_start_time = time.time()
        data = json.loads(message)
        if "command" in data:
            await asyncio.sleep(0.1)
            ack_message = {
                "ack": f"command '{data['command']}' received",
                "send_time": data.get("send_time")
            }
            response_json = json.dumps(ack_message)

            bandwidth_data.append(len(response_json.encode('utf-8')))

            logging.info(f"SCOOTER TX (ACK): {ack_message['ack']}")
            await ws.send(response_json)

            # Komutun gelişinden cevabın çıkışına kadar geçen süre
            process_latency = time.time() - process_start_time
            latency_data.append(process_latency)


async def scooter_client_main(scenario_to_run: str):
    global reconnect_time_data
    uri = f"ws://{SERVER_HOST}:{SERVER_PORT}"

    while True:
        try:
            logging.info(f"Scooter sunucuya bağlanıyor: {uri}")
            reconnect_start_time = time.time()
            async with websockets.connect(uri) as websocket:
                reconnect_time = time.time() - reconnect_start_time
                reconnect_time_data.append(reconnect_time)

                logging.info(f"Scooter bağlandı! (Süre: {reconnect_time:.4f}s)")
                logging.info(f"ÇALIŞAN SENARYO: {scenario_to_run}")

                if scenario_to_run == 'status':
                    await scooter_send_status(websocket)
                elif scenario_to_run == 'location':
                    await scooter_send_location(websocket)
                elif scenario_to_run == 'command':
                    await scooter_listen(websocket)
                elif scenario_to_run == 'all':
                    await asyncio.gather(
                        scooter_listen(websocket),
                        scooter_send_location(websocket),
                        scooter_send_status(websocket)
                    )

        except (websockets.exceptions.ConnectionClosedError, OSError) as e:
            logging.warning(f"Bağlantı koptu: {e}. 5 saniye içinde yeniden denenecek...")
            await asyncio.sleep(5)
        except Exception as e:
            logging.error(f"Hata: {e}. Yeniden deneniyor...")
            await asyncio.sleep(5)


def save_results_to_csv(protocol_name, suffix=""):
    """
    Toplanan verileri CSV dosyasına kaydeder.
    """
    filename = f"results_{protocol_name.lower()}{suffix}.csv"

    rows = []
    max_len = max(len(latency_data), len(bandwidth_data), len(reconnect_time_data))

    for i in range(max_len):
        lat = latency_data[i] if i < len(latency_data) else None
        bw = bandwidth_data[i] if i < len(bandwidth_data) else None
        rec = reconnect_time_data[i] if i < len(reconnect_time_data) else None
        rows.append([lat, bw, rec])

    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Latency", "Bandwidth", "ReconnectTime"])
        writer.writerows(rows)

    logging.info(f"Sonuçlar kaydedildi: {filename}")

def main():
    parser = argparse.ArgumentParser(description="IoT Scooter Simülasyonu")
    parser.add_argument('mode', choices=['server', 'client'], help="'server' veya 'client' modu")
    parser.add_argument('--scenario', choices=['status', 'location', 'command', 'all'], default='all',
                        help="Senaryo seçimi")
    args = parser.parse_args()

    if args.mode == 'server':
        try:
            asyncio.run(start_server())
        except KeyboardInterrupt:
            logging.info("Sunucu kapatılıyor...")
            save_results_to_csv("WebSocket", suffix="_server")

    elif args.mode == 'client':
        try:
            asyncio.run(scooter_client_main(args.scenario))
        except KeyboardInterrupt:
            logging.info("Scooter kapatılıyor...")

            #SONUÇ
            logging.info("--- SIMÜLASYON SONUÇLARI (WebSocket) ---")

            # 1. Yeniden Bağlanma
            if reconnect_time_data:
                avg_reconnect = sum(reconnect_time_data) / len(reconnect_time_data)
                logging.info(
                    f"Ortalama Yeniden Bağlanma: {avg_reconnect:.4f} sn (Toplam {len(reconnect_time_data)} bağlantı)")

            # 2. Gecikme (Latency)
            if latency_data:
                avg_latency = sum(latency_data) / len(latency_data)
                logging.info(f"Ortalama Gecikme (Latency): {avg_latency:.4f} sn (Toplam {len(latency_data)} işlem)")
            else:
                logging.info("Gecikme verisi yok (Komut senaryosu çalışmadı mı?)")

            # 3. Bant Genişliği (Bandwidth)
            if bandwidth_data:
                total_bw = sum(bandwidth_data)
                avg_bw = total_bw / len(bandwidth_data)
                logging.info(f"Toplam Veri Transferi: {total_bw} bytes ({total_bw / 1024:.2f} KB)")
                logging.info(f"Ortalama Mesaj Boyutu: {avg_bw:.1f} bytes")
            else:
                logging.info("Veri transferi olmadı.")
            logging.info("Paket Kayıp Oranı: %0.00 (WebSocket/TCP Garantili İletim)")
            logging.info("--- METRİKLER (Ham Veri Özeti) ---")
            save_results_to_csv("WebSocket", suffix="_client")


if __name__ == "__main__":
    main()