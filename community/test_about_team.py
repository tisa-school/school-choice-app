import json
from django.conf import settings
from django.test import TestCase, Client
from .localization import ACTIVE_LOCALES, catalog


class AboutTeamTests(TestCase):
    def test_verified_roster_in_every_language(self):
        expected = {
            'students': ['Sophia Gateneo', 'Rosie Markovska', 'Daniel Vinnikov'],
            'lead': ['Zehra Yilmaz'],
            'coordination': ['Lucas Alves'],
            'leadership': ['Artem Tolmachev', 'Karina Medvedeva', 'Anna Kupavtseva'],
        }
        project = json.loads((settings.BASE_DIR / 'content/project.json').read_text())
        self.assertEqual(project['school'], 'Unicorn School')
        for group, names in expected.items():
            self.assertEqual([p['public_name'] for p in project['contributors'] if p['group'] == group], names)
        for locale in ACTIVE_LOCALES:
            with self.subTest(locale=locale):
                response = Client().get('/about/', {'lang': locale})
                self.assertEqual(response.status_code, 200)
                for names in expected.values():
                    for name in names:
                        self.assertContains(response, name.split()[0] if name in expected['students'] else name, count=1)
                self.assertContains(response, 'Unicorn School')
                self.assertNotContains(response, 'Theodore International')
                self.assertNotContains(response, '<p class="eyebrow">TISA')
                self.assertNotContains(response, '<img')
                for role in ['Student Contributors', 'Project Lead', 'STEAM Mentor', 'Project Coordination', 'School Leadership']:
                    self.assertContains(response, catalog(locale)[role])
