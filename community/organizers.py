"""Organizer permissions and lifecycle operations. No public attendee directory."""
from django.db import transaction
from django.utils import timezone
from .models import Event, Membership, OrganizerApplication, Participation, TicketHistory, ParticipationHistory, Notification
from .services import staff_notify

def can_manage(user, member, event):
    return bool(user.is_superuser or (member and member.verified and member.school_id==event.school_id and (member.role=='staff' or (member.role=='organizer' and event.created_by_id==user.pk))))

@transaction.atomic
def review_application(user,member,pk,status,note=''):
    if not member or member.role!='staff' or not member.verified: raise PermissionError()
    application=OrganizerApplication.objects.select_for_update().get(pk=pk,school=member.school)
    if status not in ['approved','declined'] or application.status!='pending': raise ValueError('This application is not awaiting a valid decision.')
    if status=='approved':
        # Serialize with other approvals involving this same account.
        from django.contrib.auth.models import User
        User.objects.select_for_update().get(pk=application.user_id)
        existing=Membership.objects.select_for_update().filter(user=application.user).first()
        if existing and (existing.school_id!=member.school_id or existing.role in ['student','staff']): raise ValueError('This account has an incompatible school role. A trusted administrator must review it.')
        Membership.objects.update_or_create(user=application.user,defaults={'school':member.school,'role':'organizer','verified':True})
    application.status=status;application.reviewed_by=user;application.reviewed_at=timezone.now();application.decision_note=note[:500];application.save()
    Notification.objects.create(user=application.user,school=member.school,kind='organizer',title='Organizer application '+status,message=note[:500] or 'Your organizer application has been reviewed.',link='/organizer/')
    return application

@transaction.atomic
def cancel_listing(user,member,pk,note):
    event=Event.objects.select_for_update().get(pk=pk)
    if not can_manage(user,member,event): raise PermissionError()
    if event.is_cancelled: raise ValueError('This listing is already cancelled.')
    if not note.strip(): raise ValueError('Add a cancellation reason so families understand what changed.')
    event.is_cancelled=True;event.cancellation_note=note.strip()[:500];event.save(update_fields=['is_cancelled','cancellation_note','updated_at'])
    event.sessions.update(is_cancelled=True)
    recipients=set()
    for booking in event.family_bookings.select_for_update().select_related('parent').filter(status__in=['pending','confirmed']):
        booking.status='cancelled';booking.save();recipients.add(booking.parent.user_id)
    for ticket in event.requests.select_for_update().filter(status__in=['requested','under_review','approved']):
        previous=ticket.status;ticket.status='cancelled';ticket.save()
        TicketHistory.objects.create(ticket=ticket,previous_status=previous,new_status='cancelled',changed_by=user)
        recipients.add(ticket.student_id)
    for item in event.participations.select_for_update().select_related('child__parent').exclude(status__in=['cancelled','declined']):
        previous=item.status;item.status='cancelled';item.save()
        ParticipationHistory.objects.create(participation=item,previous_status=previous,new_status='cancelled',changed_by=user)
        recipients.add(item.child.parent.user_id)
    for recipient in recipients:
        Notification.objects.create(user_id=recipient,school=event.school,kind='event',title='A listing you requested was cancelled',message=event.cancellation_note,link='/family/' if (event.participations.filter(child__parent__user_id=recipient).exists() or event.family_bookings.filter(parent__user_id=recipient).exists()) else '/tickets/')
    return event
