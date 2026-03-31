from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from Backend.app.documents.models import Profile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Cria automaticamente um Profile toda vez que um User é criado."""
    if created:
        Profile.objects.get_or_create(
            user=instance,
            defaults={"role": "admin" if instance.is_staff else "user"}
        )