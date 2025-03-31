import sys
try:
    from bleak import BleakClient
    print("✅ Bleak funciona!")
    print("Python path:", sys.executable)
except ImportError as e:
    print("❌ Falha no Bleak:")
    print("Erro:", e)
    print("Path:", sys.path)