from django.core.management.base import BaseCommand,CommandError
from django.contrib.auth.models import User
from django.db import transaction
from community.models import School,Membership
class Command(BaseCommand):
    help='Trusted operator only: verify an existing account as staff in a real school.'
    def add_arguments(self,parser):
        parser.add_argument('--email',required=True)
        parser.add_argument('--school-id',required=True,type=int)
    @transaction.atomic
    def handle(self,*args,**options):
        users=list(User.objects.filter(email__iexact=options['email'])[:2])
        if len(users)!=1:raise CommandError('Exactly one existing account must match this email; review ambiguous identities first.')
        user=users[0]
        if not user.is_active or not user.has_usable_password():raise CommandError('An active existing account with a usable password is required.')
        school=School.objects.filter(pk=options['school_id']).first()
        if not user or not school: raise CommandError('Existing registered account and school are required.')
        member=Membership.objects.filter(user=user).first()
        if member and member.school_id!=school.pk: raise CommandError('Account belongs to another school; review membership in trusted admin first.')
        if not member: member=Membership(user=user,school=school)
        member.role='staff';member.verified=True;member.save()
        self.stdout.write(self.style.SUCCESS('Staff membership verified.'))
