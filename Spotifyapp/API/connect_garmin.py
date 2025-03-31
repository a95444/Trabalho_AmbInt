'''import asyncio
from bleak import BleakScanner

async def scan_ble_devices():
    devices = await BleakScanner.discover()
    for device in devices:
        print(f"Nome: {device.name}, Endereço: {device.address}")

asyncio.run(scan_ble_devices())
'''
#Nome: Forerunner 245, Endereço: C4:12:D4:3E:83:02

'''
def notification_handler(sender, data):
    """Processa os dados recebidos do Garmin"""
    heart_rate = data[1]  # O segundo byte contém o valor da frequência cardíaca
    print(f"Ritmo Cardíaco: {heart_rate} bpm")


async def connect_to_garmin():
    async with BleakClient(GARMIN_ADDRESS) as client:
        print(f"Conectado a {GARMIN_ADDRESS}")

        # Ativar notificações para receber dados em tempo real
        await client.start_notify(HEART_RATE_UUID, notification_handler)

        # Mantém a conexão ativa por 60 segundos
        await asyncio.sleep(60)

        # Para as notificações quando terminar
        await client.stop_notify(HEART_RATE_UUID)


asyncio.run(connect_to_garmin())
'''


'''
import requests
from django.utils import timezone

def send_heart_rate_to_django(session_key, heart_rate):
    try:
        response = requests.post(
            "http://localhost:8000/api/heart-rate/",
            json={
                "session_key": session_key,
                "heart_rate": heart_rate,
            }
        )
        print(f"Dados enviados: {response.status_code}")
    except Exception as e:
        print(f"Erro ao enviar dados: {e}")

async def connect_to_garmin():
    print("Comecei")
    async with BleakClient(GARMIN_ADDRESS) as client:
        print(f"Conectado a {GARMIN_ADDRESS}")
        await client.start_notify(HEART_RATE_UUID, lambda sender, data: send_heart_rate_to_django("SESSION_KEY_TEST", data[1]))
        await asyncio.sleep(60)  # Manter conexão'''

'''
import asyncio
from bleak import BleakClient
import requests
from django.conf import settings

GARMIN_ADDRESS = "C4:12:D4:3E:83:02"
HEART_RATE_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

def send_heart_rate_to_django(heart_rate):
    """Envia dados para uma API do Django."""
    try:
        requests.post(
            f"http://{settings.ALLOWED_HOSTS[0]}/api/heart-rate/",
            json={"heart_rate": heart_rate},
            timeout=3
        )
    except Exception as e:
        print(f"Erro ao enviar heart rate: {e}")

async def _connect_to_garmin():
    """Conexão assíncrona com o Garmin."""
    while True:  # Reconecta automaticamente em caso de falha
        try:
            async with BleakClient(GARMIN_ADDRESS) as client:
                print(f"Conectado ao Garmin {GARMIN_ADDRESS}")
                await client.start_notify(
                    HEART_RATE_UUID,
                    lambda sender, data: send_heart_rate_to_django(data[1])
                )
                while True:
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"Erro na conexão: {e}. Tentando reconectar em 5s...")
            await asyncio.sleep(5)

def start_garmin_listener():
    """Inicia o loop assíncrono em uma thread separada."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_connect_to_garmin())'''

# API/connect_garmin.py
import asyncio
import threading
from bleak import BleakClient

GARMIN_ADDRESS = "C4:12:D4:3E:83:02"
HEART_RATE_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

def print_heart_rate(heart_rate):
    print(f"❤️ Heart rate: {heart_rate} BPM")

async def _run_garmin_listener():
    while True:
        try:
            async with BleakClient(GARMIN_ADDRESS) as client:
                print(f"✅ Conectado ao Garmin {GARMIN_ADDRESS}")
                await client.start_notify(
                    HEART_RATE_UUID,
                    lambda sender, data: print_heart_rate(data[1])
                )
                while True:
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"❌ Erro: {e}. Reconectando em 5s...")
            await asyncio.sleep(5)

def start_listener():
    """Inicia o listener em uma thread separada."""
    print("listener iniciado")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_run_garmin_listener())

# Inicia automaticamente quando importado
garmin_thread = threading.Thread(target=start_listener, daemon=True)
garmin_thread.start()