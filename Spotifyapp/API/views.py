from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import *
from requests import *
from django.http import HttpResponseRedirect
from .credentials import CLIENT_ID, CLIENT_SECRET, REDIRECT_URL


class AuthenticationURL(APIView):
    def get(self, request, format=None):
        scopes="user-read-currently-playing user-read-playback-state user-modify-playback-state "
        url= Request('GET', 'https://accounts.spotify.com/authorize',
                     params= {
                         'scope': scope,
                         'response_type': 'code',
                         'redirect_url': REDIRECT_URL,
                         'client_id': CLIENT_ID
                     }).prepare().url
        return HttpResponseRedirect(url)
