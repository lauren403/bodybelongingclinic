#!/usr/bin/env python3
"""
site_gate.py — the gate for the Body Belonging Clinic website.

Run before any commit to the site, and in CI on every push:

    python3 .github/site_gate.py                 # every page, both widths, both themes
    python3 .github/site_gate.py resources.html  # one page
    python3 .github/site_gate.py --static        # source checks only, no browser

Why it exists (7 Sep 2026): the sheets section on /resources shipped with its
question and lede at opacity 0 for every visitor. The site's reveal script adds
`reveal-init` itself to a fixed list of selectors and only observes those; the
section hard coded the class onto two elements the script never watches. Every
check that ran before deploy measured geometry and never measured whether the
words could be seen. This gate measures whether the words can be seen.

Static checks, per page (no browser):
  S1  no `reveal-init` or `reveal-in` written into markup — the script owns them
  S2  every inline script block parses (`node --check`)
  S3  <title>, <meta charset>, <meta viewport> present

Render checks, per page, at 1280x900 and 390x844 (headless Chromium):
  R1  after scrolling the whole page, no visible text sits at effective opacity < 0.1
  R2  no visible text has contrast below 3:1 against its background, in light AND dark
      (below 4.5:1 is reported for review, not failed; text over images is skipped)
  R3  no horizontal overflow
  R4  every same-origin image and stylesheet loads; no console errors

A gate is only worth having if it has been seen to fail: `--self-test` injects the
7 Sep defect into a copy of resources.html and asserts the gate catches it.
"""
import argparse, http.server, json, os, re, shutil, subprocess, sys, tempfile, threading, functools

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
WIDTHS = [(1280, 900), (390, 844)]
THEMES = ['light', 'dark']
FAIL_CONTRAST, REVIEW_CONTRAST = 3.0, 4.5
MIN_OPACITY = 0.1

# ---------------------------------------------------------------- static checks

SCRIPT_RE = re.compile(r'<script(?P<attrs>[^>]*)>(?P<body>[\s\S]*?)</script>', re.I)
STYLE_RE = re.compile(r'<style[^>]*>[\s\S]*?</style>', re.I)

def static_checks(path):
    fails, notes = [], []
    html = open(path, encoding='utf-8').read()
    markup = STYLE_RE.sub('', SCRIPT_RE.sub('', html))
    for cls in ('reveal-init', 'reveal-in'):
        n = len(re.findall(r'class="[^"]*\b%s\b[^"]*"' % re.escape(cls), markup))
        if n:
            fails.append('S1 `%s` written into markup %d time(s); the reveal script owns that class' % (cls, n))
    for i, m in enumerate(SCRIPT_RE.finditer(html)):
        attrs, body = m.group('attrs'), m.group('body')
        if 'src=' in attrs or 'ld+json' in attrs or not body.strip():
            continue
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f:
            f.write(body); tmp = f.name
        r = subprocess.run(['node', '--check', tmp], capture_output=True, text=True)
        os.unlink(tmp)
        if r.returncode != 0:
            fails.append('S2 script block %d does not parse: %s' % (i, r.stderr.strip().splitlines()[-1] if r.stderr.strip() else '?'))
    head = html[:html.lower().find('</head>')] if '</head>' in html.lower() else html
    if not re.search(r'<title>[^<]+</title>', head, re.I): fails.append('S3 no <title>')
    if not re.search(r'<meta[^>]+charset', head, re.I): fails.append('S3 no <meta charset>')
    if not re.search(r'<meta[^>]+name="viewport"', head, re.I): fails.append('S3 no viewport meta')
    return fails, notes

# ---------------------------------------------------------------- render checks

PAGE_JS = r"""
async (args) => {
  const {minOpacity} = args;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  // Scroll the whole page so every observer-driven reveal has fired.
  const H = () => document.documentElement.scrollHeight;
  for (let y = 0; y < H(); y += Math.max(200, innerHeight * 0.6)) { scrollTo(0, y); await sleep(200); }
  scrollTo(0, H()); await sleep(1200); scrollTo(0, 0); await sleep(300);
  const effOpacity = el => { let o = 1; for (let e = el; e && e !== document.documentElement; e = e.parentElement) o *= parseFloat(getComputedStyle(e).opacity); return o; };

  const lum = (r, g, b) => { const f = c => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const parse = s => { const m = s && s.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(',').map(Number); return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1}; };
  const blend = (fg, bg) => ({r: fg.r * fg.a + bg.r * (1 - fg.a), g: fg.g * fg.a + bg.g * (1 - fg.a), b: fg.b * fg.a + bg.b * (1 - fg.a), a: 1});
  const ratio = (a, b) => { const l1 = lum(a.r, a.g, a.b), l2 = lum(b.r, b.g, b.b); return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05); };

  const desc = el => { const t = (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 60);
    const id = el.id ? '#' + el.id : ''; const cls = el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : '';
    return el.tagName.toLowerCase() + id + cls + ' "' + t + '"'; };

  const out = {invisible: [], lowContrast: [], review: [], checked: 0};
  const all = document.querySelectorAll('body *');
  for (const el of all) {
    if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'SVG', 'OPTION'].includes(el.tagName)) continue;
    let own = '';
    for (const n of el.childNodes) if (n.nodeType === 3) own += n.textContent;
    if (!own.trim()) continue;
    // Walk up: hidden ancestors, effective opacity, effective background.
    let e = el, opacity = 1, hidden = false, bg = null, overImage = false;
    while (e && e !== document.documentElement) {
      const cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden' || e.hidden) { hidden = true; break; }
      opacity *= parseFloat(cs.opacity);
      if (bg === null) {
        const c = parse(cs.backgroundColor);
        if (cs.backgroundImage && cs.backgroundImage !== 'none') overImage = true;
        if (c && c.a > 0) bg = c.a < 1 ? null : c;   // semi-transparent: keep walking and blend later
        if (c && c.a > 0 && c.a < 1) { bg = {pending: c}; }
      } else if (bg.pending) {
        const c = parse(cs.backgroundColor);
        if (c && c.a === 1) bg = blend(bg.pending, c);
      }
      e = e.parentElement;
    }
    if (hidden) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;                 // sr-only, collapsed, clipped
    const cs = getComputedStyle(el);
    if (cs.fontSize && parseFloat(cs.fontSize) < 1) continue;
    out.checked++;
    if (opacity < minOpacity) {
      // Confirm before accusing: bring it into view the way a reader would and read again.
      // A slow runner can leave an observer-driven reveal unfired; a real defect stays at 0.
      el.scrollIntoView({block: 'center'}); await sleep(700);
      const again = effOpacity(el);
      if (again < minOpacity) out.invisible.push(desc(el) + ' opacity=' + again.toFixed(2) + ' (still, after scrolling to it)');
      continue;
    }
    if (overImage) continue;
    if (!bg || bg.pending) bg = parse(getComputedStyle(document.body).backgroundColor);
    if (!bg || bg.a === 0) bg = {r: 255, g: 255, b: 255, a: 1};
    let fg = parse(cs.color); if (!fg) continue;
    if (fg.a < 1) fg = blend(fg, bg);
    const cr = ratio(fg, bg);
    const rec = desc(el) + ' ' + cr.toFixed(2) + ':1';
    if (cr < args.failContrast) out.lowContrast.push(rec); else if (cr < args.reviewContrast) out.review.push(rec);
  }
  out.overflow = document.documentElement.scrollWidth > document.documentElement.clientWidth + 1;
  return out;
}
"""

class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k): pass

def serve(root):
    handler = functools.partial(_Quiet, directory=root)
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, 'http://127.0.0.1:%d' % srv.server_address[1]

def render_checks(root, pages):
    from playwright.sync_api import sync_playwright
    srv, base = serve(root)
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for page_name in pages:
            fails, notes = [], []
            for (w, h) in WIDTHS:
                ctx = browser.new_context(viewport={'width': w, 'height': h})
                pg = ctx.new_page()
                # Netlify's image CDN (/.netlify/images?url=/assets/x.jpg&w=...) does not exist offline:
                # serve the original file so the page is measured with its pictures in place.
                def _cdn(route):
                    from urllib.parse import urlparse, parse_qs, unquote
                    u = parse_qs(urlparse(route.request.url).query).get('url', [''])[0]
                    f = os.path.join(root, unquote(u).lstrip('/'))
                    route.fulfill(path=f) if os.path.isfile(f) else route.fulfill(status=404)
                pg.route(re.compile(r'/\.netlify/images'), _cdn)
                # Freeze every transition and animation: theme toggles animate colour, and a
                # mid-transition read is neither theme. Reveals still complete, instantly.
                pg.add_init_script("addEventListener('DOMContentLoaded',()=>{const s=document.createElement('style');s.textContent='*,*::before,*::after{transition:none!important;animation:none!important}';document.head.appendChild(s);})")
                errors, missing = [], []
                pg.on('pageerror', lambda e: errors.append(str(e)))
                pg.on('response', lambda r: missing.append(r.url) if r.status >= 400 and r.url.startswith(base) else None)
                pg.goto(base + '/' + page_name, wait_until='load')
                pg.wait_for_timeout(400)
                for theme in THEMES:
                    pg.evaluate("t => document.documentElement.setAttribute('data-theme', t)", theme)
                    pg.wait_for_timeout(250)
                    r = pg.evaluate(PAGE_JS, {'minOpacity': MIN_OPACITY, 'failContrast': FAIL_CONTRAST, 'reviewContrast': REVIEW_CONTRAST})
                    tag = '%dpx %s' % (w, theme)
                    for x in r['invisible']: fails.append('R1 [%s] invisible: %s' % (tag, x))
                    for x in r['lowContrast']: fails.append('R2 [%s] contrast: %s' % (tag, x))
                    for x in r['review']: notes.append('R2 [%s] review: %s' % (tag, x))
                    if r['overflow']: fails.append('R3 [%s] horizontal overflow' % tag)
                    if theme == 'light': notes.append('checked %d text elements at %dpx' % (r['checked'], w))
                if missing: fails.append('R4 [%dpx] missing same-origin resource(s): %s' % (w, ', '.join(sorted(set(m.replace(base, '') for m in missing)))))
                if errors: fails.append('R4 [%dpx] console error(s): %s' % (w, ' | '.join(errors)[:300]))
                ctx.close()
            results[page_name] = (fails, notes)
        browser.close()
    srv.shutdown()
    return results

# ---------------------------------------------------------------- self test

# The defect that shipped on 7 Sep 2026, verbatim: reveal-init hard coded onto the pull quote.
DEFECT_FROM = '<blockquote class="pull-quote" style="margin: 0 0 2rem;">'
DEFECT_TO = '<blockquote class="pull-quote reveal-init" style="transition-delay: 110ms; margin: 0 0 2rem;">'

def self_test():
    """Copy the site, re-introduce the 7 Sep defect and the dark-mode <em> bug, and require the gate to fail."""
    tmp = tempfile.mkdtemp()
    for name in os.listdir(ROOT):
        if name.startswith('.'): continue
        src = os.path.join(ROOT, name)
        (shutil.copytree if os.path.isdir(src) else shutil.copy2)(src, os.path.join(tmp, name))
    path = os.path.join(tmp, 'resources.html')
    html = open(path, encoding='utf-8').read()
    assert DEFECT_FROM in html, 'self-test anchor not found; update DEFECT_FROM'
    html = html.replace(DEFECT_FROM, DEFECT_TO, 1)
    # A second, visible pull quote carrying the dark-mode <em> bug (accent hard coded to burgundy, 1.68:1 on the dark band).
    html = html.replace('<p class="lede-2">That is one of them.',
                        '<blockquote class="pull-quote">Where do you <em>actually</em> belong?</blockquote><p class="lede-2">That is one of them.', 1)
    html = html.replace('<p class="lede-2">That is one of them.', '<p class="lede-2">That is one of them. <script>var x = "unterminated;</script>', 1)
    open(path, 'w', encoding='utf-8').write(html)
    s_fails, _ = static_checks(path)
    r_fails, _ = render_checks(tmp, ['resources.html'])['resources.html']
    shutil.rmtree(tmp)
    want = {'S1': any(f.startswith('S1') for f in s_fails), 'S2': any(f.startswith('S2') for f in s_fails),
            'R1': any(f.startswith('R1') for f in r_fails), 'R2 dark em': any(f.startswith('R2 [1280px dark]') and 'actually' in f for f in r_fails)}
    for k, v in want.items():
        print('  self-test %-10s %s' % (k, 'caught' if v else 'MISSED'))
    return all(want.values())

# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pages', nargs='*')
    ap.add_argument('--static', action='store_true', help='source checks only')
    ap.add_argument('--self-test', action='store_true', help='prove the gate fails on a known defect')
    ap.add_argument('--quiet', action='store_true', help='hide review notes')
    a = ap.parse_args()
    if a.self_test:
        ok = self_test()
        print('self-test:', 'PASS (the gate fails when it should)' if ok else 'FAIL (a known defect got through)')
        sys.exit(0 if ok else 1)
    pages = a.pages or sorted(f for f in os.listdir(ROOT) if f.endswith('.html'))
    total_fail = 0
    static = {p: static_checks(os.path.join(ROOT, p)) for p in pages}
    rendered = {} if a.static else render_checks(ROOT, pages)
    for p in pages:
        fails = static[p][0] + rendered.get(p, ([], []))[0]
        notes = static[p][1] + rendered.get(p, ([], []))[1]
        total_fail += len(fails)
        print('%s %s' % ('FAIL' if fails else 'ok  ', p))
        for f in fails: print('     ' + f)
        if not a.quiet:
            for n in notes: print('       ' + n)
    print('\n%d page(s), %d failure(s)' % (len(pages), total_fail))
    sys.exit(1 if total_fail else 0)

if __name__ == '__main__':
    main()
