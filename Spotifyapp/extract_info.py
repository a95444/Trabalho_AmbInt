import json
import os

def calcular_media_ritmo_por_artista(dados_json):
    ritmo_cardiaco_por_artista = {}

    for entrada in dados_json:
        artista = entrada["artista"]
        print(artista)
        artista_id= entrada["artista_id"]
        ritmo_cardiaco = entrada["ritmo_cardiaco"]

        if artista_id not in ritmo_cardiaco_por_artista:
            ritmo_cardiaco_por_artista[artista_id] = {
                "artista": artista,
                "soma_ritmo_cardiaco": 0,
                "contagem": 0,
                "media_ritmo_cardiaco": 0.0
            }

        # Atualiza os valores
        ritmo_cardiaco_por_artista[artista_id]["soma_ritmo_cardiaco"] += ritmo_cardiaco
        ritmo_cardiaco_por_artista[artista_id]["contagem"] += 1
        ritmo_cardiaco_por_artista[artista_id]["media_ritmo_cardiaco"] = (
            ritmo_cardiaco_por_artista[artista_id]["soma_ritmo_cardiaco"] /
            ritmo_cardiaco_por_artista[artista_id]["contagem"]
        )

    return ritmo_cardiaco_por_artista


def calcular_media_ritmo_por_genero(dados_json):
    ritmo_cardiaco_por_genero = {}

    for entrada in dados_json:
        generos = entrada["genero"]  # Lista de géneros
        ritmo_cardiaco = entrada["ritmo_cardiaco"]
        musica = entrada["musica"]

        for genero in generos:
            if genero not in ritmo_cardiaco_por_genero:
                ritmo_cardiaco_por_genero[genero] = {
                    "soma_ritmo_cardiaco": 0,
                    "contagem": 0,
                    "media_ritmo_cardiaco": 0.0,
                    "musicas": set()
                }

            # Atualiza os valores
            ritmo_cardiaco_por_genero[genero]["soma_ritmo_cardiaco"] += ritmo_cardiaco
            ritmo_cardiaco_por_genero[genero]["contagem"] += 1
            ritmo_cardiaco_por_genero[genero]["media_ritmo_cardiaco"] = (
                ritmo_cardiaco_por_genero[genero]["soma_ritmo_cardiaco"] /
                ritmo_cardiaco_por_genero[genero]["contagem"]
            )
            ritmo_cardiaco_por_genero[genero]["musicas"].add(musica)

    return ritmo_cardiaco_por_genero


def calcular_media_ritmo_por_volume(dados_json):
    ritmo_cardiaco_por_volume = {}

    for entrada in dados_json:
        volume = entrada["volume"]
        ritmo_cardiaco = entrada["ritmo_cardiaco"]

        # Definir a faixa de volume (arredondando para o múltiplo de 10 mais próximo)
        faixa_volume = f"{(volume // 10) * 10}-{((volume // 10) * 10) + 9}"

        if faixa_volume not in ritmo_cardiaco_por_volume:
            ritmo_cardiaco_por_volume[faixa_volume] = {
                "soma_ritmo_cardiaco": 0,
                "contagem": 0,
                "media_ritmo_cardiaco": 0.0
            }

        # Atualiza os valores da faixa de volume
        ritmo_cardiaco_por_volume[faixa_volume]["soma_ritmo_cardiaco"] += ritmo_cardiaco
        ritmo_cardiaco_por_volume[faixa_volume]["contagem"] += 1
        ritmo_cardiaco_por_volume[faixa_volume]["media_ritmo_cardiaco"] = (
            ritmo_cardiaco_por_volume[faixa_volume]["soma_ritmo_cardiaco"] /
            ritmo_cardiaco_por_volume[faixa_volume]["contagem"]
        )

    return ritmo_cardiaco_por_volume


JSON_FILE = "dados_ritmo.json"
dados_json = json.load(open(JSON_FILE))

print(calcular_media_ritmo_por_volume(dados_json))