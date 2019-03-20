from django.dispatch import receiver
import registration.signals

from comics_db import models


@receiver(registration.signals.user_registered)
def create_profile(sender, user, request, **kwargs):
    profile = models.Profile()
    profile.user = user
    profile.save()
