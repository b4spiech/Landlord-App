# APEX Element Group — Brand Integration (instructions for Claude Code)

This folder (`brand/` at the repo root) holds the final APEX Element Group logo
files. Integrate them into the APEX Property Management app in the phases below.

## Ground rules

- Create a branch off `dev` named `brand-integration` before changing anything. Commit at the end of each phase.
- Do not change backend behavior, API routes, data models, or business logic. This is a visual change only.
- Do not edit, redraw, recolor, or "improve" the logo artwork. Use the files in `brand/` exactly as provided.
- The Railway image serves the committed `frontend/dist`. After any change under `frontend/`, run `npm run build` in `frontend/` and commit the updated `frontend/dist`.
- Do not make requests to the live site or any Railway URL.
- At every STOP, stop, summarize what changed, list the files touched, and wait for me to say "continue."

## Brand reference

### Files in `brand/`

| File | Use |
|---|---|
| `apex-logo-horizontal.svg` / `.png` | Primary logo on light backgrounds (headers, login, documents) |
| `apex-logo-horizontal-reversed.svg` / `.png` | Primary logo on navy/dark backgrounds |
| `apex-logo-horizontal-black.svg` | One-color black (fax, stamps, single-color print) |
| `apex-logo-stacked.svg` / `.png` | Square-ish spaces (login card, splash, social avatar) |
| `apex-logo-stacked-reversed.svg` | Stacked, on dark backgrounds |
| `apex-mark.svg` / `.png` | Icon only, light backgrounds (collapsed sidebar, small spaces) |
| `apex-mark-white.svg` | Icon only, dark backgrounds |
| `favicon.ico` (16/32/48), `favicon.svg` | Browser tab |
| `apple-touch-icon.png` (180) | iOS home screen |
| `icon-192.png`, `icon-512.png` | Web app manifest |

All SVG text is converted to outlines, so the SVGs render correctly without the font installed.

### Colors

| Token | Hex | Use |
|---|---|---|
| `apex-navy` | `#0B2545` | Primary brand color, headers, dark surfaces, primary text |
| `apex-deep` | `#1F4F8F` | Secondary text, hover on navy, links |
| `apex-blue` | `#2B7BE4` | Accent, primary buttons, focus rings, active nav item |
| `apex-sky` | `#5FA2F5` | Accent on navy backgrounds only |
| `apex-mist` | `#B9D3F5` | Secondary text on navy backgrounds |
| white | `#FFFFFF` | Light surfaces |

Contrast: `apex-blue` on white is about 4.0:1, so it is fine for buttons with white text at 16px semibold+ and for large text, but use `apex-deep` or `apex-navy` for small body text and links.

### Typography

Montserrat: 700 for headings and the wordmark style, 500/600 for UI labels. Body text can stay on the existing system/Tailwind sans stack if it is already set; otherwise use Montserrat 500 with a fallback of `system-ui, sans-serif`.

### Mark geometry (for an inline React component)

ViewBox `0 0 100 88`:

```
<path fill-rule="evenodd" d="M0 88 L50 0 L100 88 Z M24 88 L50 42.24 L76 88 Z" />   <!-- outer chevron -->
<path d="M32 88 L50 56.32 L68 88 Z" />                                             <!-- inner triangle -->
```

Light background: chevron `#0B2545`, inner `#2B7BE4`. Dark background: chevron `#FFFFFF`, inner `#5FA2F5`.

### Usage rules

- Clear space around any logo: at least the height of the inner triangle on all sides.
- Minimum size: horizontal logo 120px wide on screen; below that, use the mark alone.
- Never stretch, rotate, recolor outside the palette, add shadows/gradients, or place the color logo on a busy or mid-tone background.

---

## PHASE 0 — Recon (no changes)

1. Inspect `frontend/` and report: where `index.html` is, current favicon/title/meta tags, whether `frontend/public/` exists, the Tailwind config file and version (v3 `tailwind.config.*` vs v4 CSS `@theme`), how fonts are loaded today, and every place the app currently shows a logo, app name, or placeholder brand text (sidebar, top bar, login/landing page, page titles, empty states).
2. Find every backend Jinja2 template used for generated PDFs (WeasyPrint) and emails, and report where a logo or company name appears or should appear (headers/letterhead).
3. Propose exactly where each brand file will be used.

STOP — report findings and the placement plan.

## PHASE 1 — Favicons, title, and manifest

1. Copy into `frontend/public/`: `favicon.ico`, `favicon.svg`, `apple-touch-icon.png`, `icon-192.png`, `icon-512.png`.
2. Create `frontend/public/site.webmanifest` with `name` "APEX Property Management", `short_name` "APEX", `theme_color` and `background_color` `#0B2545`, `display` "standalone", and the 192/512 icons.
3. In `frontend/index.html`, remove any old/default (e.g. Vite) favicon and add:
   - `<link rel="icon" href="/favicon.ico" sizes="any">`
   - `<link rel="icon" href="/favicon.svg" type="image/svg+xml">`
   - `<link rel="apple-touch-icon" href="/apple-touch-icon.png">`
   - `<link rel="manifest" href="/site.webmanifest">`
   - `<meta name="theme-color" content="#0B2545">`
   - Keep `<title>APEX Property Management</title>`.
4. Confirm the FastAPI SPA catch-all in `app/main.py` serves these root-level files from `frontend/dist` (it serves real files that exist in dist). Do not change that route's logic in this phase.

STOP — show the diff.

## PHASE 2 — Design tokens and font

1. Add the colors above as Tailwind theme colors named `apex-navy`, `apex-deep`, `apex-blue`, `apex-sky`, `apex-mist` (v3: `theme.extend.colors` in `tailwind.config.*`; v4: `@theme` variables in the main CSS). Do not remove existing colors.
2. Load Montserrat (500, 600, 700). Prefer self-hosting via `@fontsource/montserrat` (import the three weights in `main.tsx`) so the app has no runtime dependency on Google Fonts; tell me if you chose otherwise and why.
3. Add a `font-brand` family (`Montserrat, system-ui, sans-serif`) to the Tailwind theme. Apply it to headings and nav; leave body text as is unless Phase 0 showed no font is set.

STOP — show the diff.

## PHASE 3 — Logo components

1. Copy the SVG logo files into `frontend/src/assets/brand/`.
2. Create `frontend/src/components/brand/ApexMark.tsx`: an inline SVG using the geometry above, props `variant: "color" | "reversed" | "mono"` (mono uses `currentColor` for both paths), `size` (height in px, width = height × 100/88), and `title` for accessibility (`role="img"` + `<title>`; when `decorative` is true use `aria-hidden="true"` instead).
3. Create `frontend/src/components/brand/ApexLogo.tsx`: renders the imported horizontal or stacked SVG via `<img>` with props `layout: "horizontal" | "stacked"`, `variant: "color" | "reversed"`, `className`, and `alt="APEX Element Group"`.
4. Export both from `frontend/src/components/brand/index.ts`.

STOP — show the components.

## PHASE 4 — Apply in the UI

1. Sidebar/top nav: horizontal logo (reversed if the nav is navy, color if light). If the sidebar collapses, show `ApexMark` alone when collapsed.
2. Login/landing page (if one exists): stacked logo centered.
3. Brand accents: primary buttons `bg-apex-blue` with white text and a darker hover (`hover:bg-apex-deep`), active nav item uses `apex-blue`, focus rings `apex-blue`, page headings `text-apex-navy font-brand`. Change only brand-level styling, not layouts.
4. Replace any leftover placeholder brand text or generic icons used as a logo.
5. Check at phone width that the header logo doesn't overflow; switch to the mark alone below ~380px if needed.
6. Run `npm run build` and commit `frontend/dist`.

STOP — list every component changed, with before/after descriptions.

## PHASE 5 — Generated documents and email

1. Copy `apex-logo-horizontal.png` (and the SVG if WeasyPrint templates can reference it) to the backend's template static location. Reference it with an absolute filesystem path or a `base_url` passed to WeasyPrint so it resolves during PDF rendering; do not use a remote URL.
2. Add a letterhead header to the PDF templates (lease break options, termination agreement, move-out statement): logo top-left at about 1.8in wide, a thin `#2B7BE4` rule beneath, company name and `apexelementgrp.com` in the footer. Keep all existing template content and field logic unchanged.
3. For HTML emails, add the logo at the top using a hosted URL only if the app already serves static files publicly; otherwise use the company name in navy Montserrat-style bold text and tell me (email clients block most inline/CID images unpredictably).
4. Generate one sample PDF of each template locally and tell me the output paths so I can review them.

STOP — show diffs and the sample PDF paths.

## PHASE 6 — Wrap-up

1. Add a short "Branding" section to the README pointing to `brand/` and `brand/BRAND_INTEGRATION.md`, listing the color tokens and components.
2. Confirm nothing outside the brand scope changed (`git diff --stat dev`).

STOP — final summary.
