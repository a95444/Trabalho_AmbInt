import asyncio
import threading
from bleak import BleakClient

GARMIN_ADDRESS = "C4:12:D4:3E:83:02"
HEART_RATE_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

latest_heart_rate = None
garmin_connected = False  # Flag para verificar se conectou


def update_heart_rate(heart_rate):
    """Atualiza o valor global do ritmo cardíaco"""
    global latest_heart_rate
    latest_heart_rate = heart_rate


async def _initial_garmin_connection():
    """Tenta conectar ao Garmin e retorna True se for bem-sucedido"""
    global garmin_connected
    try:
        async with BleakClient(GARMIN_ADDRESS) as client:
            print(f"✅ Conectado ao Garmin {GARMIN_ADDRESS}")
            garmin_connected = True  # Define flag de sucesso
            return True
    except Exception as e:
        print(f"❌ Falha na conexão inicial: {e}")
        return False


async def _run_garmin_listener():
    """Mantém a escuta contínua das notificações do Garmin"""
    global garmin_connected
    while True:
        try:
            async with BleakClient(GARMIN_ADDRESS) as client:
                print(f"🔊 Escutando dados do Garmin {GARMIN_ADDRESS}")
                await client.start_notify(
                    HEART_RATE_UUID,
                    lambda sender, data: update_heart_rate(data[1])
                )
                while True:
                    await asyncio.sleep(1)  # Mantém o loop ativo
        except Exception as e:
            print(f"⚠️ Erro na escuta do Garmin: {e}. Tentando reconectar...")
            await asyncio.sleep(2)


def start_garmin_listener():
    """Bloqueia até conectar e depois roda o listener em segundo plano."""
    global garmin_connected

    print("🔄 A aguardar conexão ao Garmin...")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    success = loop.run_until_complete(_initial_garmin_connection())  # Bloqueia até conectar

    if success:
        print("🚀 Iniciando escuta contínua...")
        listener_thread = threading.Thread(target=lambda: asyncio.run(_run_garmin_listener()), daemon=True)
        listener_thread.start()
        return True

    return False


def get_latest_heart_rate():
    """Retorna o último valor do ritmo cardíaco capturado"""
    return latest_heart_rate
