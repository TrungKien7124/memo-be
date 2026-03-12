from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.app_server.models.implemented.nfs_flashcard_model import Flashcard
from apps.srs.models.srs_card_srs_state_model import CardSRSState


@receiver(post_save, sender=Flashcard)
def create_srs_state_for_flashcard(sender, instance, created, **kwargs):
    if created:
        CardSRSState.objects.get_or_create(card=instance)
