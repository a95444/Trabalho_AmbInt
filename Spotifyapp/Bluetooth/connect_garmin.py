'''import asyncio
from bleak import BleakScanner

async def scan_ble_devices():
    devices = await BleakScanner.discover()
    for device in devices:
        print(f"Nome: {device.name}, Endereço: {device.address}")

asyncio.run(scan_ble_devices())
'''
#Nome: Forerunner 245, Endereço: C4:12:D4:3E:83:02

import asyncio
from bleak import BleakClient

GARMIN_ADDRESS = "C4:12:D4:3E:83:02"  # Substitui pelo endereço do teu Garmin
HEART_RATE_UUID = "00002a37-0000-1000-8000-00805f9b34fb"  # UUID padrão da frequência cardíaca BLE


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
