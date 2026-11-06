from datetime import timedelta
from django.core.management.base import BaseCommand,CommandError
from django.utils import timezone
from community.models import Feedback
class Command(BaseCommand):
    help='Review feedback retention (90 days by default). Dry run unless --apply is explicitly supplied.'
    def add_arguments(self,parser):
        parser.add_argument('--days',type=int,default=90)
        parser.add_argument('--apply',action='store_true')
    def handle(self,*args,**options):
        if options['days']<1: raise CommandError('Use at least one retention day.')
        rows=Feedback.objects.filter(created_at__lt=timezone.now()-timedelta(days=options['days']))
        count=rows.count()
        if options['apply']: rows.delete()
        self.stdout.write(f'{count} old feedback records '+('deleted.' if options['apply'] else 'would be deleted. Dry run; no records changed.'))
