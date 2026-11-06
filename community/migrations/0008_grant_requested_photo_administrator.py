"""Owner-authorized, one-time production grant for an existing registered account.

This is not a login allowlist: it never creates an account, changes a password,
activates an account, or runs when somebody signs up or signs in.
"""
import os
from django.contrib.auth.hashers import is_password_usable, make_password
from django.db import migrations, transaction

TARGET_EMAIL = 'students.steam2@tisaschool.nl'
SCHOOL_NAME = 'Unicorn School'


def grant_requested_access(apps, schema_editor):
    # Preview/CI databases must never receive a production account grant.
    if os.environ.get('VERCEL_ENV') != 'production':
        return
    alias = schema_editor.connection.alias
    User = apps.get_model('auth', 'User')
    School = apps.get_model('community', 'School')
    Membership = apps.get_model('community', 'Membership')
    with transaction.atomic(using=alias):
        users = list(User.objects.using(alias).select_for_update().filter(email__iexact=TARGET_EMAIL))
        if len(users) != 1:
            raise RuntimeError('Photo administrator setup requires exactly one existing registered account for the requested email. No account was created or granted access.')
        user = users[0]
        if not user.is_active or not user.password or not is_password_usable(user.password):
            raise RuntimeError('Photo administrator setup requires an active account with an existing usable password. No authentication settings were changed.')
        member = Membership.objects.using(alias).select_for_update().filter(user_id=user.pk).first()
        if member:
            school = School.objects.using(alias).get(pk=member.school_id)
            if school.name.casefold() != SCHOOL_NAME.casefold():
                raise RuntimeError('The requested account already belongs to another school. Trusted membership review is required; existing access was not changed.')
        else:
            schools = list(School.objects.using(alias).select_for_update().filter(name__iexact=SCHOOL_NAME))
            if len(schools) > 1:
                raise RuntimeError('Multiple matching schools exist. Trusted school review is required before granting access.')
            school = schools[0] if schools else School.objects.using(alias).create(
                name=SCHOOL_NAME,
                time_zone='Europe/Lisbon',
                # No working invitation code is created by this photo-admin setup.
                invite_code_hash=make_password(None),
            )
        Membership.objects.using(alias).update_or_create(
            user_id=user.pk,
            defaults={'school_id':school.pk, 'role':'staff', 'verified':True},
        )
        if not Membership.objects.using(alias).filter(user_id=user.pk,school_id=school.pk,role='staff',verified=True).exists():
            raise RuntimeError('Photo administrator setup did not pass its permission check.')


class Migration(migrations.Migration):
    atomic = True
    dependencies = [('community', '0007_activitysession_child_capacity_event_child_capacity_and_more')]
    operations = [migrations.RunPython(grant_requested_access, migrations.RunPython.noop)]
