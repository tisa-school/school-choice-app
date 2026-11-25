"""Opt-in mobile records. Raw access tokens are never stored in the database."""
from django.conf import settings
from django.db import models
from django.db.models import Q

class MobileSession(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    token_hash=models.CharField(max_length=64,unique=True)
    platform=models.CharField(max_length=8,choices=[('ios','iOS'),('android','Android'),('web','Development web')])
    expires_at=models.DateTimeField(db_index=True)
    revoked=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)

class MobilePushDevice(models.Model):
    session=models.OneToOneField(MobileSession,on_delete=models.CASCADE)
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    token=models.CharField(max_length=4096)
    platform=models.CharField(max_length=8)
    enabled=models.BooleanField(default=True)
    updated_at=models.DateTimeField(auto_now=True)

class MobileDeletionRequest(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    status=models.CharField(max_length=12,choices=[('pending','Pending'),('completed','Completed')],default='pending')
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['user'],condition=Q(status='pending'),name='one_pending_mobile_deletion')]
