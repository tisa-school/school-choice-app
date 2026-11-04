from .models import Membership, Notification, ParentAccount, SaveReceipt
from django.utils import timezone
from zoneinfo import ZoneInfo

def shell(request):
    member=Membership.objects.select_related('school').filter(user=request.user).first() if request.user.is_authenticated else None
    timezone.activate(ZoneInfo(member.school.time_zone) if member else ZoneInfo('Europe/Lisbon'))
    return {'member':member,'is_staff_member':bool(member and member.role=='staff' and member.verified),'save_receipt':SaveReceipt.objects.filter(user=request.user).first() if request.user.is_authenticated else None,'parent_account':ParentAccount.objects.filter(user=request.user).first() if request.user.is_authenticated else None,'unread_count':Notification.objects.filter(user=request.user,is_read=False).count() if request.user.is_authenticated else 0}
