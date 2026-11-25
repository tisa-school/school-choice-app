"""Explicit, server-only delivery adapter. Never includes child/profile content on a lock screen.
Optional dependencies are installed separately; no network call occurs on import or API reads.
"""
import json
import time
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from .models import MobilePushDevice


def configured(platform):
    if platform=='ios':
        return bool((settings.MOBILE_APNS_KEY_FILE or settings.MOBILE_APNS_PRIVATE_KEY) and settings.MOBILE_APNS_KEY_ID and settings.MOBILE_APNS_TEAM_ID)
    return bool(platform=='android' and (settings.MOBILE_FCM_CREDENTIALS_FILE or settings.MOBILE_FCM_CREDENTIALS_JSON))


def send(notification):
    """Called only by the trusted operator command; raises on provider failure, never claims delivery."""
    import httpx
    outcomes=[]
    devices=MobilePushDevice.objects.filter(user=notification.user,enabled=True,session__revoked=False,session__expires_at__gt=timezone.now())
    for device in devices:
        if not configured(device.platform):continue
        if device.platform=='ios':
            import jwt
            key=settings.MOBILE_APNS_PRIVATE_KEY or Path(settings.MOBILE_APNS_KEY_FILE).read_text()
            token=jwt.encode({'iss':settings.MOBILE_APNS_TEAM_ID,'iat':int(time.time())},key,algorithm='ES256',headers={'kid':settings.MOBILE_APNS_KEY_ID})
            host='api.sandbox.push.apple.com' if settings.MOBILE_APNS_SANDBOX else 'api.push.apple.com'
            with httpx.Client(http2=True,timeout=15) as client:
                response=client.post(f'https://{host}/3/device/{device.token}',headers={'authorization':'bearer '+token,'apns-topic':settings.MOBILE_APP_ID,'apns-push-type':'alert'},json={'aps':{'alert':{'title':'TK-ZONE','body':'You have an update. Open your private inbox.'},'sound':'default'}})
        else:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request
            info=json.loads(settings.MOBILE_FCM_CREDENTIALS_JSON) if settings.MOBILE_FCM_CREDENTIALS_JSON else json.loads(Path(settings.MOBILE_FCM_CREDENTIALS_FILE).read_text())
            credentials=service_account.Credentials.from_service_account_info(info,scopes=['https://www.googleapis.com/auth/firebase.messaging'])
            credentials.refresh(Request())
            response=httpx.post(f'https://fcm.googleapis.com/v1/projects/{credentials.project_id}/messages:send',headers={'Authorization':'Bearer '+credentials.token},json={'message':{'token':device.token,'notification':{'title':'TK-ZONE','body':'You have an update. Open your private inbox.'}}},timeout=15)
        # Never expose a provider response containing a device token or credential.
        if response.status_code not in (200,201):raise RuntimeError(f'Push provider rejected the request ({response.status_code}).')
        outcomes.append(device.pk)
    return outcomes
