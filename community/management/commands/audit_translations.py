"""Read-only whole-template catalogue coverage audit; never auto-fills English as a translation."""
import json,re
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from community.localization import ACTIVE_LOCALES,catalog
class Command(BaseCommand):
    help='Audit catalogue parity, explicit template keys, format placeholders and possible English fallback text.'
    def add_arguments(self,parser):parser.add_argument('--strict-review',action='store_true')
    def handle(self,*args,**options):
        en=catalog('en');used=set()
        for p in (settings.BASE_DIR/'templates').rglob('*.html'):
            used.update(m[1] for m in re.findall(r'{%\s*ui\s+([\'"])(.*?)\1\s*%}',p.read_text(),re.S))
        bad=False
        for locale in ACTIVE_LOCALES:
            values=catalog(locale);missing=sorted((set(en)|used)-set(values));empty=[k for k,v in values.items() if not str(v).strip()]
            placeholders=[k for k in en if sorted(re.findall(r'\{value\d+\}',en[k]))!=sorted(re.findall(r'\{value\d+\}',values.get(k,'')))]
            review=sorted(k for k in used if locale!='en' and values.get(k)==k and re.search(r'[A-Za-z]{3}',k))
            row={'locale':locale,'missing_keys':missing,'empty_values':empty,'placeholder_mismatches':placeholders,'identical_to_english_needs_review':review}
            self.stdout.write(json.dumps(row,ensure_ascii=False))
            bad=bad or bool(missing or empty or placeholders or options['strict_review'] and review)
        if bad:raise CommandError('Translation audit needs attention; see the reported keys.')
