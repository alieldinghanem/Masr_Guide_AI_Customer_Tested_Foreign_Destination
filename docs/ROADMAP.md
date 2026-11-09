# Roadmap

## Done (v1.8)

- Bilingual UI with RTL, hash routing, bilingual catalogue content incl. Arabic tips
- BM25 retrieval with Arabic normalisation, evaluation harness and regression guard
- Planner with estimated inter-city travel, route re-ordering and warnings; 12-invariant stress test
- Atomic catalogue rebuild, thread-safe index, trusted-proxy rate-limit keying
- Component-based frontend; ESLint (hooks rules enforced), unit/component and axe accessibility tests
- Hardened Docker/Nginx demo configuration; Nginx config smoke-tested with a real nginx

## Validate on your own machine before publishing

- The "Not verified here" list in `docs/QUALITY.md`: live LLM, real-browser/RTL visual review, Docker, CSP behaviour in a browser
- Review every reference URL, catalogue fact and image licence

## Next

1. Arabic/French versions of the longer detail text; larger catalogue with verified sources
2. Replace estimated travel with a routing/transport data source; model day-1 arrival
3. Embeddings + hybrid retrieval, judged on a larger, independently written evaluation set
4. Opening hours / ticket data from licensed providers; accounts and server-side saved trips
5. Production operations: TLS, distributed rate limiting, spend caps, observability
