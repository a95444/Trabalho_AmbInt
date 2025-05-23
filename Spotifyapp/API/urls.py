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
    path('api/play_calm_song/', play_calm_song),
    path('api/play_stimulating_song/', play_stimulating_song),
    path('api/get-token/', get_access_token, name='get-token'),
    path('api/set_volume_down/', set_volume_down, name='set_volume_down'),
    path('api/trigger-webhook/', trigger_make_webhook, name='trigger-webhook'),
    path('api/save-latest/', save_latest, name='save-latest'),
    path('api/get-profiles/', get_profiles, name='get-profiles'),
    path('api/create-profile/', create_profile, name='create-profile'),
    path('api/set-active-profile/', set_active_profile, name='set-active-profile'),

    ]

