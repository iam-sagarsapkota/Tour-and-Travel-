from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User, UserProfile


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        UserProfile.objects.create(user=instance)
