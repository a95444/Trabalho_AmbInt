import requests
from .models import Token
from django.utils import  timezone
from datetime import timedelta
from requests import *
from.credentials import *


BASE_URL='https://api.spotify.com/v1/me/'

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



def spotify_requests_execution(session_id, endpoint):
    token = check_token(session_id)
    #print(f"TOKEN TOKEN: {token}")
    headers = {"Content-Type": "application/json", 
               'Authorization' : 'Bearer ' + token.access_token}

    #get data on the song from spotify API
    #print(f"URL DO REQUEST: {BASE_URL}{endpoint}")

    # Ensure you're using PUT for controlling playback
    if endpoint == "player/pause" or endpoint == "player/play":
        response = put(BASE_URL + endpoint, {}, headers=headers)
    elif endpoint == "player/next" or endpoint == "player/previous":
        response = post(BASE_URL + endpoint, {}, headers=headers)
    else:
        response = get(BASE_URL + endpoint, {}, headers=headers)

    if response:
        pass
        #print(response)
    else:
        print('No Response on spotify_requests_Execution!')

    try:
        return response.json()
    except:
        return {'Error' : 'Issue with request'}
    

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
