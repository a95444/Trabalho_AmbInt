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




class AuthenticationURL(APIView):
    def get(self, request, format=None):
        scopes="user-read-currently-playing user-read-playback-state user-modify-playback-state  "
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

    create_or_update_tokens(
        session_id=authKey,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        token_type=token_type,
    )
    # Inicia o listener do Garmin após a autenticação
    from .connect_garmin import start_garmin_listener
    start_garmin_listener()

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



from rest_framework import status
from rest_framework.response import Response


class CurrentSong(APIView):
    kwarg = "key"

    def get(self, request, format=None):
        key = request.GET.get(self.kwarg)
        token = Token.objects.filter(user=key).first()

        if not token:
            return Response({'error': 'Token inválido'}, status=status.HTTP_401_UNAUTHORIZED)

        # Obtém o estado atual
        playback = spotify_requests_execution(key, "player/currently-playing")

        # Verifica se é string (caso inesperado)
        if isinstance(playback, str):
            return Response({'error': 'Resposta inválida da API'}, status=status.HTTP_502_BAD_GATEWAY)

        # Tratamento de erros
        if 'error' in playback:
            error_msg = playback.get('error', {}).get('message', 'Erro desconhecido')
            if 'expired' in str(error_msg).lower():
                return redirect(AuthenticationURL)
            return Response({}, status=status.HTTP_204_NO_CONTENT)

        if 'item' not in playback:
            return Response({}, status=status.HTTP_204_NO_CONTENT)

        item = playback['item']
        response_data = {
            "id": item['id'],
            "title": item['name'],
            "artist": ", ".join([a['name'] for a in item['artists']]),
            "duration": item['duration_ms'],
            "time": playback.get('progress_ms', 0),
            "album_cover": item['album']['images'][0]['url'],
            "is_playing": playback.get('is_playing', False)
        }

        # Busca extras apenas quando necessário
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            try:
                # Gêneros do artista
                artist = spotify_requests_execution(key, f"artists/{item['artists'][0]['id']}")
                if isinstance(artist, dict):
                    response_data['genres'] = artist.get('genres', [])

                # Audio Features
                features = spotify_requests_execution(key, f"audio-features/{item['id']}")
                if isinstance(features, dict):
                    response_data['audio_features'] = features

                # Volume e decibéis
                device = playback.get('device', {})
                volume = device.get('volume_percent', 50)
                response_data['volume_percent'] = volume
                response_data['decibels'] = 20 * math.log10(volume / 100) if volume > 0 else -60

            except Exception as e:
                print(f"Erro ao buscar extras: {str(e)}")

        return Response(response_data) if request.headers.get("X-Requested-With") == "XMLHttpRequest" \
            else render(request, 'current_song_template.html', {'song': response_data, "user_key": key})


class SpotifyControls(APIView):
    def post(self, request, format=None):
        key = request.data.get("key")
        action = request.data.get("action")  # 'resume', 'stop', 'seek', etc.

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
            "previous": "player/previous"
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
        else:
            # General execution for other actions
            endpoint = action_endpoints[action]
            response = spotify_requests_execution(key, endpoint)

        # Check response and return appropriate status
        if "error" in response:
            return Response_status({"error": response["error"]}, status=status.HTTP_400_BAD_REQUEST)

        return Response_status({"message": f"Action {action} executed successfully"}, status=status.HTTP_200_OK)


# views.py
'''class HeartRateAPI(APIView):
    def get(self, request):
        session_key = request.GET.get("session_key")
        print(f"Session Key recebida: {session_key}")

        if not session_key:
            print("Erro1")
            return Response({"error": "Parâmetro 'session_key' é obrigatório"}, status=400)

        try:
            token = Token.objects.get(user=session_key)
        except Token.DoesNotExist:
            print("Erro2")
            return Response({"error": "Sessão não encontrada"}, status=404)

        latest_hr = HeartRateData.objects.filter(user_session=token).order_by("-timestamp").first()

        if not latest_hr:
            print("Erro3")
            return Response({"heart_rate": None}, status=200)  # Retorna vazio se não houver dados

        print(latest_hr)
        print(latest_hr.heart_rate)
        return Response({"heart_rate": latest_hr.heart_rate})
'''

import json
import os
import math
from datetime import datetime
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.shortcuts import redirect
from .connect_garmin import get_latest_heart_rate
from .extras import spotify_requests_execution

JSON_FILE = "dados_ritmo.json"


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
        print(f"Playback: {playback}")
        if isinstance(playback, str) or 'error' in playback or 'item' not in playback:
            return Response({'error': 'Erro ao obter música'}, status=status.HTTP_502_BAD_GATEWAY)

        item = playback['item']


        # 📢 Obtém volume/decibéis
        track_id = item['id']  # ID da faixa atual
        audio_features = spotify_requests_execution(session_key, f"audio-features/{track_id}")

        # Verifica se a resposta é válida
        print(f"audio_feat {audio_features}")
        if isinstance(audio_features, dict) and 'loudness' in audio_features:
            decibeis = audio_features['loudness']
        else:
            decibeis = -60  # Valor padrão se falhar


        #print(f"ITEM: {item}")
        musica = item['name']
        artista = ", ".join([a['name'] for a in item['artists']])
        genero = []

        try:
            artist_data = spotify_requests_execution(session_key, f"artists/{item['artists'][0]['id']}")
            if isinstance(artist_data, dict):
                genero = artist_data.get('genres', [])
        except Exception:
            pass

        # 📂 Guarda os dados no JSON
        entrada = {
            "timestamp": datetime.now().isoformat(),
            "ritmo_cardiaco": heart_rate,
            "decibeis_musica": decibeis,
            "musica": musica,
            "genero": genero,
            "artista": artista,
        }

        response_data={
            "timestamp": datetime.now().isoformat(),
            "ritmo_cardiaco": heart_rate,
            "decibeis_musica": decibeis,
            "musica": musica,
            "genero": genero,
            "artista": artista,
            "album_cover": item['album']['images'][0]['url'],
            "time": playback.get('progress_ms', 0),
            "duration": item['duration_ms'],
        }

        self._guardar_json(entrada)

        return Response(response_data, status=200)



    def _guardar_json(self, entrada):
        """Guarda a entrada no ficheiro JSON sem sobrescrever os anteriores."""
        dados = []
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, "r") as f:
                try:
                    dados = json.load(f)
                except json.JSONDecodeError:
                    pass

        dados.append(entrada)

        with open(JSON_FILE, "w") as f:
            json.dump(dados, f, indent=4)

        #print(f"✅ Dados guardados: {entrada}")

'''
import json
import os
from datetime import datetime

JSON_FILE = "dados_ritmo.json"


def atualizar_dados(heart_rate=None, decibeis=None, musica=None, genero=None, artista=None):
    """Atualiza o ficheiro JSON com os novos dados."""
    dados = {}

    # Se o ficheiro já existe, carregar os dados atuais
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r") as f:
            try:
                dados = json.load(f)
            except json.JSONDecodeError:
                pass  # Se houver erro, começa com um dicionário vazio

    # Atualiza apenas os valores recebidos, mantendo os outros
    dados.update({
        "timestamp": datetime.now().isoformat(),
        "ritmo_cardiaco": heart_rate if heart_rate is not None else dados.get("ritmo_cardiaco"),
        "decibeis_musica": decibeis if decibeis is not None else dados.get("decibeis_musica"),
        "musica": musica if musica is not None else dados.get("musica"),
        "genero": genero if genero is not None else dados.get("genero"),
        "artista": artista if artista is not None else dados.get("artista"),
    })

    # Guarda os dados no ficheiro
    with open(JSON_FILE, "w") as f:
        json.dump(dados, f, indent=4)

    print("✅ JSON atualizado:", dados)
'''