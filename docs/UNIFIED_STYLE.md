# One TK-Zone product shell

The demo and live Django pages now share `static/community/product-shell.css`. Both the server-rendered base template and demo browser renderer use the same product-brand, product-header, product-sidebar and product-main component classes. Updating these styles changes both experiences together.

The shared design uses locally hosted Archivo, DM Mono and Source Serif 4; the prospectus purple palette; white navigation; a near-white canvas; violet active states; rounded controls/cards; and dark-violet hero panels. Mobile navigation uses the same horizontally scrollable sidebar treatment as the demo, with wrapping header controls to accommodate translated labels. The same layouts support right-to-left languages. Reduced-motion and larger-text preferences remain supported.

Live navigation keeps authentication-aware links, school/staff/organiser destinations, notification/profile controls, language selection, and database save receipts. Demo role switching remains presentation-only. Live school content, permissions and submission forms are preserved. A live-community header label distinguishes real content from fictional presentation data without changing the visual identity. The duplicate live bottom-navigation and top link strip have been consolidated into the shared sidebar; their destinations remain available.

Validation includes comparison of computed header, sidebar, background and font styles on `/demo/`, `/community/`, and `/finder/` at 360, 390, 768, 1024 and 1440px in English, Portuguese and Arabic; keyboard navigation; active route states; and retained CSRF form controls. Existing production and demo browser workflows are included. All 197 backend tests and the Vercel preview build script pass locally. Older browser selectors were updated for the current capacity controls and asynchronous upload preview, preserving the tested behaviour.

Screenshots captured with reduced motion for sharp, stable output:

- [Community](screenshots/unified-community.png)
- [Finder](screenshots/unified-finder.png)
- [Mobile community](screenshots/unified-community-mobile.png)

No migrations, new credentials, paid services, or changes to AI configuration are required. A connected GitHub push can trigger Vercel; hosted readiness must still be checked in Vercel.
