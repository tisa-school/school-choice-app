"""Remove private image bytes when their owning record is removed or replaced."""
from django.db import transaction
from django.db.models.signals import post_delete,pre_save
from django.dispatch import receiver
from .models import TeamPhoto,ExperiencePhoto

@receiver(post_delete,sender=TeamPhoto)
@receiver(post_delete,sender=ExperiencePhoto)
def delete_photo_bytes(sender,instance,**kwargs):
    if instance.image:
        storage,name=instance.image.storage,instance.image.name
        transaction.on_commit(lambda:storage.delete(name))

@receiver(pre_save,sender=TeamPhoto)
def replace_photo_bytes(sender,instance,**kwargs):
    if not instance.pk:return
    old=sender.objects.filter(pk=instance.pk).first()
    if old and old.image and old.image.name!=instance.image.name:
        storage,name=old.image.storage,old.image.name
        transaction.on_commit(lambda:storage.delete(name))
