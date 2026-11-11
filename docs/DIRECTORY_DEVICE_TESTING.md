# School directory expansion and device testing

## Feature review

The existing app has public school/activity discovery, age/stage/type/language/curriculum/fee filters, sourced detail pages, three-school comparison, guest/account shortlists, family plans and approvals, organizer tools, moderated experiences/photos, team uploads, and 11 selectable interface languages. These findings come from the connected source; the supplied deployment URL redirects anonymous requests to Vercel login.

This change adds six official-site school profiles alongside the project-supplied Unicorn School profile, town filtering, alphabetical/recent-check/starting-fee sorting, and a public `/test/` page reachable from navigation, school search and the footer. Unknown fees sort last. Filtering and sorting remain in the URL.

## Sources checked 11 November 2026

- Carlucci American International School of Lisbon: https://www.caislisbon.org/
- The British School of Lisbon: https://www.britishschool.pt/
- St. Julian’s School: https://www.stjulians.com/
- TASIS Portugal: https://www.tasisportugal.org/
- United Lisbon International School: https://www.unitedlisbon.school/
- Colégio Moderno: https://colegiomoderno.pt/colegio-moderno/projeto-educativo/

Profiles contain only supported fields. Ages, teaching languages and fees are left blank when the reviewed page did not establish them. No school photos, rankings, current vacancies or school memberships were created. The additive migration inserts by slug without overwriting staff changes; reversing it deliberately preserves records that staff may have edited.

## QR sharing

`/test/` defaults to `PUBLIC_SITE_URL + /schools/`, with a family-demo destination and the exact original preview as alternatives. QR codes are generated locally as PNGs, with a four-module quiet zone. The page supports downloading, copying, printing and opening the displayed link. It includes a testing checklist and feedback link. Public URLs do not carry account sessions, saved records or child data. Links come from trusted settings/fixed destinations, never request Host or arbitrary query input.

The supplied preview requires Vercel sign-in. A QR code cannot bypass that protection. The configured public origin `https://school-choice-app-hrvb.vercel.app` returned HTTP 200 on inspection. Use that origin for unauthenticated testers, or grant tester access through Vercel yourself. This change does not modify hosting protection.

Production builds apply migration 0015 using the existing deployment pipeline. Install the pinned `qrcode` dependency and run collectstatic before tests that use manifest storage. No new environment variables are required. Override the existing PUBLIC_SITE_URL setting when sharing a different public domain.

## Further options

Useful next steps are broader public-school coverage from official directories, school-specific admissions deadlines with reviewed dates, a printable comparison/visit checklist, verified accessibility and learning-support details, and opt-in saved-search updates. These are proposals, not implemented features; contact/subscription delivery needs a confirmed service and consent flow.
