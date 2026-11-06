# Languages, family attendance and moderated photographs

The existing Django application remains the source of truth. No external translation, image host, database service or notification service is called at runtime.

## Languages

The visible selectors support English, Mandarin Chinese (Simplified), Hindi, Spanish, Arabic, French, Bengali, European Portuguese, Russian and Urdu. Existing Turkish support remains available. Preference is stored in the signed-in account and a one-year HttpOnly, SameSite browser cookie. Arabic and Urdu set `dir=rtl` and use mirrored responsive layouts. The live site translates known interface text on the server, including forms and messages; the demo can switch catalogs without losing its in-memory state. User-authored text is marked so it is not translated.

Catalogs cover existing interface strings and the new workflows. New catalog entries were machine-translated from interface-only text; personal records and photographs were not sent for translation. Native-language editorial review can improve wording. Django supplies its native validation translations. Source English and translated catalogs must have matching keys; the regression suite checks this.

## Attendance

`Event.capacity` retains its existing total-seat meaning. New nullable `child_capacity` fields support a separate child limit on events and activity sessions. Confirmed school tickets and legacy child participations count as children; confirmed family bookings add their stated adults and children. Children count in both limits. Pending requests do not reserve spaces.

Family registrations support adults-only groups and collect counts rather than attendee identities. The organizer's existing management page lists the requests and confirms, declines or cancels them. The family workspace supports cancellation. Event and session cancellations close the affected bookings. Capacity is checked again while holding the existing event/session database locks; forms cannot lower limits below confirmed allocations. The race regression exercises competing school and family confirmations.

Migration `0007` adds fields and tables without changing or deleting existing event, ticket or family data. The existing production build applies it through the GitHub-to-Vercel workflow.

## Comments and experience photos

Parent/guardian accounts and verified organizers/staff can submit comments and up to three photos per upload (3 MB combined, up to twelve per contribution). Authenticated users can report published comments or photos. Content starts pending moderation and editing a published contribution sends it back for review. Authors can edit/delete their own content and photo descriptions. School administrators moderate at `/staff/content/`; global administrators can moderate across schools.

Images are decoded, checked for size/type, reoriented and re-encoded as JPEG with metadata removed. They remain in the application's existing private storage. Every image response rechecks visibility and returns private/no-store headers. File bytes are removed after record deletion or photo replacement. Captions and comments are rendered as escaped text.

## Team photos

Administrators manage individual profiles and group galleries at `/team/photos/`. They can prefill a roster member from the upload page. Names, roles, captions and accessible image descriptions are supported. The uploader includes the exact requested permission notice.

Visibility defaults to **Administrators only**. School and public visibility require a sharing-permission declaration, and student/child-containing photographs require guardian consent. A group containing children must be marked accordingly. Student cards display first names by default. Full names remain available only in the protected administrator editor. Photo URLs enforce the same visibility rules as the gallery.

The supplied portraits must stay administrators-only as requested. No real photographs are committed to the public GitHub repository, and no privileged production account is created automatically. An authorized school administrator uploads the original files through the protected uploader; image files embedded in chat are not automatically imported into the production database.

## Verification

Run the existing build, Django suite, Node suites and optional browser walkthrough:

```sh
sh scripts/vercel-build.sh
python manage.py test --noinput
node static/community/demo-state.test.cjs
node static/community/succession.test.cjs
python manage.py test community.browser_expansion --noinput
```

Browser tests require the existing development Playwright dependency and Chromium. They use synthetic images and isolated fictional accounts. Production photo import and actual content moderation are performed by authorized users, not by test fixtures.
