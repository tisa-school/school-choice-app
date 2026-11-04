import hashlib
from django.conf import settings
import ipaddress
from datetime import timedelta
from django.http import HttpResponse
from django.utils import timezone
from .models import RateAttempt
class RateLimitMiddleware:
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        if request.method=='POST':
            # Vercel sets this edge header. Outside Vercel, never trust forwarded addresses.
            address=request.META.get('REMOTE_ADDR','')
            if settings.ON_VERCEL:
                try: address=str(ipaddress.ip_address(request.META.get('HTTP_X_VERCEL_FORWARDED_FOR',address).split(',')[0].strip()))
                except ValueError: pass
            actor='user:'+str(request.user.pk) if request.user.is_authenticated else 'address:'+address
            key=hashlib.sha256((actor+request.path).encode()).hexdigest()
            cutoff=timezone.now()-timedelta(minutes=10)
            if RateAttempt.objects.filter(key=key,created_at__gte=cutoff).count()>=30:
                response=HttpResponse('Please wait a few minutes before trying again.',status=429)
                response['Retry-After']='600'
                return response
            RateAttempt.objects.create(key=key)
            RateAttempt.objects.filter(created_at__lt=cutoff).delete()
        return self.get_response(request)
