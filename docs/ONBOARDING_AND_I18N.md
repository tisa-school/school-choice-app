# Discovery onboarding, recommendations and language improvements

Implemented on `feature/onboarding-i18n`. Existing website branding, routes, account roles, saved records and mobile work remain intact. No live deployment or production database migration has been performed.

## Working features

- Optional seven-question modal on first entry to Home, activities/events, school discovery, Finder or Saved. One question at a time, progress, Back/Continue/Skip, multi-select interests/types, keyboard controls, responsive cards and reduced-motion support.
- No name, email, date of birth, precise address or GPS is requested. City/region is optional and capped at 100 characters. All values are validated server-side. A self-described student/parent/teacher preference never grants a school membership or staff privileges.
- Guest answers persist in the server-side Django session with a one-year session cookie. Personalized guest/account responses use private, no-store caching. Signed-in answers persist in `DiscoveryPreference`; completed guest answers are imported on that user's next visit after login unless that account already has preferences. Language remains in the existing `InterfacePreference`/language cookie system. Discovery preferences can be edited from the unified sidebar or Profile & Settings.
- Recommended for You uses existing, school-scoped published listings. It excludes cancelled, archived, past and full listings, uses an available future recurring session, honours the free-only preference using the actual numeric price, ranks confirmed interest/area/event-type/attendance matches, and explains those actual matches. It never fabricates an event, price, safeguarding check or booking. All events remain available through Explore all events.
- Optional `Event.city`, `event_kind` and `attendance_mode` fields are exposed in the existing event creator. Old records are not guessed/backfilled: a missing attendance/type/area is not claimed as a preference match. Interest matching groups Technology with Coding, Education with School Life/Educational Visits and Art with existing arts categories.
- Authored event `translations` can contain title/description values by supported locale. Existing authorised event editing validates their shape and length. Event titles/descriptions across templates use the requested translation when supplied, with escaped original text as fallback. No private text is sent to an external translation or AI service.

## Language work and explicit remaining gap

The existing shared system supports English, European Portuguese, Chinese, Hindi, Spanish, Arabic, French, Bengali, Russian, Urdu and Turkish. This change keeps those languages and uses the same central catalogues, not a second translation framework.

All new questionnaire questions, options, settings, recommendation reasons, save/error messages and controls have catalogue values for all eleven languages. Selected public headings and navigation translations were repaired. 413 existing literal template nodes were converted to explicit catalogue lookups. Self-closing form attributes, image alt/title attributes, language-switch auto-submit, POST-vs-URL language persistence and localized currency/progress numbers were improved. URL `?lang=` and aliases (such as `pt`) take precedence, existing filter parameters are preserved, RTL remains enabled for Arabic/Urdu, and the language persists between pages and sessions.

**The entire legacy website is not yet fully translated.** Many pre-existing catalogue values outside the new flow still repeat English. Structural parity/non-empty values do not establish translation quality. The read-only whole-template catalogue audit reports candidate keys rather than silently filling them with English or declaring them translated. Some identical words are valid loanwords/brand names; the remaining ones need real translations and context review. Authored event text without a supplied translation also stays original, as required to avoid invented content.

At the final audit, English has no review candidates; European Portuguese's five are `LISBOA · TK-ZONE`, `Menu`, `Online`, `TK-ZONE` and `TK-Zone` (legitimate shared labels/branding). Other catalogue counts are Chinese 312, Hindi 312, Spanish 314, Arabic 312, French 315, Bengali 312, Russian 312, Urdu 313, Turkish 313. These are **candidate explicit-template strings identical to English**, not a count of all untranslated dynamic content. Forms/notifications/JavaScript and authored content also require contextual review before claiming complete whole-site localization. This is a known unfinished portion of the user's global-language requirement.

Commands:

```bash
python manage.py audit_translations
# Adds a failure when any identical-to-English candidates remain:
python manage.py audit_translations --strict-review
```

The normal audit verifies catalogue key parity, literal template key existence, non-empty values and interpolation-token consistency. The strict review is expected to report outstanding legacy candidates; it must not be presented as passed. Content authors must provide any missing authored event translations; UI catalogues must not be used to rewrite people's names or private profile content.

## Validation

Executed successfully:

- Django system checks and migration drift check.
- Full backend suite: **334 tests passed**, including 15 preference/i18n tests. These exercise privacy/scope, no role escalation, CSRF, invalid inputs, guest/account persistence, actual save receipts, prices/availability, authored translation escaping and page rendering across all 11 locales.
- Three Chromium tests passed: the full questionnaire/Back/Skip, saving an activity, settings edits, language switching/persistence, failure feedback, and **completing the entire questionnaire separately in each of the 11 languages**. Final focused browser reruns cover styling/save feedback and failure recovery. If saving Skip fails, the modal still closes with an explicit warning; the next visit asks again rather than claiming persistence.
- JavaScript syntax checks for onboarding, app and shared i18n scripts.
- The catalogue structural audit passed for all 11 languages. It does not certify the unfinished legacy translation review above.
- Isolated Vercel Preview build script passed with synthetic settings and no production database connection/migration.

Screenshots from the real browser implementation, using fictional test fixtures: `artifacts/onboarding/welcome-mobile.png`, `interests-mobile.png`, and `recommendations-desktop.png`.

## Review and deployment

Review the feature branch and run:

```bash
python manage.py migrate --plan
python manage.py migrate                 # only against your approved target database
python manage.py collectstatic --noinput
python manage.py check
python manage.py test community --noinput
python manage.py test community.browser_preferences --noinput
python manage.py audit_translations
```

Migration `0023_discovery_preferences_and_event_locales` is additive and follows the existing mobile migration. The existing Vercel script migrates production only; an isolated Preview database needs its approved migration step before these views can query the new preferences table. Do not point unreviewed preview migrations at production. Set `DISCOVERY_ONBOARDING_ENABLED=0` to temporarily disable automatic modal presentation; Settings remains available and recommendations are still based on saved choices. No main-branch merge is performed by this work.
