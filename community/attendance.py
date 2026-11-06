"""Shared confirmed seat accounting. Call under the event lock before allocating seats."""
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from .models import Event, ActivitySession, FamilyBooking, ParentAccount, Notification
from .discovery import visible_events, membership
from .organizers import can_manage


def attendance(target):
    session=isinstance(target, ActivitySession)
    legacy_children=target.participations.filter(status='confirmed', **({} if session else {'session__isnull':True})).count()
    if not session: legacy_children+=target.requests.filter(status='approved').count()
    groups=target.family_bookings.filter(status='confirmed', **({} if session else {'session__isnull':True})).aggregate(adults=Sum('adults'),children=Sum('children'))
    adults=groups['adults'] or 0
    children=legacy_children+(groups['children'] or 0)
    total=adults+children
    return dict(adults=adults,children=children,total=total,remaining_total=None if target.capacity is None else max(0,target.capacity-total),remaining_children=None if target.child_capacity is None else max(0,target.child_capacity-children))


def check_space(target, adults, children):
    counts=attendance(target)
    if (counts['remaining_total'] is not None and adults+children>counts['remaining_total']) or (counts['remaining_children'] is not None and children>counts['remaining_children']):
        raise ValueError('There are not enough total or child spaces for this family.')


@transaction.atomic
def book_family(user,event_id,adults,children,session_id=None):
    if type(adults) is not int or type(children) is not int or min(adults,children)<0 or max(adults,children)>1000 or adults+children==0:
        raise ValueError('Enter a valid number of adults and children, with at least one attendee.')
    parent=ParentAccount.objects.get(user=user)
    event=visible_events(user).select_for_update().filter(pk=event_id).first()
    if not event:raise ValueError('This listing is no longer available.')
    target=event
    session=None
    if event.listing_type=='activity':
        session=ActivitySession.objects.select_for_update().filter(pk=session_id,activity=event,is_cancelled=False).first()
        if not session:raise ValueError('This session is no longer available.')
        target=session
    elif session_id: raise ValueError('Choose a valid event or activity session.')
    if event.is_cancelled or target.start_at<=timezone.now() or not event.ticket_requests_enabled or (event.requests_close_at and event.requests_close_at<=timezone.now()):
        raise ValueError('This listing is no longer accepting registrations.')
    if FamilyBooking.objects.filter(parent=parent,event=event,session=session,status__in=['pending','confirmed']).exists():
        raise ValueError('You already have an active family registration for this event or session.')
    check_space(target,adults,children)
    return FamilyBooking.objects.create(parent=parent,event=event,session=session,adults=adults,children=children)


@transaction.atomic
def decide_booking(user,pk,action):
    event_id=FamilyBooking.objects.values_list('event_id',flat=True).get(pk=pk)
    event=Event.objects.select_for_update().get(pk=event_id)
    item=FamilyBooking.objects.select_for_update().select_related('parent__user').get(pk=pk,event=event)
    manager=can_manage(user,membership(user),event)
    if action=='cancel':
        if user.pk!=item.parent.user_id and not manager: raise PermissionError()
        if item.status not in ['pending','confirmed']: raise ValueError('This registration is already closed.')
        item.status='cancelled'
    else:
        if not manager: raise PermissionError()
        if action not in ['confirm','decline'] or item.status!='pending': raise ValueError('This registration is not awaiting a decision.')
        if action=='confirm':
            target=ActivitySession.objects.select_for_update().get(pk=item.session_id,activity=event) if item.session_id else event
            if event.is_cancelled or getattr(target,'is_cancelled',False) or event.status!='published' or target.start_at<=timezone.now(): raise ValueError('This listing is no longer available.')
            if not visible_events(item.parent.user).filter(pk=event.pk).exists(): raise ValueError('This family no longer has access to this event.')
            check_space(target,item.adults,item.children)
        item.status='confirmed' if action=='confirm' else 'declined'
    item.reviewed_by=user;item.save()
    Notification.objects.create(user=item.parent.user,school=event.school,kind='family',title='Family registration updated',message=item.get_status_display(),link='/family/')
    return item


def confirmed_total(events):
    """Dashboard totals count people, including all activity sessions, rather than request rows."""
    from .models import TicketRequest,Participation
    groups=FamilyBooking.objects.filter(event__in=events,status='confirmed').aggregate(adults=Sum('adults'),children=Sum('children'))
    return TicketRequest.objects.filter(event__in=events,status='approved').count()+Participation.objects.filter(event__in=events,status='confirmed').count()+(groups['adults'] or 0)+(groups['children'] or 0)
