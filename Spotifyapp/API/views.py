from django.shortcuts import render, redirect
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response as Response_status
from rest_framework import *
from requests import *
from django.http import HttpResponseRedirect, JsonResponse
from .credentials import CLIENT_ID, CLIENT_SECRET, REDIRECT_URL
from .extras import *
import math
import requests
from .models import *
from django.shortcuts import render
import portalocker
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
import json
from datetime import datetime
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.shortcuts import redirect
from .connect_garmin import get_latest_heart_rate
from .extras import spotify_requests_execution
from rest_framework import status
from rest_framework.response import Response

def get_access_token(request):
    session_key = request.session.session_key
    token = Token.objects.get(user=session_key)
    return JsonResponse({'access_token': token.access_token})

class AuthenticationURL(APIView):
    def get(self, request, format=None):
        scopes="user-read-currently-playing user-read-playback-state user-modify-playback-state user-read-private user-read-email streaming"
        url= Request('GET', 'https://accounts.spotify.com/authorize',
                     params= {
                         'scope': scopes,
                         'response_type': 'code',
                         'redirect_uri': REDIRECT_URL,
                         'client_id': CLIENT_ID
                     }).prepare().url
        return HttpResponseRedirect(url)

def spotify_redirect(request, format=None):
    code=request.GET.get('code')
    error=request.GET.get('error')
    print("REDIRECT")
    if error:
        return error

    response = post('https://accounts.spotify.com/api/token', data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URL,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }).json()

    access_token=response.get('access_token')
    refresh_token=response.get('refresh_token')
    expires_in=response.get('expires_in')
    token_type=response.get('token_type')

    authKey = request.session.session_key
    if not request.session.exists(authKey):
        request.session.create()
        authKey = request.session.session_key

    try:
        create_or_update_tokens(
            session_id=authKey,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            token_type=token_type,
        )
    except Exception as e:
        pass
    # Inicia o listener do Garmin após a autenticação
    from .connect_garmin import start_garmin_listener
    print("⏳ A conectar ao Garmin antes de redirecionar...")
    garmin_ready = start_garmin_listener()

    while not garmin_ready:
        print("❌ Falha na conexão com o Garmin, a tentar novamente...")
        garmin_ready = start_garmin_listener()

    if garmin_ready:
        print("✅ Garmin conectado! Redirecionando para a página atual...")

    #create a redirect url to the current song details
    redirect_url = f"http://127.0.0.1:8000/spotify/current-song?key={authKey}" #recebe o parametro que vem da classe currentsong
    return HttpResponseRedirect(redirect_url)


#Verify whether the user has been authenticated by Spotify
class CheckAuthentication(APIView):
    def get(self, request, format=None):
        key = self.request.session.session_key
        if not self.request.session.exists(key):
            self.request.session.create()
            key = self.request.session.session_key

        auth_status = is_spotify_authenticated(key)

        if auth_status:
            #will be redirected to the credentials of a song
            redirect_url= f"http://127.0.0.1:8000/spotify/current-song?key={key}"
            return  HttpResponseRedirect(redirect_url)
        else:
            #will redirect to the AuthenticationURL
            redirect_url=f"http://127.0.0.1:8000/spotify/auth-url"
            return HttpResponseRedirect(redirect_url)



def home(request):
    return render(request, 'home.html')



class CurrentSong(APIView):
    kwarg = "key"

    def get(self, request, format=None):
        key = request.GET.get(self.kwarg)
        token = Token.objects.filter(user=key)
        # print(token)

        # create an endpoint
        endpoint = "player/currently-playing"
        playback = spotify_requests_execution(key, endpoint)

        if "error" in playback or "item" not in playback:
            # print(f"RESPONSE: {response}")
            try:
                if 'token expired' in playback['error']['message']:
                    # print("CORRI CRLH")
                    return redirect(AuthenticationURL)
            except:
                return Response_status({}, status=204)  # Use numeric status code directly


        # print(f"Playback: {playback}")

        if isinstance(playback, str) or 'error' in playback or 'item' not in playback:
            return Response({'error': 'Erro ao obter música'}, status=status.HTTP_502_BAD_GATEWAY)

        item = playback['item']

        # 📢 Obtém volume/decibéis
        track_id = item['id']  # ID da faixa atual
        volume = int(get_system_volume())
        # print(f"volume {volume}")

        artist_id = playback['item']['artists'][0]['id']
        # print(f"Artist id {artist_id}")
        artist_data = spotify_requests_artists(key, f"artists/{artist_id}")

        #print(f"Artist data {artist_data}")
        #generos = artist_data['genres']
        artista = artist_data['name']

        # print(f"ITEM: {item}")
        musica = item['name']

        song = {
            "id": track_id,
            "title": musica,
            "artist": artista, #artista
            "album_cover": item['album']['images'][0]['url'],
            "time": playback.get('progress_ms', 0),
            "duration": item['duration_ms'],
        }
        '''        print(song)
        print(f"CURRENT SONG Key: {key}")
        print(f"CURRENT SONG Token: {Token.objects.filter(user=key)}")'''

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":  # AJAX request
            # print(f"SONG INFO NOW: {song}")
            return JsonResponse(song, status=200)

        return render(request, 'current_song_template.html', {'song': song, "user_token": token, "user_key": key})
        # return Response_status(song, status=status.HTTP_200_OK) #no 1º campo posso passar o que eu quiser desde que tenha um formato de dicionário, posso passar a Response toda, que tem informação de todas as coisas


class SpotifyControls(APIView):
    def post(self, request, format=None):
        key = request.data.get("key")
        action = request.data.get("action")  # 'resume', 'stop', 'seek', etc.
        print("O URL FUNCIONOU E TOU AQUI")
        if not key or not action:
            return Response_status({"error": "Missing key or action"}, status=status.HTTP_400_BAD_REQUEST)

        # Log the request
        print(f"SPOTIFY CONTROLS Key: {key}")
        print(f"SPOTIFY CONTROLS Action: {action}")

        # Define supported actions and their respective Spotify API endpoints
        action_endpoints = {
            "resume": "player/play",
            "stop": "player/pause",
            "seek": "player/seek",
            "skip": "player/next",
            "previous": "player/previous",
            "add_to_queue": "player/queue"
        }

        # Validate the action
        if action not in action_endpoints:
            return Response_status({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

        # Special handling for "seek"
        if action == "seek":
            position_ms = request.data.get("position")
            if not position_ms:
                return Response_status({"error": "Missing position for seek action"}, status=status.HTTP_400_BAD_REQUEST)
            endpoint = action_endpoints[action]
            response = spotify_seek(key, int(position_ms))
            print(f"RESPOSTA SEEK {response}") 
        elif action == "add_to_queue":
            print()
            uri = request.data.get("uri")
            if not uri:
                return Response_status({"error": "URI da música necessária"}, status=400)

            endpoint = "player/queue"
            params = {"uri": uri}
            response = spotify_requests_execution(key, endpoint, params=params, method="post")
            #print(f"RESPOSTA QUEUE {response}")

            return Response_status({"message": "Música adicionada à fila"}, status=200)
        else:
            # General execution for other actions
            endpoint = action_endpoints[action]
            response = spotify_requests_execution(key, endpoint)

        # Check response and return appropriate status
        if "error" in response:
            return Response_status({"error": response["error"]}, status=status.HTTP_400_BAD_REQUEST)

        return Response_status({"message": f"Action {action} executed successfully"}, status=status.HTTP_200_OK)


PERFIS_FILE = "perfis.json"
DEFAULT_PROFILE = "default"
#JSON_FILE = ""
# Substitua a linha global JSON_FILE por:
def get_json_file(request):
    """Obtém o arquivo JSON correto baseado na sessão"""
    profiles = load_profiles()
    print(f"ABC: {request.session.get('json_file', profiles[DEFAULT_PROFILE])}")
    return request.session.get('json_file', profiles[DEFAULT_PROFILE])


import time


class SyncedHeartRateMusic(APIView):
    def get(self, request):
        session_key = request.GET.get("session_key")
        if not session_key:
            return Response({"error": "Parâmetro 'session_key' é obrigatório"}, status=400)



        # 🩺 Obtém o último ritmo cardíaco
        heart_rate = get_latest_heart_rate()
        if heart_rate is None:
            return Response({"error": "Nenhum dado de ritmo cardíaco disponível"}, status=404)

        # 🎵 Obtém os dados da Música Atual
        playback = spotify_requests_execution(session_key, "player/currently-playing")
        #print(f"Playback: {playback}")

        if isinstance(playback, str) or 'error' in playback or 'item' not in playback:
            return Response({'error': 'Erro ao obter música'}, status=status.HTTP_502_BAD_GATEWAY)

        item = playback['item']


        # 📢 Obtém volume/decibéis
        track_id = item['id']  # ID da faixa atual
        volume = int(get_system_volume())
        #print(f"volume {volume}")

        artist_id = playback['item']['artists'][0]['id']
        #print(f"Artist id {artist_id}")
        artist_data = spotify_requests_artists(session_key, f"artists/{artist_id}")
        print(f"Artist data {artist_data}")
        generos = artist_data['genres']
        artista = artist_data['name']

        #print(f"ITEM: {item}")
        musica = item['name']


        # 📂 Guarda os dados no JSON
        entrada = {
            "timestamp": datetime.now().isoformat(),
            "ritmo_cardiaco": heart_rate,
            "decibeis_musica": 0,
            "musica": musica,
            "musica_id": track_id,
            "genero": generos,
            "artista": artista,
            "artista_id": artist_id,
            "volume":volume
        }

        response_data={
            "timestamp": datetime.now().isoformat(),
            "ritmo_cardiaco": heart_rate,
            "decibeis_musica": 0,
            "musica": musica,
            "genero": generos,
            "artista": artista,
            "album_cover": item['album']['images'][0]['url'],
            "time": playback.get('progress_ms', 0),
            "duration": item['duration_ms'],
            "volume": volume
        }

        #self._guardar_json(entrada)

        return Response((response_data, entrada), status=200)

    def _guardar_json(self, entrada, request):
        """Guarda os dados mantendo o histórico completo com lock"""
        for _ in range(3):  # Tentar até 3 vezes em caso de conflito
            try:
                json_file = get_json_file(request)
                print(f"GUARDAR JSON: {json_file}")
                with open(json_file, 'r+') as f:
                    portalocker.lock(f, portalocker.LOCK_EX)  # Bloqueio exclusivo

                    # Tenta ler dados existentes
                    try:
                        dados = json.load(f)
                    except (json.JSONDecodeError, FileNotFoundError):
                        dados = []

                    # Adiciona nova entrada
                    dados.append(entrada)

                    # Reescreve o arquivo inteiro
                    f.seek(0)
                    json.dump(dados, f, indent=4)
                    f.truncate()

                    return
            except (IOError, portalocker.LockException) as e:
                print(f"Erro de E/S, tentando novamente... ({str(e)})")
                time.sleep(0.1)
        raise Exception("Falha ao escrever no arquivo após 3 tentativas")


# views.py
@csrf_exempt
def save_latest(request):
    if request.method == 'POST':
        try:
            active_profile = request.session.get('active_profile', DEFAULT_PROFILE)
            profiles = load_profiles()
            json_file = request.session.get('json_file', profiles[DEFAULT_PROFILE])

            new_data = json.loads(request.body)

            # Modo 'r+' não cria o arquivo se não existir, use 'a+'
            with open(json_file, 'a+') as f:  # Alterado para 'a+' para criar arquivo se necessário
                portalocker.lock(f, portalocker.LOCK_EX)
                f.seek(0)  # Vai para o início para ler

                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = []  # Inicializa se arquivo estiver vazio/corrompido

                existing_data.append(new_data)

                f.seek(0)
                f.truncate()  # Limpa o arquivo antes de escrever
                json.dump(existing_data, f, indent=4)

            return JsonResponse({"status": "Dado salvo com sucesso"})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Método não permitido"}, status=405)

# views.py
from django.http import JsonResponse
from .extract_info import calcular_media_ritmo_por_artista, calcular_media_ritmo_por_genero


def artist_stats(request):
    try:
        import portalocker
        min_count = int(request.GET.get('min_count', 40))
        sort_order = request.GET.get('sort', 'desc')
        json_file = get_json_file(request)
        #print(f"artist_stats: {json_file}")

        with open(json_file, 'r') as f:
            portalocker.lock(f, portalocker.LOCK_SH)
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                return JsonResponse({"error": "Invalid JSON format"}, status=500)
            finally:
                portalocker.unlock(f)

        stats = calcular_media_ritmo_por_artista(data)

        # Filtrar e formatar para o frontend
        filtered_stats = {
            k: {
                "artista": v["artista"],
                "media_ritmo_cardiaco": v["media_ritmo_cardiaco"],
                "contagem": v["contagem"]
            }
            for k, v in stats.items() if v["contagem"] > min_count
        }

        sorted_stats = sorted(
            filtered_stats.items(),
            key=lambda x: x[1]["media_ritmo_cardiaco"],
            reverse=(sort_order == 'desc')
        )

        return JsonResponse(dict(sorted_stats), safe=False)

    except Exception as e:
        print(f"Erro em artist_stats: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)
import traceback


def genre_stats(request):
    json_file = get_json_file(request)
    print(f"genre_stats: {json_file}")
    try:
        import portalocker
        min_count = int(request.GET.get('min_count', 40))
        sort_order = request.GET.get('sort', 'desc')
        json_file = get_json_file(request)
        #print(f"genre_stats: {json_file}")
        with open(json_file, 'r') as f:
            portalocker.lock(f, portalocker.LOCK_SH)
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                return JsonResponse({"error": "Invalid JSON format"}, status=500)
            finally:
                portalocker.unlock(f)

        stats = calcular_media_ritmo_por_genero(data)
        #print(f"STATS {stats}")

        # Filtrar e formatar para o frontend
        filtered_stats = {
            k: {
                "media_ritmo_cardiaco": v["media_ritmo_cardiaco"],
                "contagem": v["contagem"],
                "musicas": list(v["musicas"])
            }
            for k, v in stats.items() if v["contagem"] > min_count
        }

        sorted_stats = sorted(
            filtered_stats.items(),
            key=lambda x: x[1]["media_ritmo_cardiaco"],
            reverse=(sort_order == 'desc')
        )
        #print(f"sortedSTATS {sorted_stats}")
        return JsonResponse(dict(sorted_stats), safe=False)

    except Exception as e:
        print(f"Erro em genre_stats: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


# views.py
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import random


@require_POST
def play_calm_song(request):
    try:
        data = json.loads(request.body)
        user_key = data.get('key')
        json_file = get_json_file(request)
        with open(json_file, 'r') as f:
            try:
                json_data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Erro no JSON: {str(e)}")
                return JsonResponse({"error": "Invalid JSON format"}, status=500)

            stats = calcular_media_ritmo_por_artista(json_data)

            # Filtrar artistas com mais de 50 registros
            filtered_artists = [
                (artist_id, data)
                for artist_id, data in stats.items()
                if data.get('contagem', 0) > 50
            ]

            # Ordenar por média de ritmo cardíaco (mais calmos primeiro)
            sorted_artists = sorted(
                filtered_artists,
                key=lambda x: (x[1]['media_ritmo_cardiaco'], x[1]['contagem'])
            )[:10]
            random.shuffle(sorted_artists)  # Embaralha os artistas

            if not sorted_artists:
                return JsonResponse({'error': 'Nenhum artista calmo encontrado'}, status=404)

            #print(f"Artistas filtrados: {len(filtered_artists)}")
            #print(f"Artistas ordenados: {[a[1]['artista'] for a in sorted_artists]}")
            all_tracks = []
            for artist_id, artist_data in sorted_artists:
                # Buscar top tracks para cada artista
                #print(f"artista nome: {artist_data}")
                response = spotify_requests_artists(user_key, f"artists/{artist_id}/top-tracks?country=PT")

                if response and 'tracks' in response:
                    # Adicionar 2 músicas por artista (ajuste conforme necessário)
                    if len(response['tracks']) > 2:
                        all_tracks.extend(random.sample(response['tracks'], 2))
                    else:
                        all_tracks.extend(response['tracks'])

            if not all_tracks:
                return JsonResponse({'error': 'Nenhuma música encontrada'}, status=404)

            #print(f"ALL TRACKS {len(all_tracks)}")
            # Selecionar 10 músicas aleatórias da lista combinada
            num_tracks = min(10, len(all_tracks))
            selected_tracks = random.sample(all_tracks, min(num_tracks, len(all_tracks)))

            return JsonResponse({
                'status': 'success',
                'track_uris': [track['uri'] for track in selected_tracks],
                'tracks': [{
                    'name': track['name'],
                    'artist': track['artists'][0]['name']
                } for track in selected_tracks]
            })

    except Exception as e:
        print(f"Erro no processamento: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@require_POST
def play_stimulating_song(request):
    try:
        data = json.loads(request.body)
        user_key = data.get('key')
        json_file = get_json_file(request)

        with open(json_file, 'r') as f:
            try:
                json_data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Erro no JSON: {str(e)}")
                return JsonResponse({"error": "Invalid JSON format"}, status=500)

            stats = calcular_media_ritmo_por_artista(json_data)

            # Filtrar artistas com mais de 50 registros
            filtered_artists = [
                (artist_id, data)
                for artist_id, data in stats.items()
                if data.get('contagem', 0) > 50
            ]

            # Ordenar por média de ritmo cardíaco (mais ativos primeiro)
            sorted_artists = sorted(
                filtered_artists,
                key=lambda x: (x[1]['media_ritmo_cardiaco'], x[1]['contagem']),
                reverse=True
            )[:10]
            random.shuffle(sorted_artists)  # Embaralha os artistas

            if not sorted_artists:
                return JsonResponse({'error': 'Nenhum artista calmo encontrado'}, status=404)

            #print(f"Artistas filtrados: {len(filtered_artists)}")
            print(f"Artistas ordenados: {[a[1]['artista'] for a in sorted_artists]}")
            all_tracks = []
            for artist_id, artist_data in sorted_artists:
                # Buscar top tracks para cada artista
                print(f"artista nome: {artist_data}")
                response = spotify_requests_artists(user_key, f"artists/{artist_id}/top-tracks?country=PT")

                if response and 'tracks' in response:
                    # Adicionar 2 músicas por artista (ajuste conforme necessário)
                    if len(response['tracks']) > 2:
                        all_tracks.extend(random.sample(response['tracks'], 2))
                    else:
                        all_tracks.extend(response['tracks'])

            if not all_tracks:
                return JsonResponse({'error': 'Nenhuma música encontrada'}, status=404)

            #print(f"ALL TRACKS {len(all_tracks)}")
            # Selecionar 10 músicas aleatórias da lista combinada
            num_tracks = min(10, len(all_tracks))
            selected_tracks = random.sample(all_tracks, min(num_tracks, len(all_tracks)))

            return JsonResponse({
                'status': 'success',
                'track_uris': [track['uri'] for track in selected_tracks],
                'tracks': [{
                    'name': track['name'],
                    'artist': track['artists'][0]['name']
                } for track in selected_tracks]
            })

    except Exception as e:
        print(f"Erro no processamento: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)



def set_volume_down(request):
    try:
        # Obtém o valor do volume do request GET
        volume = int(request.GET.get('volume', 30))  # Default 30 se não fornecido
    except (ValueError, TypeError):
        volume = 30

    if set_system_volume(volume):
        return JsonResponse({"status": "Success", "message": f"Volume set to {volume}%"})
    else:
        return JsonResponse({"status": "Error", "message": "Failed to set volume"}, status=500)

WEBHOOK_URL = "https://hook.eu2.make.com/0a1185wba2jcsi8utipxo46qf2ug3htx"  # URL fixa

@csrf_exempt  # Descomente e mantenha isso
def trigger_make_webhook(request):
    print("WEBHOOK COMECOU")
    try:
        print("WEBHOOK A CORRER BEM")
        payload = {
            "event": "notification_pushup",
            "user_id": 1,
            "timestamp": "2024-04-05T10:00:00Z"
        }

        response = requests.post(
            WEBHOOK_URL,  # Usa a URL fixa corrigida
            json=payload,
            timeout=5
        )

        return JsonResponse({"status": "Webhook acionado!" if response.status_code == 200 else "Erro no Make"})

    except Exception as e:
        print("WEBHOOK A CORREU MALLLL")
        return JsonResponse({"error": str(e)}, status=500)


#PERFIS
def load_profiles():
    """Carrega os perfis do arquivo JSON"""
    if not os.path.exists(PERFIS_FILE):
        return {DEFAULT_PROFILE: "dados_ritmo.json"}

    with open(PERFIS_FILE, 'r') as f:
        return json.load(f)  # Remove o [0], retorna o dicionário completo


def save_profiles(profiles):
    """Salva os perfis no arquivo JSON"""
    with open(PERFIS_FILE, 'w') as f:
        json.dump(profiles, f, indent=2)


@csrf_exempt
def get_profiles(request):
    """Obtém a lista de perfis disponíveis"""
    if request.method == 'GET':
        try:
            profiles = load_profiles()
            return JsonResponse({
                "profiles": list(profiles.keys()),
                "active_profile": request.session.get('active_profile', DEFAULT_PROFILE)
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Método não permitido"}, status=405)


@csrf_exempt
def create_profile(request):
    """Cria um novo perfil"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            profile_name = data.get('profile_name')

            profiles = load_profiles()

            if profile_name in profiles:
                return JsonResponse({"error": "Perfil já existe"}, status=400)

            # Cria o arquivo com uma lista vazia
            filename = f"dados_ritmo_{profile_name}.json"
            with open(filename, 'w') as f:
                json.dump([], f)  # Inicializa com array vazio

            profiles[profile_name] = filename
            save_profiles(profiles)

            return JsonResponse({"status": "Perfil criado", "profile": profile_name})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Método não permitido"}, status=405)


@csrf_exempt
def set_active_profile(request):
    """Define o perfil ativo"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            profile_name = data.get('profile_name')

            profiles = load_profiles()

            if profile_name not in profiles.keys():
                return JsonResponse({"error": "Perfil não encontrado"}, status=404)

            request.session['active_profile'] = profile_name
            request.session['json_file'] = profiles[profile_name]  # Armazena o nome do arquivo na sessão

            return JsonResponse({
                "status": "Perfil ativo atualizado",
                "profile": profile_name,
                "json_file": request.session['json_file']})


        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Método não permitido"}, status=405)