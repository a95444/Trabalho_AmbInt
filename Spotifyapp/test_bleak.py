'''import sys
try:
    from bleak import BleakClient
    print("✅ Bleak funciona!")
    print("Python path:", sys.executable)
except ImportError as e:
    print("❌ Falha no Bleak:")
    print("Erro:", e)
    print("Path:", sys.path)

'''
import asyncio
from bleak import BleakScanner

async def scan_ble_devices():
    print("iniciou")
    devices = await BleakScanner.discover()
    for device in devices:
        print(f"Nome: {device.name}, Endereço: {device.address}")

asyncio.run(scan_ble_devices())