# Voice search on Discover

Discover in the fictional demo and live community/event/activity explorer includes an accessible microphone button. The implementation uses the browser's native SpeechRecognition or webkitSpeechRecognition API, with English and Portuguese controls and the selected interface language for recognition.

The user sees a privacy explanation and parent-agreement checkbox before listening. Only interests should be spoken. After recognition, the transcript is editable; the user explicitly chooses **Search with AI** before the text is sent to Claude. TK-Zone does not record, store, or upload audio files. The browser's speech service may process audio online; its availability and privacy terms are separate. Browser microphone permission is still required.

Live Discover submits the reviewed text to the existing CSRF-protected `/finder/` flow. The demo uses a CSRF-protected `/demo/voice-filters/` endpoint and applies Claude's validated filters to fictional listings only. Neither path makes a booking or approval. Age, interest(s), area, language, price, day and time-period constraints are respected. Multiple interests use OR matching, so drawing and football can find Arts or Sports. Standard typed search remains available without voice or AI.

The transcript is not written to the demo checkpoint. Only applied structured filters are preserved through refresh. Successful voice searches do not create real events or child records. The existing POST rate limits apply, no API key is exposed, and consent, payload limits and validation are checked before a provider call.

Denied permission, missing microphones, unsupported browsers, speech-service failures, and unavailable AI show clear messages. Cancel and page exit stop recognition; users can stop it manually as well. The browser must support speech recognition in a secure context (normally HTTPS). Claude searches still require an API key and available credits.

Implementation: `static/community/voice-search.js`, the shared voice-button template, `community/voice.py`, and extensions to the existing Finder interpreter and demo filters. No new package, speech API key or paid transcription service is installed.

Validation uses simulated browser speech events, not a real microphone or a paid provider request. Tests cover transcript review, mixed-interest matching, refresh recovery, denied permission, cancellation, unsupported-browser typed search, live Finder submission, consent, CSRF, payload limits, provider errors, and responsive layouts. Actual recognition accuracy and availability should be rehearsed on the presentation device and school network.
