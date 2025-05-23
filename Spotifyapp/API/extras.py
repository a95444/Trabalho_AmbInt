import requests
from .models import Token
from django.utils import  timezone
from datetime import timedelta
from requests import *
from.credentials import *
import json
import time
BASE_URL='https://api.spotify.com/v1/me/'
BASE_URL_ARTISTS='https://api.spotify.com/v1/'

# 1- Check Tokens

def check_token(session_id):
    tokens = Token.objects.filter(user = session_id)
    if tokens:
        return tokens[0]
    else:
        return None

# 2- Create and update the token model
def create_or_update_tokens(session_id, access_token, refresh_token, expires_in, token_type):
    tokens = check_token(session_id)
    expires_in = timezone.now() + timedelta(seconds=expires_in)

    #update tokens if the exsit
    if tokens:
        tokens.access_token = access_token
        tokens.refresh_token = refresh_token
        tokens.expires_in = expires_in
        tokens.type = token_type
        tokens.save(update_fields=['access_token', 'refresh_token', 'expires_in', 'token_type'])

        return tokens

    else:
        tokens = Token(
            user = session_id,
            access_token = access_token,
            refresh_token = refresh_token,
            expires_in = expires_in,
            token_type = token_type,
        )
        tokens.save()

def is_spotify_authenticated(session_id):
    tokens = check_token(session_id)

    if tokens:
        if tokens.expires_in <= timezone.now():
            refresh_token_function(session_id)  # Refresh token if expired
        return True
    return False

# 4 - Refresh token function
def refresh_token_function(session_id):
    refresh_token = check_token(session_id).refresh_token

    response = post('https://accounts.spotify.com/api/token', data={
        'grant_type': 'authorization_code',
        'refresh_token': refresh_token,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }).json()

    access_token=response.get('access_token')
    expires_in=response.get('expires_in')
    token_type=response.get('token_type')

    create_or_update_tokens(
        session_id=session_id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        token_type=token_type,
    )


def spotify_requests_execution(session_id, endpoint, params=None, method="get"):
    token = check_token(session_id)

    if not token:
        return {'error': {'message': 'Token inválido'}}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token.access_token}"
    }

    try:
        # Endpoints que modificam estado
        if endpoint in ["player/pause", "player/play"]:
            print("REQUESTE DOS BOTÕES CHEGOU")
            response = put(BASE_URL + endpoint, headers=headers)
        elif endpoint in ["player/next", "player/previous"]:
            print("REQUESTE DOS BOTÕES CHEGOU")
            response = post(BASE_URL + endpoint, headers=headers)
        elif endpoint in "player/queue":
            print("REQUEST QUEUE")
            try:
                response = post(BASE_URL + endpoint, headers=headers, params=params)
                if response.status_code == 204:  # Resposta bem-sucedida sem conteúdo
                    return {'status': 'success'}
                return response.json()
            except json.JSONDecodeError:
                return {'status': 'success'}  # Resposta vazia é normal para esta operação
        else:
            response = get(BASE_URL + endpoint, headers=headers)

        # Tratamento consistente de respostas
        if not response.ok:
            try:
                return {'error': response.json()}
            except:
                return {'error': {'message': f"HTTP {response.status_code}"}}

        try:
            return response.json() if response.content else {'status': 'no_content'}
        except ValueError:
            return {'error': {'message': 'Resposta inválida da API'}}

    except Exception as e:
        print(f"Erro na requisição para {endpoint}: {str(e)}")
        return {'error': {'message': str(e)}}

def spotify_requests_artists(session_id, endpoint, max_retries=3):
    token = check_token(session_id)
    if not token:
        return {'error': {'message': 'Token inválido'}}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token.access_token}"
    }

    for attempt in range(max_retries + 1):
        try:
            # Construção dinâmica da URL
            if "artists/" in endpoint:
                url = BASE_URL_ARTISTS + endpoint
                print(f"Artists url: {url}")
                response = requests.get(url, headers=headers)
            elif "audio-features/" in endpoint:
                url = BASE_URL_ARTISTS + endpoint
                print(f"Audio Features url: {url}")
                response = requests.get(url, headers=headers)
            else:
                url = BASE_URL + endpoint
                response = requests.get(url, headers=headers)

            print(f"Response Status: {response.status_code}")

            # Tratamento de Rate Limit (429)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 10))  # Default 10s
                print(f"Tempodeespera: {retry_after} ")
                retry_after = min(retry_after, 60)  # Limita a 60 segundos <--- Correção
                print(f"⚠️ Aguardando {retry_after}s...")
                time.sleep(retry_after)
                continue

            # Tratamento de outros erros HTTP
            if not response.ok:
                try:
                    return {'error': response.json()}
                except:
                    return {'error': {'message': f"HTTP {response.status_code}"}}

            # Processamento de resposta bem-sucedida
            return response.json() if response.content else {'status': 'no_content'}

        except Exception as e:
            print(f"Erro na requisição para {endpoint}: {str(e)}")
            if attempt == max_retries:  # Última tentativa
                return {'error': {'message': str(e)}}
            time.sleep(2 ** attempt)  # Backoff exponencial para outros erros

    return {'error': {'message': 'Número máximo de tentativas excedido'}}

def spotify_seek(session_id, position_ms):
    token = check_token(session_id)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token.access_token}",
    }

    # Correct endpoint
    endpoint = f"player/seek?position_ms={position_ms}"
    #print(f"BASE_URL 2: {BASE_URL + endpoint}")

    response = put(BASE_URL + endpoint, headers=headers)

    if response.status_code == 204:
        return {"success": True, "message": "Seek successful"}
    else:
        try:
            # Only attempt to parse the JSON if the status code is not 204
            response_data = response.json()
            return {"success": False, "message": "Seek failed", "details": response_data}
        except requests.exceptions.JSONDecodeError:
            # If JSON decoding fails, handle the error gracefully
            return {"success": False, "message": "Seek failed, no JSON response", "details": response.text}



from ctypes import cast, POINTER
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import comtypes
from comtypes import CoInitialize, CoUninitialize, CLSCTX_ALL
from comtypes.automation import POINTER
comtypes.CoUninitialize()  # Limpa qualquer estado residual

def get_system_volume():
    try:
        CoInitialize()  # Inicializa o COM uma vez por thread
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioEndpointVolume._iid_,
            CLSCTX_ALL,
            None
        )
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        current_volume = volume.GetMasterVolumeLevelScalar()
        return int(current_volume * 100)
    except Exception as e:
        print(f"Erro ao obter volume: {str(e)}")
        return 50  # Valor padrão seguro
    finally:
        CoUninitialize()  # Libera recursos COM obrigatoriamente


def set_system_volume(volume_percent=30):
    try:
        CoInitialize()
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioEndpointVolume._iid_,
            CLSCTX_ALL,
            None
        )
        volume = cast(interface, POINTER(IAudioEndpointVolume))

        # Garante que o valor está entre 0 e 100
        volume_percent = max(0, min(100, volume_percent))
        volume_level = volume_percent / 100.0

        volume.SetMasterVolumeLevelScalar(volume_level, None)
        return True
    except Exception as e:
        print(f"Erro ao definir volume: {str(e)}")
        return False
    finally:
        CoUninitialize()
