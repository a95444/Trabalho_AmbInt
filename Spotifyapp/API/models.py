from django.db import models


class Token(models.Model):
    user = models.CharField(unique=True, max_length=255)
    access_token = models.CharField(max_length=500)
    refresh_token = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_in = models.DateTimeField()
    token_type = models.CharField(max_length=50)

class HeartRateData(models.Model):
    user_session = models.ForeignKey(Token, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    heart_rate = models.IntegerField()  # BPM
