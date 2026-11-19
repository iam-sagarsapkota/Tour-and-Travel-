# Frontend

React 19 + Vite 8 + TypeScript, Tailwind CSS 4, shadcn/ui, React Bits, TanStack Query,
React Router 7. Exact versions are pinned in `frontend/package-lock.json`.

## Layout

```
frontend/src/
  components/
    animations/            React Bits wrappers (HeroHeadline, Reveal)
      reactbits/           React Bits source, installed from the official registry
    ui/                    shadcn/ui primitives (button, input, label, badge, skeleton, sonner)
    CoverImage, DifficultyBadge, PriceDisplay, Pagination, States, LoadingSkeleton
  features/
    auth/                  AuthContext, login/register forms, RequireAuth guard
    events/                EventCard, FilterSidebar, URL filter state, queries
    destinations/          DestinationCard, queries
  layouts/                 RootLayout (navbar, footer, toasts)
  pages/                   Home, Events, EventDetail, Destinations
  routes/                  AppRoutes (lazy-loaded pages)
  lib/                     api client, token store, safeNext, formatting
  types/                   API response types
```

## Brand tokens

Defined once in `src/index.css` (PRD 11.1) and mapped onto shadcn/ui variables:
Forest Green `#123B32` (primary), Adventure Gold `#E8A34A` (accent), Off White `#F7F8F5`
(background), Slate `#263238` (text), plus semantic success, warning and destructive.
Headings use Manrope, body text Inter, both self-hosted via Fontsource.

## Authentication in the browser

- Access token in memory only; refresh token in `sessionStorage` (survives reload, ends with
  the tab). Tokens go in the `Authorization` header, so there is no CSRF exposure.
- On a 401 the client refreshes once (concurrent requests share a single refresh) and retries.
- Guests opening `/events/{slug}` are redirected to `/register?next=/events/{slug}`; the
  login link carries the same `next`. After sign-in the user returns to that page.
- `next` is validated by `lib/safeNext.ts`: single-slash local paths under `/events`,
  `/destinations`, `/dashboard` or `/admin` only. Anything else falls back to `/events`.
- The route guard is a convenience. The API rejects unauthenticated detail requests itself.

## Event listing

All filter state lives in the URL query string, so results can be shared and survive reloads.
Values are validated when read from the URL; invalid ones are dropped before calling the API.

## React Bits components

| Component | Where | Notes |
|-----------|-------|-------|
| Split Text | Homepage hero headline (`HeroHeadline`) | Words rise on load |
| Spotlight Card | Featured event cards on the homepage only | Gold spotlight, light theme |
| Animated Content | Scroll reveal for homepage sections (`Reveal`) | 32 px rise, 0.6 s |

- **Source:** official registry, `npx shadcn add https://reactbits.dev/r/<Name>-TS-TW.json`
  (TypeScript + Tailwind variants), installed November 2026. The registry does not version
  components; the installed source is committed under `components/animations/reactbits/`
  and is not edited, so it can be diffed against a later download.
- **Dependencies:** Split Text and Animated Content require GSAP (`gsap` 3.15, `@gsap/react`).
  No other animation library is installed.
- **Licences:** React Bits is MIT with the Commons Clause (free to use in this product; the
  components themselves may not be sold). GSAP is under its standard no-charge licence
  (https://gsap.com/standard-license).
- **Accessibility and performance:** all three components honour `prefers-reduced-motion`.
  Split Text and Animated Content are lazy-loaded with the plain content as the Suspense
  fallback, so text is readable immediately and there is no layout shift. Animation is not
  used on forms, filters or anything in the booking path.

Not yet used from the PRD list: Blur Text and Aurora (hero, medium priority), Tilted Card
(destinations), Count Up (admin KPIs, phase 6), Magnet, Shiny Text and Marquee (low priority).

## Commands

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173, proxies /api to http://localhost:8000
npm test               # Vitest + React Testing Library
npm run typecheck
npm run lint           # oxlint
npm run format:check   # Prettier
npm run build
```

With Docker, `docker compose up` starts the frontend on http://localhost:5173.
