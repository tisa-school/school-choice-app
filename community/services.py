from django.db import transaction
from django.utils import timezone
from .models import Event, TicketRequest, TicketHistory, Notification, Membership, Announcement

def staff_notify(school,title,message,link):
    Notification.objects.bulk_create([Notification(user=m.user,school=school,kind='ticket',title=title,message=message,link=link) for m in Membership.objects.filter(school=school,role='staff',verified=True)])
def notify_school(announcement):
    Notification.objects.bulk_create([Notification(user=m.user,school=announcement.school,kind='announcement',title=announcement.title,message='A new school announcement is ready to read.',link='/announcements/') for m in Membership.objects.filter(school=announcement.school)])
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
    if member.role!='staff' or not member.verified: raise PermissionError()
    # SQLite IMMEDIATE transactions serialize all writers; event lock also supports row-locking backends.
    ticket=TicketRequest.objects.select_for_update().select_related('event').get(pk=ticket_id,event__school=member.school)
    event=Event.objects.select_for_update().get(pk=ticket.event_id)
    if status not in ['under_review','approved','declined']: raise ValueError('Invalid decision.')
    if ticket.status not in ['requested','under_review']: raise ValueError('This request has already been decided.')
    if status=='approved' and (event.remaining==0 or event.status!='published' or event.start_at<=timezone.now()): raise ValueError('Approval unavailable: the event is full or unpublished.')
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
