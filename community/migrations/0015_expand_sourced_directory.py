"""Official-site snapshot checked 11 November 2026; no estimated fees or vacancies."""
from django.db import migrations

PROFILES = [{'slug': 'carlucci-american-international-school-lisbon',
  'name': 'Carlucci American International School of Lisbon',
  'city': 'Sintra',
  'school_type': 'international',
  'stages': 'early,primary,lower_secondary,upper_secondary',
  'summary': 'International school with early childhood, elementary, middle and high school divisions. '
             'Consult the school for grade-specific admissions.',
  'website': 'https://www.caislisbon.org/',
  'source_name': 'Carlucci American International School of Lisbon — official school website',
  'last_checked': '2026-11-11',
  'is_published': True,
  'source_url': 'https://www.caislisbon.org/'},
 {'slug': 'british-school-lisbon',
  'name': 'The British School of Lisbon',
  'city': 'Lisbon',
  'school_type': 'international',
  'stages': 'early,primary,lower_secondary,upper_secondary',
  'curriculum': 'British education',
  'summary': 'British school with primary and secondary campuses in Lisbon, with music, sport and arts '
             'alongside academic subjects.',
  'address': 'Primary: Rua São Paulo 89, Lisbon 1200-427; Secondary: Rua de Alcolena 10, Lisbon 1400-004',
  'website': 'https://www.britishschool.pt/',
  'source_name': 'The British School of Lisbon — official school website',
  'last_checked': '2026-11-11',
  'is_published': True,
  'source_url': 'https://www.britishschool.pt/'},
 {'slug': 'st-julians-school',
  'name': 'St. Julian’s School',
  'city': 'Carcavelos',
  'school_type': 'international',
  'min_age': 3,
  'max_age': 18,
  'stages': 'early,primary,lower_secondary,upper_secondary',
  'curriculum': 'British international; bilingual pathway for ages 6–14',
  'summary': 'British international school in Carcavelos for ages 3–18, with a bilingual pathway for ages '
             '6–14.',
  'website': 'https://www.stjulians.com/',
  'source_name': 'St. Julian’s School — official school website',
  'last_checked': '2026-11-11',
  'is_published': True,
  'source_url': 'https://www.stjulians.com/'},
 {'slug': 'tasis-portugal',
  'name': 'TASIS Portugal',
  'city': 'Sintra',
  'school_type': 'international',
  'stages': 'early,primary,lower_secondary,upper_secondary',
  'curriculum': 'Core Knowledge; Singapore Math; Cambridge IGCSE; IB Diploma',
  'summary': 'International school offering pre-kindergarten through high school, with Core Knowledge, '
             'Singapore Math, Cambridge IGCSE and IB pathways.',
  'website': 'https://www.tasisportugal.org/',
  'source_name': 'TASIS Portugal — official school website',
  'last_checked': '2026-11-11',
  'is_published': True,
  'source_url': 'https://www.tasisportugal.org/'},
 {'slug': 'united-lisbon-international-school',
  'name': 'United Lisbon International School',
  'city': 'Lisbon',
  'school_type': 'international',
  'min_age': 3,
  'max_age': 18,
  'languages': 'en',
  'stages': 'early,primary,lower_secondary,upper_secondary',
  'curriculum': 'IEYC; International Primary Curriculum; International Middle Years Curriculum; IB Diploma',
  'address': 'Avenida Marechal Gomes da Costa 9, 1800-255 Lisbon',
  'summary': 'English-medium international education for ages 3–18 in Lisbon, with early years, primary, '
             'middle school and IB Diploma pathways.',
  'website': 'https://www.unitedlisbon.school/',
  'source_name': 'United Lisbon International School — official school website',
  'last_checked': '2026-11-11',
  'is_published': True,
  'source_url': 'https://www.unitedlisbon.school/'},
 {'slug': 'colegio-moderno',
  'name': 'Colégio Moderno',
  'city': 'Lisbon',
  'school_type': 'private',
  'stages': 'early,primary,lower_secondary,upper_secondary',
  'summary': 'Secular private school whose educational project covers pre-school, basic and secondary '
             'education, with humanist values and active learning.',
  'teaching_approach': 'The educational project emphasises autonomy, citizenship, creativity and respect for '
                       'different learning rhythms.',
  'website': 'https://colegiomoderno.pt/',
  'source_url': 'https://colegiomoderno.pt/colegio-moderno/projeto-educativo/',
  'source_name': 'Colégio Moderno — official school website',
  'last_checked': '2026-11-11',
  'is_published': True}]


def add_profiles(apps, schema_editor):
    Profile = apps.get_model('community', 'SchoolProfile')
    for record in PROFILES:
        values = dict(record)
        slug = values.pop('slug')
        Profile.objects.using(schema_editor.connection.alias).get_or_create(slug=slug, defaults=values)


class Migration(migrations.Migration):
    dependencies = [('community', '0014_project_school_source')]
    operations = [migrations.RunPython(add_profiles, migrations.RunPython.noop)]
