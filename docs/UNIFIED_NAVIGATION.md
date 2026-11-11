# Unified sidebar

The live Django pages and presentation use one destination definition in `community/navigation.py`. Native rendering uses `discovery/sidebar.html`; the presentation consumes the same server-provided list and keeps its existing in-session demo navigation and role checks. There is no Community tools wrapper, second primary menu, sidebar introduction, school badge, tagline, or alternate mobile list.

## Destination audit

Order: Home, Activities, Find schools, Saved, Family workspace, then the remaining unique tools, followed by About Us and Team photos.

- Activities already combines one-off events and recurring clubs. The redundant Events menu item is consolidated into Activities; `/events/`, individual event links, and `/activities/` remain functional and highlight Activities.
- Community feed, Activity Finder, actual event Calendar, explicitly fictional Demo catalogue, My zone, Crews, fictional family Calendar, presentation demo, Safety Centre, feedback, and account/profile access remain directly accessible. The demo parent inbox is the existing Family workspace destination, rather than another duplicate menu item.
- School announcements, student tickets, and school joining remain available as appropriate to the account.
- Verified staff retain overview/listings, school directory editing, participation requests, announcement studio, listing reports/feedback, organiser applications, and content moderation.
- Organiser studio and demo moderation retain their existing account/role restrictions. Switching demo roles updates the relevant workspace entries.
- About Us and Team photos are the final entries.

Saved is one sidebar destination. Existing account saved records and collections are unchanged, school shortlists remain separate, and the Saved page now also clearly links to this tab’s fictional demo favourites. Guest device saves and demo session saves keep their existing storage keys and behaviour. No data migration or deletion is involved.

## Mobile and accessibility

A single labelled Menu button opens the same sidebar DOM used on desktop. `aria-expanded` and `aria-controls` describe it, keyboard focus moves to the first destination, and Escape closes it and restores focus. Navigation closes after choosing a destination. This is an inline expanded region, not an inaccessible modal. Icons, padding, active states, hover states, and focus treatment are consistent. Short desktop viewports use denser spacing without hiding tools.

## Verification

Backend checks cover unique keys/URLs, ordering, route resolution, exactly one active entry, preserved staff/student tools, and existing saves/collections. Browser checks cover actual guest link responses, desktop/mobile list equality, mobile opening/Escape/focus, overflow, active entries, presentation navigation, and role switching. Existing browser journeys now open the mobile menu before using sidebar links.

Home, Activities, Find schools and About Us keep their canonical URLs from the presentation as well. The separate fictional catalogue has its own clearly labelled entry; existing demonstration links retain their in-session interactions.

Final verification: 265 backend tests and 34 Chromium browser tests passed. JavaScript syntax checks, Django system checks, migration drift checks, and the actual Vercel Preview build script passed. Screenshots: `screenshots/unified-sidebar-desktop.png` and `screenshots/unified-sidebar-mobile.png`. Hosted Vercel deployment readiness is not established by these local checks.
