import time
from django.core.management.base import BaseCommand
from community.services import publish_due
class Command(BaseCommand):
    help='Publish due announcements once, or poll every 30 seconds with --watch.'
    def add_arguments(self,parser): parser.add_argument('--watch',action='store_true')
    def handle(self,*args,**kwargs):
        try:
            while True:
                publish_due()
                if not kwargs['watch']: break
                time.sleep(30)
        except KeyboardInterrupt: pass
        self.stdout.write('Scheduled announcement processing stopped.' if kwargs['watch'] else 'Due announcements processed.')
