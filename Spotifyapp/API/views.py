from django.shortcuts import render, redirect
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response as Response_status
from rest_framework import *
from requests import *
from django.http import HttpResponseRedirect, JsonResponse
from .credentials import CLIENT_ID, CLIENT_SECRET, REDIRECT_URL
from .extras import *

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


class CurrentSong(APIView):
    kwarg = "key"
    def get(self, request, format=None):
        key = request.GET.get(self.kwarg)
        token = Token.objects.filter(user = key)
        #print(token)

        #create an endpoint
        endpoint = "player/currently-playing"
        response = spotify_requests_execution(key, endpoint)

        if "error" in response or "item" not in response:
            #print(f"RESPONSE: {response}")
            try:
                if 'token expired' in response['error']['message']:
                    #print("CORRI CRLH")
                    return redirect(AuthenticationURL)
            except:
                return Response_status({}, status=204)  # Use numeric status code directly

        item = response.get('item') #objeto que vem do API que tem informações como o Album, nome da musica e afins
        progress= response.get('progress_ms') #vem do API e diz em que ponto da musica esta se a ouvir
        is_playing=response.get('is_playing')
        duration=item.get('duration_ms')
        song_id=item.get('id')
        title = item.get('name')
        album_cover = item.get('album').get('images')[0].get('url')

        artists = ""
        for i, artist in enumerate(item.get("artists")): #vai iterar sobre a lista de todos os artistas que vem do API, e vai concatenar a variavel artists
            if i>0:
                artists+=", "
    
            name =artist.get("name")
            artists+=name

        song={
            "id":song_id,
            "title":title,
            "artist":artists,
            "duration":duration,
            "time":progress,
            "album_cover":album_cover,
            "is_playing":is_playing
        }
        '''        print(song)
        print(f"CURRENT SONG Key: {key}")
        print(f"CURRENT SONG Token: {Token.objects.filter(user=key)}")'''

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":  # AJAX request
            #print(f"SONG INFO NOW: {song}")
            return JsonResponse(song, status=200)

        return render(request, 'current_song_template.html', {'song': song, "user_token":token, "user_key":key})
        #return Response_status(song, status=status.HTTP_200_OK) #no 1º campo posso passar o que eu quiser desde que tenha um formato de dicionário, posso passar a Response toda, que tem informação de todas as coisas 
        

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
            "seek": "player/seek",  # Seek will need special handling
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

