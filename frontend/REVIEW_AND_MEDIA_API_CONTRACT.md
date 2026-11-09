# Frontend integration still needed

The current backend exposes curated places but no public traveler-review or traveler-story API. The frontend therefore shows an honest empty state and does not accept review submissions or display ratings. Editorial journal articles must stay separate from visitor submissions.

## Traveler reviews

Suggested contract for a future backend (not called by this frontend yet):

- `GET /api/places/{place_id}/reviews?cursor=&sort=recent|helpful&rating=1..5` returns `{ reviews: [...], next_cursor, total_count, rating_summary }`. Each review needs a stable `id`, catalog `place_id`, display name or anonymous label, integer rating 1–5, text, `created_at`, optional `visited_at`, moderated approved photo URLs, and a server verified publication state. `rating_summary` should include count and distribution calculated only from published reviews.
- `POST /api/places/{place_id}/reviews` accepts rating, text, optional visit date and approved uploads from an authenticated traveler. The response must distinguish accepted for moderation from published; the UI must never show a public success claim before publication.
- Helpful and report actions need authenticated, rate-limited endpoints and an explicit response state. Photos need a secure upload flow with size/type limits, moderation, copyright rules, and deletion support.
- Public `GET /api/reviews` or equivalent feed is needed before the global Traveler Reviews page can show real content. Story/community features also need their own moderated API and cannot reuse editorial articles as user content.

## Destination media and visitor information

`GET /api/places` currently has location, copy, source links, and suggested visit duration, but no structured gallery, verified opening hours, ticket prices, accessibility, nearby places, or live availability. The new detail page uses an existing credited Wikimedia image when available and otherwise shows a no-photo state. A future media contract should provide per-place image URLs, localized alt text, creator, license, source, attribution, sort order, and a moderation/rights state. Any hours, prices, or accessibility claims need source URL and last-verified time. The current UI intentionally omits unsupported facts.

## Trip handoff

The current planner accepts cities, interests, days, pace and family options. It does not accept a required `place_id`. A real “Add to Trip” action needs a planner request field or draft itinerary endpoint that can add a specific place while preserving the user's existing plan. Until then, the detail page offers “Ask AI” and save place, without a misleading add action.
