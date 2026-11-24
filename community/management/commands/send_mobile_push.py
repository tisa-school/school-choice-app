from django.core.management.base import BaseCommand,CommandError
from community.models import Notification
from community.mobile_push import send

class Command(BaseCommand):
    help='Explicitly send a generic push for one existing user notification (not automatic; may incur provider costs).'
    def add_arguments(self,parser):parser.add_argument('--notification-id',type=int,required=True)
    def handle(self,*args,**options):
        try:notification=Notification.objects.get(pk=options['notification_id'])
        except Notification.DoesNotExist:raise CommandError('Notification does not exist.')
        try:accepted=send(notification)
        except Exception:raise CommandError('Push not accepted. Check server credentials and provider logs; tokens are not printed.')
        self.stdout.write(f'Provider accepted {len(accepted)} request(s). This does not prove device receipt. Do not repeat without checking for duplicates.')
