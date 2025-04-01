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
        scopes="user-read-currently-playing user-read-playback-state user-modify-playback-state user-read-private user-read-email"
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



from rest_framework import status
from rest_framework.response import Response


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
        # print(f"Artist data {artist_data}")
        generos = artist_data['genres']
        artista = artist_data['name']

        # print(f"ITEM: {item}")
        musica = item['name']

        song = {
            "id": track_id,
            "title": musica,
            "artist": artista,
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
        #print(f"Artist data {artist_data}")
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


# views.py
from django.http import JsonResponse
from .extract_info import calcular_media_ritmo_por_artista, calcular_media_ritmo_por_genero


def artist_stats(request):
    try:
        with open(JSON_FILE, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Erro no JSON na linha {e.lineno}, coluna {e.colno}: {e.msg}")
                print("Conteúdo problemático:", f.read()[e.pos - 50:e.pos + 50])
                return JsonResponse({"error": "Invalid JSON format"}, status=500)

        sort_order = request.GET.get('sort', 'desc')
        stats = calcular_media_ritmo_por_artista(data)
        sorted_stats = sorted(stats.items(),
                              key=lambda x: x[1]['media_ritmo_cardiaco'],
                              reverse=(sort_order == 'desc'))

        print(f"Artistas: {sorted_stats}")
        return JsonResponse(dict(sorted_stats), safe=False)

    except Exception as e:
        print("Erro em artist_stats:", str(e))
        return JsonResponse({"error": str(e)}, status=500)


def genre_stats(request):
    try:
        min_count = int(request.GET.get('min_count', 40))
        sort_order = request.GET.get('sort', 'desc')

        with open(JSON_FILE, 'r') as f:
            data = json.load(f)

        stats = calcular_media_ritmo_por_genero(data)

        # Filtra e converte para dicionário serializável
        filtered_stats = {
            k: {
                **v,
                "musicas": list(v["musicas"])  # Converte para lista
            }
            for k, v in stats.items()
            if v["contagem"] > min_count
        }

        sorted_stats = sorted(filtered_stats.items(),
                              key=lambda x: x[1]['media_ritmo_cardiaco'],
                              reverse=(sort_order == 'desc'))

        print(f"generos: {sorted_stats}")
        return JsonResponse(dict(sorted_stats), safe=False)

    except Exception as e:
        print("Erro em genre_stats:", str(e))
        return JsonResponse({"error": str(e)}, status=500)