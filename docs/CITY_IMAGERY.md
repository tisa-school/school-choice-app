# Project sharing artwork

Event cards, event details and organiser previews follow [Activity image policy](ACTIVITY_IMAGE_POLICY.md). Generic cityscape event fallbacks have been retired; the older city-cover helper and unused riverside files have been removed.

The rooftop/Tagus illustration remains only in the **generic TK-ZONE brand preview**, not as an event cover. It was generated for this project on 10 November 2026 and is explicitly disclosed as an AI-generated city illustration. It is not documentary photography or evidence of a venue. No real children are depicted.

`static/community/imagery/tk-zone-share.png` is a 1200 × 630 composition with the school name and mission. `scripts/share-preview.html` is the editable layout; `python scripts/render-share-preview.py` regenerates it using development-only Playwright/Chromium and a loopback HTTP server.

Shared base/demo templates render Open Graph and Twitter metadata on the server. The static PNG is public without authentication or client-side JavaScript. The generic copy does not expose private activities, child profiles or query strings. It never claims to show a specific event.

`PUBLIC_SITE_URL` defaults to `https://school-choice-app-hrvb.vercel.app`. For a future custom domain, set the HTTPS origin only and redeploy. Sharing URLs use this trusted setting instead of the request Host header.

Tests check the PNG dimensions, absolute generic metadata and anonymous image retrieval. Actual WhatsApp and LinkedIn rendering requires their crawlers to fetch the Ready deployment. Existing shares may cache an old preview; the app cannot force a third-party cache refresh.
