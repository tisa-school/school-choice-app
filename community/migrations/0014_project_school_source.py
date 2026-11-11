"""Publish only the name/city/relationship explicitly supplied by the project team."""
from datetime import date
from django.db import migrations

def add_project_school(apps,schema_editor):
    Profile=apps.get_model('community','SchoolProfile');School=apps.get_model('community','School')
    alias=schema_editor.connection.alias
    matches=list(School.objects.using(alias).filter(name__iexact='Unicorn School').values_list('pk',flat=True))
    Profile.objects.using(alias).get_or_create(slug='unicorn-school-lisbon',defaults={'name':'Unicorn School','city':'Lisbon','summary':'Unicorn School is the Lisbon school behind the student-led TK-ZONE project.','source_name':'School-provided TK-ZONE project presentation; no independent school-website check','last_checked':date(2026,11,10),'is_published':True,'school_id':matches[0] if len(matches)==1 else None})

class Migration(migrations.Migration):
    dependencies=[('community','0013_school_directory')]
    operations=[migrations.RunPython(add_project_school,migrations.RunPython.noop)]
