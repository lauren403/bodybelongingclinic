# Body Belonging Clinic — website

Live site: **https://www.bodybelongingclinic.com.au**

Static HTML/CSS/JS. No build step — Netlify publishes this repository root as-is.

## Structure

```
/                     page HTML (one file per route)
/assets               images, PDF, nav.js
styles.css            single stylesheet
sitemap.xml           update when adding or removing a page
robots.txt
netlify.toml          headers + caching (see below)
```

## Editing

Every page is plain HTML. Edit, commit, push — Netlify deploys `main` automatically.

**Fee and session details appear in two places on most pages: the visible copy AND the
FAQPage JSON-LD block in `<head>`. Change both, or Google keeps serving the old figure
in rich results.**

## Source of truth

- **Fees and session lengths: Zanda** (Settings → Billing → Services). The site must
  match Zanda, never the other way around. See the project doc `locked-fee-schedule`.
- Standard session is **55 minutes**; first session is **60 minutes**. 50 minutes is the
  *Medicare eligibility minimum* for items 80160 / 91176 / 82379 / 93103 — it is not the
  session length and should not be advertised as one.
- The concession rate is **not published as a figure**. Use the wording already on
  `contact.html`: "A limited number of reduced-fee concession places are available."

## History

Initial commit is a byte-exact mirror of the live production deploy captured
19 August 2026, taken before the site moved off Netlify drag-and-drop deploys.
