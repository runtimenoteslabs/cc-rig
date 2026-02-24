"""Next.js framework template content."""

CONTENT: dict = {
    "rules": """\
## Framework Rules (Next.js / App Router)
- Use the App Router (`app/` directory). Do NOT use the Pages Router.
- Default to React Server Components (RSC). Add `"use client"` only when \
the component needs browser APIs, useState, useEffect, or event handlers.
- Data fetching belongs in Server Components or Route Handlers, never in \
client components. Use `fetch()` with Next.js caching options.
- Route Handlers go in `app/api/**/route.ts`. Use NextRequest/NextResponse.
- Layouts (`layout.tsx`) own shared UI. Do not duplicate nav/footer in pages.
- Use `loading.tsx` and `error.tsx` for Suspense boundaries per route segment.
- Image optimization: always use `next/image`, never raw `<img>` tags.
- Environment variables: server-only by default. Prefix with `NEXT_PUBLIC_` \
only when the value must reach the browser.\
""",
    "architecture": """\
# Architecture — Next.js App Router

## Directory Layout
```
app/
  layout.tsx          # Root layout (html, body, providers)
  page.tsx            # Home route
  (auth)/             # Route group — shared auth layout
    login/page.tsx
    register/page.tsx
  api/
    route.ts          # API route handlers
  dashboard/
    layout.tsx        # Nested layout
    page.tsx
    loading.tsx       # Streaming fallback
    error.tsx         # Error boundary
lib/                  # Shared utilities, API clients, constants
components/
  ui/                 # Presentational / design-system components
  features/           # Feature-specific composite components
```

## Key Patterns
- **Server Components by default**: fetch data at the component level; no \
waterfall because requests are deduplicated and cached.
- **Client islands**: wrap interactive pieces in `"use client"` components \
and keep them as leaf nodes.
- **Parallel routes & intercepting routes**: use `@slot` and `(.)` \
conventions for modals and split layouts.
- **Server Actions**: colocate mutations in `"use server"` functions; \
call from forms or `startTransition`.
- **Middleware** (`middleware.ts` at project root): auth redirects, \
geo-routing, feature flags. Runs on the Edge.
- **Caching layers**: Request memoization → Data Cache → Full Route Cache. \
Use `revalidateTag` / `revalidatePath` to bust caches.\
""",
    "conventions": """\
# Conventions — Next.js

## Naming
- Files: kebab-case (`user-profile.tsx`). Components: PascalCase.
- Route segments: lowercase with hyphens (`app/user-settings/page.tsx`).
- Server Actions: prefix with verb (`createUser`, `deletePost`).

## Component Guidelines
- One exported component per file. Co-locate types in the same file \
unless shared.
- Props interfaces named `<Component>Props` and exported.
- Avoid `useEffect` for data fetching — use Server Components instead.
- Wrap third-party client libs in a thin client component to keep the \
import boundary explicit.

## State Management
- Server state: fetch in RSC, pass as props. No global store needed \
for server data.
- Client state: React context or Zustand for cross-component client state. \
Avoid Redux unless already adopted.
- URL state: use `searchParams` and `useSearchParams` for filter/sort/page.

## Error Handling
- Every route segment should have an `error.tsx` boundary.
- API Route Handlers: return typed `NextResponse.json()` with explicit \
status codes. Never throw unhandled.
- Use `notFound()` from `next/navigation` — do not return 404 manually.\
""",
    "testing": """\
# Testing — Next.js

## Stack
- **Unit/Component**: Vitest + React Testing Library.
- **E2E**: Playwright (preferred) or Cypress.
- **API Routes**: direct handler invocation with mocked NextRequest.

## Principles
- Test behavior, not implementation. Query by role/label, not class names.
- Server Components: test the rendered output via a thin wrapper that \
calls the async component and renders the result.
- Client Components: render with `@testing-library/react`, simulate user \
events, assert on DOM changes.
- Mock `fetch` at the network layer (MSW) so server/client components \
both hit the same mock.

## File Layout
```
src/__tests__/
  components/       # Component unit tests
  app/              # Route-level integration tests
  lib/              # Utility tests
e2e/                # Playwright specs
```

## Commands
- `npm test` — run Vitest in watch mode.
- `npm run test:ci` — single run with coverage.
- `npx playwright test` — E2E suite.\
""",
    "deployment": """\
# Deployment — Next.js

## Build
- `next build` produces `.next/` with static + server bundles.
- Check `next build` output for route-level static/dynamic classification.

## Vercel (recommended)
- Zero-config: push to main, Vercel auto-deploys.
- Preview deployments on every PR branch.
- Environment variables set in Vercel dashboard, not `.env` in repo.

## Self-Hosted (Node.js)
- `next start` runs the production server on port 3000.
- Use `output: "standalone"` in `next.config.js` for Docker-friendly \
minimal builds.
- Reverse proxy (nginx/Caddy) in front for TLS termination.

## Environment Variables
- Build-time: `NEXT_PUBLIC_*` baked into client JS.
- Runtime: server-only vars read via `process.env` in Route Handlers \
and Server Components.
- Never commit `.env.local` — use `.env.example` as a template.\
""",
}
