"""Correct the project contributor name without changing photo consent or access."""
from django.db import migrations, transaction

OLD = 'Sophia Gateneo'
NEW = 'Sophia Gatenyo'


def correct_name(apps, schema_editor):
    alias = schema_editor.connection.alias
    School = apps.get_model('community', 'School')
    Photo = apps.get_model('community', 'TeamPhoto')
    User = apps.get_model('auth', 'User')
    Membership = apps.get_model('community', 'Membership')
    schools = School.objects.using(alias).filter(name__iexact='Unicorn School').values_list('pk', flat=True)
    with transaction.atomic(using=alias):
        for photo in Photo.objects.using(alias).filter(school_id__in=schools):
            changed = []
            for field in ('name', 'caption', 'description'):
                value = getattr(photo, field)
                corrected = value.replace(OLD, NEW)
                if value != corrected:
                    setattr(photo, field, corrected)
                    changed.append(field)
            if changed:
                photo.save(using=alias, update_fields=changed)
        ids = Membership.objects.using(alias).filter(school_id__in=schools).values_list('user_id', flat=True)
        User.objects.using(alias).filter(pk__in=ids, first_name='Sophia', last_name='Gateneo').update(last_name='Gatenyo')
        User.objects.using(alias).filter(pk__in=ids, first_name=OLD).update(first_name=NEW)


class Migration(migrations.Migration):
    dependencies = [('community', '0010_publish_updated_student_portraits')]
    operations = [migrations.RunPython(correct_name, migrations.RunPython.noop)]
