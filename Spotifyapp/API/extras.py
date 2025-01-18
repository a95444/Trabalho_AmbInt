from .models import Token
from django.utils import  timezone
from datetime import timedelta

BASE_URL='https://api.spotify.com/v1/me'

# 1- Check Tokens

def check_token(session_id):
    tokens = Token.objects.filter