# Web Summit Release A

Historical release notes. The later [Tech Week final presentation release](TECH_WEEK_FINAL.md) supersedes the demo storage model and team-credit defaults described below.

This release extends the existing Django application and preserves its PostgreSQL, organizer moderation, family, ticketing, saved-data status, and registration-free Tech Week demo workflows. No Gmail integration or new email registration requirement was added.

## Included

- Public About Us with mission, project story, three equal student contributor cards, educator roles, research attribution, learning goals, and a dated project timeline. The 12 November 2026 presentation is marked planned.
- Gaming, Shopping, and Theater & Drama categories alongside existing categories.
- Public event/activity calendar scoped to published, authorized listings and their time zones; separate fictional demo calendar.
- Age, date, area, indoor/outdoor, and availability discovery filters. Availability uses stored allocation data.
- Anonymous feedback and listing reports with consent, CSRF protection, honeypot validation, existing POST rate limits, and persistent records. Private school reports require authorized listing access. Verified school staff review their school's reports; superusers handle general feedback through Django admin.
- Shared interface language catalogs and persistent language selection for English, European Portuguese, and Turkish. Core navigation, discovery, About, and feedback are localized. Advanced workspace strings and user-authored listings may remain in their original language or English; this limitation is disclosed on About.

## Content and privacy

`content/project.json` controls contributor profiles. Public names are intentionally empty pending school/publication permission, including parental permission where needed. Student cards have equal roles and visual weight. No student photos, contact information, or biographies are fabricated. `content/about.json` contains the three language versions of editorial content. Moviinn is acknowledged as a research interview contributor, without implying partnership or endorsement.

Feedback asks visitors not to include children's private information. Operators can inspect retention with `python manage.py prune_feedback --days 90`; deletion requires explicitly adding `--apply`. Retention is not automatically scheduled by this release.

## Validation

133 backend tests pass with isolated PostgreSQL, covering existing workflows plus Release A visibility, feedback authorization, translations, categories, calendar, and retention. Browser coverage exercises family and organizer flows, saved-data receipts, registration-free demo, translated discovery/About/calendar, feedback submission, and mobile/tablet/desktop overflow checks. The actual Vercel preview build script passes locally with test configuration; required production settings continue to fail closed when missing. Migration 0006 is additive.

## Deployment and remaining scope

The existing Vercel build script runs migrations only for production deployments. GitHub main pushes use the connected Vercel deployment workflow. Hosted readiness must be checked in Vercel: this execution environment's proxy blocks the supplied public Vercel URL, and no Vercel account credential is connected here.

Additional requested locales, Hebrew RTL, human editorial translation review, approved named credits, and later roadmap releases remain follow-up work. They are not represented as completed features. This release adds no paid services or new external AI provider.
