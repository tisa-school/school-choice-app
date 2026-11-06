from django.db import transaction
from django.utils import timezone
from .models import Event, TicketRequest, TicketHistory, Notification, Membership, Announcement

def staff_notify(school,title,message,link):
    Notification.objects.bulk_create([Notification(user=m.user,school=school,kind='ticket',title=title,message=message,link=link) for m in Membership.objects.filter(school=school,role='staff',verified=True)])
def notify_school(announcement):
    Notification.objects.bulk_create([Notification(user=m.user,school=announcement.school,kind='announcement',title=announcement.title,message='A new school announcement is ready to read.',link='/announcements/') for m in Membership.objects.filter(school=announcement.school).exclude(role='organizer')])
@transaction.atomic
def publish_due(school=None):
    qs=Announcement.objects.select_for_update().filter(status='scheduled',scheduled_for__lte=timezone.now())
    if school: qs=qs.filter(school=school)
    for item in qs:
        item.status='published';item.published_at=timezone.now();item.save()
        notify_school(item)
@transaction.atomic
def request_ticket(user,member,event_id):
    event=Event.objects.select_for_update().get(pk=event_id,school=member.school,status='published')
    if member.role!='student': raise ValueError('Ticket requests are available to students.')
    if not event.eligible: raise ValueError('This event is no longer accepting ticket requests.')
    if TicketRequest.objects.filter(event=event,student=user,status__in=['requested','under_review','approved']).exists(): raise ValueError('You already have an active request for this event.')
    ticket=TicketRequest.objects.create(event=event,student=user)
    TicketHistory.objects.create(ticket=ticket,new_status='requested',changed_by=user)
    Notification.objects.create(user=user,school=member.school,kind='ticket',title='Request received ✦',message=f'Your request for {event.title} is awaiting staff approval.',link='/tickets/')
    staff_notify(member.school,'New ticket request',f'A student requested a ticket for {event.title}.','/staff/requests/')
    return ticket
@transaction.atomic
def decide(user,member,ticket_id,status,note=''):
    if member.role not in ['staff','organizer'] or not member.verified: raise PermissionError()
    # SQLite IMMEDIATE transactions serialize all writers; event lock also supports row-locking backends.
    event_id=TicketRequest.objects.values_list('event_id',flat=True).get(pk=ticket_id,event__school=member.school)
    event=Event.objects.select_for_update().get(pk=event_id,school=member.school)
    ticket=TicketRequest.objects.select_for_update().get(pk=ticket_id,event=event)
    if member.role=='organizer' and event.created_by_id!=user.pk: raise PermissionError()
    if status not in ['under_review','approved','declined']: raise ValueError('Invalid decision.')
    if ticket.status not in ['requested','under_review']: raise ValueError('This request has already been decided.')
    if status=='approved' and (event.remaining==0 or event.status!='published' or event.is_cancelled or event.start_at<=timezone.now()): raise ValueError('Approval unavailable: the event is full or unpublished.')
    if status=='approved':
        from .attendance import check_space
        check_space(event,0,1)
    old=ticket.status
    ticket.status=status;ticket.reviewed_by=user;ticket.reviewed_at=timezone.now();ticket.decision_note=note[:500];ticket.save()
    TicketHistory.objects.create(ticket=ticket,previous_status=old,new_status=status,changed_by=user)
    Notification.objects.create(user=ticket.student,school=member.school,kind='ticket',title=f'Ticket {ticket.get_status_display()}',message=f'{event.title}: {ticket.get_status_display()}. '+note[:500],link='/tickets/')
@transaction.atomic
def cancel(user,member,ticket_id):
    ticket=TicketRequest.objects.select_for_update().get(pk=ticket_id,student=user,event__school=member.school)
    if ticket.status not in ['requested','under_review','approved']: raise ValueError('This request is already closed.')
    old=ticket.status;ticket.status='cancelled';ticket.save()
    TicketHistory.objects.create(ticket=ticket,previous_status=old,new_status='cancelled',changed_by=user)
    staff_notify(member.school,'Ticket cancelled',f'A student cancelled their ticket for {ticket.event.title}.','/staff/requests/')

from .models import ParentAccount, ChildProfile, ActivitySession, Participation, ParticipationHistory
from .discovery import visible_events


def participation_notice(item,title,message):
    Notification.objects.create(user=item.child.parent.user,school=item.event.school,kind='family',title=title,message=message,link='/family/')

def record_participation(item,previous,user):
    ParticipationHistory.objects.create(participation=item,previous_status=previous,new_status=item.status,changed_by=user)

@transaction.atomic
def express_interest(user,event_id,child_id,session_id=None):
    parent=ParentAccount.objects.get(user=user)
    child=ChildProfile.objects.get(pk=child_id,parent=parent)
    event=visible_events(user).select_for_update().get(pk=event_id)
    session=None
    if event.is_cancelled: raise ValueError('This listing has been cancelled.')
    if event.listing_type=='activity':
        session=ActivitySession.objects.select_for_update().get(pk=session_id,activity=event,is_cancelled=False)
        if session.start_at<=timezone.now() or session.remaining==0: raise ValueError('This session is no longer available.')
    elif session_id: raise ValueError('Choose an event or a valid activity session.')
    elif not event.eligible: raise ValueError('This event is not accepting requests.')
    # Age bands must fit inside the organizer's declared bounds; uncertain suitability requires clarification.
    low,high=map(int,child.age_band.split('-'))
    if event.min_age is None or event.max_age is None or low<event.min_age or high>event.max_age:
        raise ValueError('The child’s age band must fit the published age range. Ask the organizer to clarify suitability.')
    if not event.ticket_requests_enabled: raise ValueError('This listing is not accepting requests.')
    if Participation.objects.filter(child=child,event=event,session=session,status__in=['interested','parent_pending','organizer_pending','confirmed']).exists():
        raise ValueError('There is already an active request for this child and session.')
    item=Participation.objects.create(child=child,event=event,session=session)
    record_participation(item,'',user)
    participation_notice(item,'Interest saved ✦','Send this interest for parent review. It does not reserve a place.')
    return item

@transaction.atomic
def parent_decision(user,pk,action,password=''):
    parent=ParentAccount.objects.get(user=user)
    item=Participation.objects.select_for_update().get(pk=pk,child__parent=parent)
    previous=item.status
    if action=='send' and item.status=='interested': item.status='parent_pending'
    elif action in ('approve','decline') and item.status=='parent_pending':
        if not user.check_password(password): raise ValueError('Confirm with your account password to make a parent decision.')
        if not visible_events(user).filter(pk=item.event_id).exists(): raise ValueError('This listing is no longer available.')
        item.status='organizer_pending' if action=='approve' else 'declined'
        item.parent_reviewed_at=timezone.now()
        if action=='approve': staff_notify(item.event.school,'Family participation request','A parent approved a participation request. Organizer confirmation is still required.','/staff/requests/')
    elif action=='cancel' and item.status not in ('declined','cancelled'): item.status='cancelled'
    else: raise ValueError('This action is not available for the current request status.')
    item.save();record_participation(item,previous,user)
    participation_notice(item,item.get_status_display(),'Parent approval and confirmed admission are separate steps.')
    return item

@transaction.atomic
def confirm_participation(user,member,pk,status,note=''):
    if member.role not in ['staff','organizer'] or not member.verified: raise PermissionError()
    # Lock event first, then session, then request: all confirmations share the same lock order.
    event_id=Participation.objects.values_list('event_id',flat=True).get(pk=pk,event__school=member.school)
    event=Event.objects.select_for_update().get(pk=event_id,school=member.school)
    if member.role=='organizer' and event.created_by_id!=user.pk: raise PermissionError()
    item=Participation.objects.select_for_update().select_related('child__parent').get(pk=pk,event=event)
    if item.status!='organizer_pending' or status not in ('confirmed','declined'): raise ValueError('This request is not awaiting organizer confirmation.')
    if status=='confirmed':
        target=ActivitySession.objects.select_for_update().get(pk=item.session_id,activity=event,is_cancelled=False) if item.session_id else event
        low,high=map(int,item.child.age_band.split('-'))
        if event.min_age is None or event.max_age is None or low<event.min_age or high>event.max_age: raise ValueError('The child’s current age band does not fit this listing.')
        if event.status!='published' or event.is_cancelled or target.start_at<=timezone.now() or target.remaining==0: raise ValueError('This listing is full, unpublished, cancelled, or has already started.')
        from .attendance import check_space
        check_space(target,0,1)
        if not visible_events(item.child.parent.user).filter(pk=event.pk).exists(): raise ValueError('The family no longer has access to this listing.')
    previous=item.status;item.status=status;item.reviewed_by=user;item.reviewed_at=timezone.now();item.decision_note=note[:500];item.save()
    record_participation(item,previous,user)
    participation_notice(item,item.get_status_display(),f'{event.title}: {item.get_status_display()}. '+note[:500])
    return item
