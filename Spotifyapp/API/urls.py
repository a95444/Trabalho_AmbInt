from .views import *
from django.urls import path
from .views import SyncedHeartRateMusic


urlpatterns=[
    path("auth-url", AuthenticationURL.as_view()),
    path("redirect", spotify_redirect),
    path("check-auth", CheckAuthentication.as_view()),
    path("current-song", CurrentSong.as_view()),
    path("controls/", SpotifyControls.as_view(), name="spotify-controls"),
    #path("heart-rate/", HeartRateAPI.as_view(), name="heart-rate-api"),
    path("api/synced-data/", SyncedHeartRateMusic.as_view(), name="synced-data/"),
    path('api/artist-stats/', artist_stats),
    path('api/genre-stats/', genre_stats),
    ]