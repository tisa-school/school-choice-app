# TK-ZONE mobile development

Capacitor 8, **not Expo**. Development application ID: `org.unicornschool.tkzone`.
See [the complete setup, security and release guide](../docs/MOBILE_APP.md).

The existing application is Django, not Next.js. This directory bundles a local TypeScript frontend and adds iOS/Android adapters. The website remains intact. The mobile API is opt-in and is **not yet deployed to the live website**.

```bash
cd mobile
npm ci
cp .env.example .env.local
# Set VITE_API_BASE_URL to an approved HTTPS backend with /mobile/v1 enabled.
npm run build
npm test
npx cap sync
npx cap open ios      # Mac with Xcode
npx cap open android  # Android Studio
```

Do not use `npx eas-cli ...`: EAS is Expo tooling and this project stays on Capacitor.
No store submission, production deployment or main-branch merge is performed by these commands.
