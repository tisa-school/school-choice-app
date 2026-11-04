from getpass import getpass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.db import transaction
from community.models import School, Membership
class Command(BaseCommand):
    help='Trusted operator only: create a real school and optionally grant an existing account verified staff membership. Never exposes invite codes.'
    def add_arguments(self,parser):
        parser.add_argument('--name',required=True)
        parser.add_argument('--timezone',default='Europe/Lisbon')
        parser.add_argument('--staff-email')
    @transaction.atomic
    def handle(self,*args,**options):
        try: ZoneInfo(options['timezone'])
        except ZoneInfoNotFoundError: raise CommandError('Use a valid IANA time zone.')
        user=None
        if options['staff_email']:
            user=User.objects.filter(email__iexact=options['staff_email']).first()
            if not user: raise CommandError('Staff must first register an account.')
            if Membership.objects.filter(user=user).exists(): raise CommandError('Account already has school membership; use the trusted Django admin to review changes.')
        code=getpass('Private school invite code (at least 12 characters): ')
        if len(code)<12: raise CommandError('Use at least 12 characters.')
        if getpass('Confirm private school invite code: ')!=code: raise CommandError('Codes did not match.')
        school=School.objects.create(name=options['name'],time_zone=options['timezone'],invite_code_hash=make_password(code))
        if user: Membership.objects.create(user=user,school=school,role='staff',verified=True)
        self.stdout.write(self.style.SUCCESS(f'School {school.pk} configured. Share its invite code privately with students.'))
