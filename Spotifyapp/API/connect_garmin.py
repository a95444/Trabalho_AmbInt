import asyncio
import threading
from bleak import BleakClient

GARMIN_ADDRESS = "C4:12:D4:3E:83:02"
HEART_RATE_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

# Variável global para armazenar o último ritmo cardíaco
latest_heart_rate = None

def update_heart_rate(heart_rate):
    """Atualiza o valor global do ritmo cardíaco"""
    global latest_heart_rate
    latest_heart_rate = heart_rate
    #print(f"❤️ Ritmo cardíaco atualizado: {latest_heart_rate} BPM")

async def _run_garmin_listener():
    while True:
        try:
            async with BleakClient(GARMIN_ADDRESS) as client:
                print(f"✅ Conectado ao Garmin {GARMIN_ADDRESS}")
                await client.start_notify(
                    HEART_RATE_UUID,
                    lambda sender, data: update_heart_rate(data[1])
                )
                while True:
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"❌ Erro na conexão: {e}. Tentando reconectar em 2s...")
            await asyncio.sleep(2)

def start_garmin_listener():
    """Inicia o listener numa thread separada."""
    listener_thread = threading.Thread(target=lambda: asyncio.run(_run_garmin_listener()), daemon=True)
    listener_thread.start()
    return listener_thread

def get_latest_heart_rate():
    """Retorna o último valor do ritmo cardíaco capturado"""
    return latest_heart_rate
