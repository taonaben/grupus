import string
import time
import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta
import random


def get_otp_expiry():
    """Return OTP expiration time (10 minutes from now)"""
    return timezone.now() + timedelta(minutes=10)


# Create your models here.
class OTP(models.Model):

    def generate_token():
        MAX_ATTEMPTS = 10
        chars = string.digits
        for attempt in range(MAX_ATTEMPTS):
            # Generate token with pattern: XXXXXX (6 characters)
            token = "".join(random.choices(chars, k=6))
            token = int(token)  # Convert to integer

            if not OTP.objects.filter(token=token).exists():
                return token

        timestamp = hex(int(time.time()))[2:]
        return int(timestamp, 16) % (10**6)  # Ensure it's a 6-digit number

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    token = models.PositiveBigIntegerField(default=generate_token, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if self._state.adding:  # Only set expires_at when creating a new OTP
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"OTP for {self.email}"

    def is_expired(self):
        """Check if the OTP token has expired"""
        return timezone.now() > self.expires_at if self.expires_at else False

    class Meta:
        indexes = [
            models.Index(fields=["expires_at"]),
        ]
