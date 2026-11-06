"""Publish replacement student portraits explicitly approved by the website owner.

The owner confirmed permission for the supplied portraits and explicitly approved
public visibility, including the students, after requesting the private setting.
Future uploads/replacements retain their existing private defaults.
"""
import os
from django.db import migrations, transaction

NAMES = ('Sophia Gateneo', 'Rosie Markovska', 'Daniel Vinnikov')


def publish_updated_student_portraits(apps, schema_editor):
    if os.environ.get('VERCEL_ENV') != 'production':
        return
    alias = schema_editor.connection.alias
    School = apps.get_model('community', 'School')
    TeamPhoto = apps.get_model('community', 'TeamPhoto')
    with transaction.atomic(using=alias):
        schools = list(School.objects.using(alias).select_for_update().filter(name__iexact='Unicorn School'))
        if len(schools) != 1:
            raise RuntimeError('Approved About portrait publication requires one unambiguous Unicorn School.')
        photos = TeamPhoto.objects.using(alias).filter(school_id=schools[0].pk, name__in=NAMES, is_group=False).order_by('-created_at', '-pk')
        selected = {}
        for photo in photos:
            selected.setdefault(photo.name, photo.pk)
        if len(selected) != len(NAMES):
            raise RuntimeError('All three approved student portraits must exist before publishing replacements.')
        TeamPhoto.objects.using(alias).filter(pk__in=selected.values()).update(
            visibility='public', sharing_permission=True, guardian_consent=True,
        )
        if TeamPhoto.objects.using(alias).filter(pk__in=selected.values(), visibility='public', sharing_permission=True, guardian_consent=True).count() != len(selected):
            raise RuntimeError('Approved portrait publication did not pass its visibility check.')


class Migration(migrations.Migration):
    dependencies = [('community', '0009_publish_approved_about_portraits')]
    operations = [migrations.RunPython(publish_updated_student_portraits, migrations.RunPython.noop)]
