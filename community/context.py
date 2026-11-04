from .models import Membership, Notification
from django.utils import timezone
from zoneinfo import ZoneInfo

def shell(request):
    member=Membership.objects.select_related('school').filter(user=request.user).first() if request.user.is_authenticated else None
    timezone.activate(ZoneInfo(member.school.time_zone) if member else ZoneInfo('Europe/Lisbon'))
    return {'member':member,'is_staff_member':bool(member and member.role=='staff' and member.verified),'unread_count':Notification.objects.filter(user=request.user,is_read=False).count() if member else 0}
