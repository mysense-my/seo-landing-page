#!/usr/bin/env python3
"""
Build Elementor import files for the SEO landing page from index.html.

Same shape as the IM landing build: every page section becomes ONE Elementor
container holding ONE HTML widget, so the page stays navigable and reorderable
in the editor and any section can be moved or deleted without touching the rest.

Produces, in ./elementor/ :
  1. MYSense-SEO-Landing-template.json  -> Templates > Saved Templates > Import
  2. MYSense-SEO-Landing.zip            -> Elementor Kit, same shape as a site export
  3. seo-landing-assets.zip             -> the 41 images, for /uploads/seo-landing/
  4. ../paste-sections/*.html           -> one file per section, for hand-building

Target: seo.mysense.com.my, page 420 ("Elementor #420", draft).
"""
import json, os, re, shutil, zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(ROOT, 'elementor')
PASTE = os.path.join(ROOT, 'paste-sections')

PAGE_ID = "420"
SITE    = "https://seo.mysense.com.my"
# All 41 images were uploaded to the media library over the REST API on 6 Sep
# 2026 and every one landed here, verified filename by filename against the
# source bytes. Not guessed — read back from each upload's source_url.
ASSET_BASE = SITE + "/wp-content/uploads/2026/09"
SCOPE   = "seo"                      # every section is wrapped in <div class="seo …">

# The page ships its own header and footer, so it wants Elementor CANVAS — the
# theme's header, footer and page title would otherwise sit around ours and the
# page would carry two of each. (The IM build used elementor_header_footer because
# that site's theme chrome was already off.)
PAGE_TEMPLATE = "elementor_canvas"


def eid(seed):
    """Elementor-style 7-char hex id, deterministic so re-runs are stable."""
    h = 2166136261
    for ch in seed:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return format(h, 'x').rjust(7, '0')[:7]


html = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
css = "\n".join(open(os.path.join(ROOT, 'css', f), encoding='utf-8').read()
                for f in ('base.css', 'hero.css', 'sections.css', 'reveal.css', 'chrome.css'))
motion = open(os.path.join(ROOT, 'js', 'motion.js'), encoding='utf-8').read()


# ---------------------------------------------------------------------------
# 1. Assets
#
# The images live in the media library at /uploads/2026/09/. They were uploaded
# by fetching each one from the GitHub Pages copy inside the logged-in admin page
# and POSTing it to /wp-json/wp/v2/media, so the resulting URLs were read back
# from the API rather than assumed.
# ---------------------------------------------------------------------------
# Filenames whose media-library URL is NOT ASSET_BASE + the local name.
# Currently empty: the page is back on the R-04/R-05 artwork carrying the
# registered mark, which still holds the plain filenames in the library. The
# `-1` copies from the brief revert to the main-site mark are unused.
EXPLICIT = {}


def rewrite(s):
    s = re.sub(r'assets/([A-Za-z0-9._-]+\.(?:jpe?g|png|webp|svg))',
               lambda m: EXPLICIT.get(m.group(1), f'{ASSET_BASE}/{m.group(1)}'), s)
    if 'assets/' in s:
        i = s.index('assets/')
        raise SystemExit("BUILD STOPPED: unresolved 'assets/' path -> " + s[max(0, i-60):i+60])
    return s


# ---------------------------------------------------------------------------
# 2. Scope the stylesheet
#
# The page's resets are written for a document it owns outright. Inside a
# WordPress page they would leak, so the bare-element rules are prefixed with the
# scope class. `:root` custom properties are left global on purpose: definitions
# do not paint anything, and scoping them would break `var()` lookups inside
# Elementor's own wrappers.
# ---------------------------------------------------------------------------
# EVERY selector gets exactly ONE `.seo ` prefix — no more, no less, and never a
# `:where()`. Two separate hazards make this the only correct choice:
#
#   1. The Elementor Kit styles bare elements at CLASS-LEVEL specificity:
#      `.elementor-kit-50 h1{font-family:Nunito Sans;text-transform:capitalize;
#      color:#100739}` is (0,1,1) and beats the page's own `.display` at (0,1,0).
#      Left alone, every heading on the page renders in the theme's font, in
#      Title Case, in the theme's colour.
#   2. Prefixing only SOME selectors inverts the page's own cascade. An earlier
#      build scoped just the bare-element resets, turning `h1{margin:0}` from
#      (0,0,1) into (0,1,1), which then beat `.hero__title{margin:0 0 20px}` and
#      flattened the hero.
#
# One uniform prefix fixes both: every rule moves up by the same (0,1,0), so the
# page's internal cascade is untouched, while `.seo .display` at (0,2,0) clears
# the kit, and `.seo h1` at (0,1,1) ties the kit and wins on source order because
# this <style> sits in the body and the kit's stylesheet is in the head.

def _split_commas(sel):
    """Split a selector list on top-level commas only — :is(a,b) stays intact."""
    parts, depth, buf = [], 0, ''
    for ch in sel:
        if ch in '([': depth += 1
        elif ch in ')]': depth -= 1
        if ch == ',' and depth == 0:
            parts.append(buf); buf = ''
        else:
            buf += ch
    parts.append(buf)
    return [p.strip() for p in parts if p.strip()]


def _split_rules(s):
    """[(header, body|None)] for each top-level rule; nested at-rules keep their body."""
    rules, i, start, depth, header, bstart = [], 0, 0, 0, '', 0
    while i < len(s):
        c = s[i]
        if c == '{':
            if depth == 0:
                header, bstart = s[start:i], i + 1
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                rules.append((header, s[bstart:i])); start = i + 1
        elif c == ';' and depth == 0 and s[start:i].strip().startswith('@'):
            rules.append((s[start:i], None)); start = i + 1
        i += 1
    tail = s[start:].strip()
    if tail:
        rules.append((tail, None))
    return rules


AT_KEYFRAMES = re.compile(r'^\s*@(-\w+-)?keyframes\b', re.I)
AT_NESTED    = re.compile(r'^\s*@(media|supports|container|layer|scope)\b', re.I)
# classes that live on <html>, so the scope has to go AFTER them, not before
HTML_STATE   = re.compile(r'^(html(?:\.[\w-]+)*|\.is-touch)\s+(.+)$')


def scope_selector(sel, scope):
    out = []
    for p in _split_commas(sel):
        if p == ':root':
            out.append(p)
        elif p in ('html', 'body'):
            out.append('.' + scope)
        elif p == '*':
            out.append(f'.{scope},.{scope} *')
        elif p.startswith('*::'):
            out.append(f'.{scope} {p}')
        else:
            m = HTML_STATE.match(p)
            # `.is-touch` is set on <html>, which is ABOVE our wrapper, so
            # `.seo .is-touch x` would never match anything
            out.append(f'{m.group(1)} .{scope} {m.group(2)}' if m else f'.{scope} {p}')
    return ','.join(out)


def scope_css(s, scope):
    out = []
    for header, body in _split_rules(s):
        h = header.strip()
        if body is None:
            out.append(h + (';' if not h.endswith(';') else ''))
        elif AT_KEYFRAMES.match(h):
            out.append(h + '{' + body + '}')            # percentages, not selectors
        elif AT_NESTED.match(h):
            out.append(h + '{' + scope_css(body, scope) + '}')
        elif h.startswith('@'):
            out.append(h + '{' + body + '}')            # @font-face and friends
        else:
            out.append(scope_selector(h, scope) + '{' + body + '}')
    return '\n'.join(out)


# body's overflow has to go BEFORE scoping. `overflow-x:clip` is free on the
# standalone page because the body IS the scroller; on a scoped <div> it makes
# that div a clipping ancestor and kills position:sticky in its descendants —
# which this page needs twice, in the closing CTA copy column and the journey
# step stack. The CSS comment in front of the declaration is stripped first:
# a decl starting with `/*` silently fails a startswith('overflow') test, which
# is exactly how it survived into .seo on the first build.
_body = re.search(r'\nbody\{(.*?)\n\}', css, re.S)
if not _body:
    raise SystemExit("BUILD STOPPED: body{} rule not found")
_decls_src = re.sub(r'/\*.*?\*/', '', _body.group(1), flags=re.S)
decls = [d.strip() for d in _decls_src.replace('\n', ' ').split(';') if d.strip()]
dropped = [d for d in decls if d.startswith('overflow')]
decls = [d for d in decls if not d.startswith('overflow')]
if not dropped:
    raise SystemExit("BUILD STOPPED: expected an overflow declaration on body{} to drop")
css = css[:_body.start()] + '\nbody{' + ';'.join(decls) + '}' + css[_body.end():]

# Comments MUST go before scoping. The selector splitter is not comment-aware, so
# a `/* … */` block reads as a selector and every comma inside it reads as a
# selector separator — which silently shredded the whole stylesheet on the first
# attempt (`.display{` survived exactly once, and half the page lost its styling).
css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
css = scope_css(css, SCOPE)

# ---------------------------------------------------------------------------
# Shield our background images from Elementor's container lazy-loading.
#
# Elementor ships this, inline in the head:
#   .e-con.e-parent:nth-of-type(n+4):not(.e-lazyloaded):not(.e-no-lazyload),
#   .e-con.e-parent:nth-of-type(n+4):not(.e-lazyloaded):not(.e-no-lazyload) *
#     { background-image: none !important }
# From the FOURTH container onward it blanks every background image inside,
# descendants included, until its own observer adds `.e-lazyloaded` on scroll.
# On this page that wiped 14 of 17 sections' gradients on load — the hero glows,
# the awards plaque, the comparison column, the slat scrims and the problem
# cards' navy sheet. With the sheet gone an opened card showed its photograph
# under `filter:saturate(.55)` instead, which is the washed-out beige blob.
#
# `e-no-lazyload` is added to every container too, but Elementor's importer
# drops container classes so that only lands once the restore script runs. This
# is the belt: the same declarations re-stated with `!important` at a
# specificity that outranks Elementor's (0,5,0) selector, so the gradients are
# never suppressed even for one frame.
# ---------------------------------------------------------------------------
BOOST = '.' + '.'.join([SCOPE] * 5)          # (0,5,0) before the element's own class

def shield(scoped):
    out, n = [], 0
    for header, body in _split_rules(scoped):
        h = header.strip()
        if body is None or AT_KEYFRAMES.match(h):
            continue
        if AT_NESTED.match(h):
            inner = shield(body)
            if inner:
                out.append(h + '{' + inner + '}')
            continue
        if h.startswith('@'):
            continue
        decls = [d.strip() for d in body.split(';')
                 if re.match(r'background(-image)?\s*:', d.strip())
                 and re.search(r'gradient|url\(', d)]
        if not decls:
            continue
        sel = ','.join(p.replace('.' + SCOPE, BOOST, 1) if p.strip().startswith('.' + SCOPE) else p
                       for p in _split_commas(h))
        out.append(sel + '{' + ';'.join(d + ' !important' for d in decls) + '}')
        n += 1
    return '\n'.join(out)

_shield = shield(css)
_shield_count = _shield.count('!important')
if _shield_count < 15:
    raise SystemExit(f"BUILD STOPPED: lazy-load shield only caught {_shield_count} "
                     "background declarations, expected 18+")
css += ("\n\n/* ---- shield against Elementor container lazy-loading (see build script) ---- */\n"
        + _shield + "\n")
print(f"lazy shield   : {_shield_count} background declarations protected")

# ---------------------------------------------------------------------------
# Hold our own button styling through :hover / :focus / :active.
#
# The kit styles BARE <button> in every interaction state:
#   .elementor-kit-50 button:hover, .elementor-kit-50 button:focus
#     { background-color: var(--e-global-color-secondary);   /* #FFC670 */
#       border-radius: 100px }
# That is (0,2,1) and beats any of our component rules at (0,2,0). The page's
# problem cards and offer slats are opened by an invisible full-card <button>
# (.pcard__hit / .slat__hit at z-index 5 and 4), so TAPPING one focused it and
# the kit painted a #FFC670 rounded rectangle straight over the card's text —
# the "yellow blob". It never showed in testing because `element.click()` does
# not move focus; only a real tap or click does.
#
# So every rule of ours that targets a <button> class is re-emitted with the
# interaction states appended, which lands at (0,3,0) and holds. The button
# classes are read out of the markup rather than hard-coded, so a new button
# picks this up automatically.
# ---------------------------------------------------------------------------
BUTTON_CLASSES = sorted({c for m in re.finditer(r'<button[^>]*class="([^"]+)"', html)
                         for c in m.group(1).split()})
STATES = (':hover', ':focus', ':focus-visible', ':active')

def button_state_guard(scoped):
    out, n = [], 0
    for header, body in _split_rules(scoped):
        h = header.strip()
        if body is None or h.startswith('@'):
            if body is not None and AT_NESTED.match(h):
                inner = button_state_guard(body)
                if inner:
                    out.append(h + '{' + inner + '}')
            continue
        parts = _split_commas(h)
        # only plain rules that end on one of our button classes, and that do
        # not already carry a pseudo-class of their own
        hits = [p for p in parts
                if any(p.rstrip().endswith('.' + c) for c in BUTTON_CLASSES) and ':' not in p]
        if not hits:
            continue
        sel = ','.join(p + st for p in hits for st in STATES)
        out.append(sel + '{' + body.strip() + '}')
        n += 1
    return '\n'.join(out)

_guard = button_state_guard(css)
if not _guard or 'pcard__hit:focus' not in _guard:
    raise SystemExit("BUILD STOPPED: button state guard did not cover .pcard__hit")
css += ("\n\n/* ---- hold button styling through hover/focus/active (see build script) ---- */\n"
        + _guard + "\n")
print(f"button guard  : {len(BUTTON_CLASSES)} button classes -> {_guard.count('{')} state rules")

# ---------------------------------------------------------------------------
# Custom-property collision guard.
#
# Elementor's containers define their own custom properties ON `.e-con`, which
# cascades into every section wrapper inside it. Any token of ours sharing a
# name is silently reassigned: `--display` cost a round trip when
# `font-family:var(--display)` started resolving to the word "flex" and every
# heading fell back to the browser default. A name clash produces no error and
# no warning, so it is asserted here instead.
# ---------------------------------------------------------------------------
ELEMENTOR_VARS = {
    'display', 'flex-direction', 'flex-wrap', 'flex-basis', 'flex-grow', 'flex-shrink',
    'justify-content', 'align-items', 'align-content', 'align-self', 'order', 'gap',
    'row-gap', 'column-gap', 'width', 'height', 'min-height', 'max-height', 'content-width',
    'overflow', 'position', 'z-index', 'text-align', 'container-widget-width',
    'container-widget-height', 'container-widget-flex-grow', 'container-widget-align-self',
    'container-max-width', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
    'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
    'padding-block-start', 'padding-block-end', 'padding-inline-start', 'padding-inline-end',
    'border-radius', 'border-width', 'border-style', 'border-color',
}
ours = {m.group(1) for m in re.finditer(r'(?m)^\s*--([a-z0-9-]+)\s*:', css)}
clash = sorted(ours & ELEMENTOR_VARS)
if clash:
    raise SystemExit(
        "BUILD STOPPED: custom properties collide with Elementor container variables -> "
        + ", ".join('--' + c for c in clash)
        + "\n  Elementor sets these on .e-con and they cascade into every section wrapper.\n"
          "  Rename the token in css/ (e.g. --display -> --ff-display).")
print(f"token guard   : {len(ours)} custom properties, no collisions")

# The scoping is the single most fragile step in this build, so it is asserted
# rather than trusted: a stylesheet that silently loses its rules still produces
# a template that imports cleanly and looks wrong only in the browser.
for must in ('.seo .display{', '.seo .hero__title', '.seo .h2{', '.seo .btn{',
             '.seo .serp' if '.serp' in css else '.seo .res__t', '.seo .site-menu{'):
    if must not in css:
        raise SystemExit(f"BUILD STOPPED: scoping lost a rule -> {must}")
if re.search(r'(^|\n)\s*\.seo\s*/\*', css):
    raise SystemExit("BUILD STOPPED: a comment was scoped as a selector")

css = rewrite(css)
motion = rewrite(motion)

# ---------------------------------------------------------------------------
# 3. Host compatibility
# ---------------------------------------------------------------------------
css += f"""

/* ---------- Elementor host compatibility ----------
   Two different jobs here, and they need OPPOSITE specificity.

   These first rules must BEAT Elementor's own defaults, so they are written
   plainly. They only ever target Elementor's classes, which the page's own
   stylesheet never styles, so there is nothing of ours for them to outrank.
   (Wrapping these in :where() was the first build's bug: at zero specificity
   the padding reset lost to Elementor's `.e-con` and every section sat in a
   10px band of page background.) */

/* Elementor containers carry their own padding and min-height. The page's
   sections bring all their own spacing, so container padding shows up as a
   stripe of the wrong colour between two sections. */
.e-con:has(> .elementor-widget-html .{SCOPE}){{padding:0;min-height:0}}
/* the engine and boot containers hold only a <style> and a <script>, so they
   must take up no room at all. A display:none ancestor does not stop a
   stylesheet applying or a script executing. */
.e-con:has(#{SCOPE}-css),.e-con:has(#{SCOPE}-js){{display:none}}

/* The widget wrapper sits between the container and our markup and would break
   every parent>child rule in the page, so it is collapsed out of the box tree. */
.elementor-widget-html:has(> .elementor-widget-container > .{SCOPE}),
.elementor-widget-html:has(> .elementor-widget-container > .{SCOPE}) > .elementor-widget-container{{
  display:contents}}

/* Nothing above a sticky element may create a scroll container, or the sticky
   silently stops working. This page has two: the .plan copy column and the
   .journey step stack. */
.e-con:has(.{SCOPE}),.e-con:has(.{SCOPE}) .e-con-inner,
.elementor-widget-html:has(.{SCOPE}),
.elementor-widget-html:has(.{SCOPE}) > .elementor-widget-container{{overflow:visible}}

/* Give inheritance back. The page colours most text by setting `color` on a
   SECTION and letting it inherit down — but inheritance only applies when no
   rule matches the element itself, and the kit matches every heading and
   paragraph directly (`.elementor-kit-50 h1{{color:#100739}}`). That silently
   beats the inherited white and paints the hero headline near-black. These sit
   at (0,1,1), the same weight as the kit's rules, and win on source order
   because this <style> is in the body; anything the page colours explicitly is
   at (0,2,0) or more and still wins over both. */
.{SCOPE} h1,.{SCOPE} h2,.{SCOPE} h3,.{SCOPE} h4,.{SCOPE} h5,.{SCOPE} h6,
.{SCOPE} p,.{SCOPE} li,.{SCOPE} dt,.{SCOPE} dd,.{SCOPE} b,.{SCOPE} strong,
.{SCOPE} em,.{SCOPE} i,.{SCOPE} span,.{SCOPE} small,.{SCOPE} label{{color:inherit}}

/* Same problem, same cause, for the typeface. The kit sets a font on bare `p`,
   so body copy stopped inheriting Manrope and silently rendered in the theme's
   face — same width, different metrics, so paragraphs re-wrapped and three
   sections came out ~22px short. Headings are deliberately NOT in this list:
   the page sets their face itself at the same weight, and `font-family:inherit`
   here would land later in the file and beat it, dropping every heading to the
   body font. */
.{SCOPE} p,.{SCOPE} li,.{SCOPE} dt,.{SCOPE} dd,.{SCOPE} b,.{SCOPE} strong,
.{SCOPE} em,.{SCOPE} i,.{SCOPE} span,.{SCOPE} small,.{SCOPE} label,.{SCOPE} a,
.{SCOPE} button,.{SCOPE} input,.{SCOPE} select,.{SCOPE} textarea{{
  font-family:inherit;text-transform:inherit;letter-spacing:inherit;line-height:inherit}}

/* From here down the rules touch OUR elements, so they are wrapped in :where()
   to contribute zero specificity and never outrank the page's own stylesheet. */

/* Undo the theme's own element defaults (Hello Elementor sets margins on
   headings, paragraphs and lists). These sit at exactly (0,0,1) — the same
   weight as the theme rules they replace, winning only on source order — so
   they can never outrank a class in the page's own stylesheet. */
:where(.{SCOPE}) h1,:where(.{SCOPE}) h2,:where(.{SCOPE}) h3,
:where(.{SCOPE}) h4,:where(.{SCOPE}) h5,:where(.{SCOPE}) h6,
:where(.{SCOPE}) p,:where(.{SCOPE}) ul,:where(.{SCOPE}) ol,
:where(.{SCOPE}) li,:where(.{SCOPE}) figure,:where(.{SCOPE}) dl,
:where(.{SCOPE}) dd,:where(.{SCOPE}) dt{{margin:0;padding:0}}
:where(.{SCOPE}) ul,:where(.{SCOPE}) ol{{list-style:none}}
:where(.{SCOPE}) a{{text-decoration:none;box-shadow:none}}
:where(.{SCOPE}) button,:where(.{SCOPE}) input,:where(.{SCOPE}) select,
:where(.{SCOPE}) textarea{{font-family:inherit}}
:where(.{SCOPE}) img{{height:auto;border-radius:0}}

/* THE SECTION WRAPPER MUST BE PINNED TO ITS CONTAINER'S WIDTH.
   Elementor's real containers compute `align-items:normal`, not `stretch`, and
   under that our block-level wrapper sized itself to its widest CONTENT instead
   of to the container. The logo marquee is `width:max-content`, so on a phone
   the wrapper became 3648px against a 390px viewport, the document overflowed
   ~9x, and mobile browsers zoomed out to fit. That in turn broke the menu:
   `position:fixed;inset:0` resolves against the VISUAL viewport, so the panel
   rendered 4x oversized and its Close button, contact block and CTA all fell
   off the bottom of the screen. One symptom, two layers away from its cause.

   The width pinning is the WHOLE fix, and no `overflow-x:clip` is needed here:
   `.brands`, `.reviews` and `.band` each carry their own `overflow:hidden`, so
   once the wrapper is pinned to the container width those sections are
   viewport-width and clip their own marquees. Verified at 320-1440: zero
   document overflow without any clip on the wrapper.

   A note for whoever measures this next. A clip WAS briefly added here and then
   removed because sticky looked broken on the live page. That reading was
   wrong: the live site has smooth scrolling, so `scrollTo` animates and any
   sample taken a few hundred ms later is read mid-flight. Measured properly —
   smooth scrolling forced off, page settled first, the column's viewport top
   sampled across its whole pinning range — sticky holds at exactly its 120px
   offset on the live page, spread 0, identical to the standalone build. Kill
   `scroll-behavior` before asserting anything about scroll position. */
.{SCOPE}{{width:100%;max-width:100%;min-width:0}}
"""

# ---------------------------------------------------------------------------
# 4. Split the page into sections
#
# Markers look like `<!-- ==== 5. THE COMPARISON ==== -->`, sometimes with a
# multi-line note under the title. A comment whose first line is nothing but `=`
# (the copy-policy block) is NOT a marker, so the title must contain a letter.
# ---------------------------------------------------------------------------
COMMENT = re.compile(r'<!--(.*?)-->', re.S)
TITLE   = re.compile(r'^=+\s*([^=]*[A-Za-z][^=]*?)\s*=+$')

body = html.split('<body>', 1)[1].split('<script src="js/motion.js', 1)[0]

marks = []                                    # [(start, end, title)]
for m in COMMENT.finditer(body):
    first = m.group(1).lstrip('\n').split('\n', 1)[0].strip()
    t = TITLE.match(first)
    if t:
        marks.append((m.start(), m.end(), t.group(1).strip()))

sections = []                                 # [(title, markup)]
head = body[:marks[0][0]].strip() if marks else body
if re.sub(r'<!--.*?-->', '', head, flags=re.S).strip():
    sections.append(('00 Header', head))
for i, (s, e, title) in enumerate(marks):
    end = marks[i + 1][0] if i + 1 < len(marks) else len(body)
    chunk = body[e:end].strip()
    if re.sub(r'<!--.*?-->', '', chunk, flags=re.S).strip():
        sections.append((title, chunk))


# ---------------------------------------------------------------------------
# 5. Elementor element builders
# ---------------------------------------------------------------------------
def container(cid, children, extra=None):
    st = {
        "content_width": "full",
        "padding": {"unit": "px", "top": "0", "right": "0", "bottom": "0", "left": "0", "isLinked": True},
        "margin":  {"unit": "px", "top": "0", "right": "0", "bottom": "0", "left": "0", "isLinked": True},
        "flex_gap": {"column": "0", "row": "0", "isLinked": True, "unit": "px", "size": 0},
        "min_height": {"unit": "px", "size": 0},
    }
    if extra:
        st.update(extra)
    return {"id": cid, "settings": st, "elements": children, "isInner": False, "elType": "container"}


def html_widget(wid, markup):
    return {"id": wid, "settings": {"html": markup},
            "elements": [], "isInner": False, "widgetType": "html", "elType": "widget"}


content = []

# --- engine: fonts + the whole stylesheet, once, before anything renders ---
engine = (
 '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
 '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
 '<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800;900'
 '&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet">\n'
 f'<style id="{SCOPE}-css">\n' + css + '\n</style>\n'
)
content.append(container(eid('engine'), [html_widget(eid('engine-w'), engine)],
                         {"_css_classes": "e-no-lazyload",
                          "_element_id": f"{SCOPE}-engine"}))

slugs = []
for title, markup in sections:
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') or 'section'
    inner = rewrite(markup).strip()
    wrapped = f'<div class="{SCOPE} {SCOPE}-sec {SCOPE}--{slug}">\n{inner}\n</div>'
    content.append(container(
        eid('c-' + slug),
        [html_widget(eid('w-' + slug), wrapped)],
        {"_css_classes": f"{SCOPE}-sec-con e-no-lazyload",
         "_element_id": f"{SCOPE}-{slug}"}))
    slugs.append((title, slug, len(wrapped)))

# --- boot: the motion engine, after every section exists in the DOM ---
# Elementor re-renders widgets over AJAX in the editor, where DOMContentLoaded
# has long since fired, so the engine is also re-run on Elementor's own hook.
boot = (
 f'<script id="{SCOPE}-js">\n' + motion + '\n</script>\n'
 f'<script id="{SCOPE}-boot">(function(){{'
 'if(window.elementorFrontend&&window.elementorFrontend.hooks){'
 'try{window.elementorFrontend.hooks.addAction("frontend/element_ready/global",function(){});}catch(e){}}'
 '})();</script>'
)
content.append(container(eid('boot'), [html_widget(eid('boot-w'), boot)],
                         {"_css_classes": "e-no-lazyload",
                          "_element_id": f"{SCOPE}-boot"}))


# ---------------------------------------------------------------------------
# 6. Class restore
#
# Elementor's importer DROPS _css_classes on CONTAINERS while keeping them on
# widgets — verified on the IM build, where every container class vanished and
# every element id survived. Container ids do survive, so the classes are
# re-applied at parse time, keyed by id.
# ---------------------------------------------------------------------------
CLASS_MAP = {}
for c in content:
    st = c['settings']
    cls = st.get('_css_classes', '').strip()
    if cls:
        CLASS_MAP[st['_element_id']] = cls

restore = (
 f'<script id="{SCOPE}-classes">(function(){{var M=' +
 json.dumps(CLASS_MAP, separators=(',', ':')) + ';'
 'function a(){for(var k in M){var el=document.getElementById(k);'
 f'if(el&&!el.getAttribute("data-{SCOPE}")){{el.className+=" "+M[k];'
 f'el.setAttribute("data-{SCOPE}","1");}}}}}}'
 'a();try{new MutationObserver(a).observe(document.documentElement,{childList:true,subtree:true});}'
 'catch(e){}document.addEventListener("DOMContentLoaded",a);})();</script>'
)
content[0]['elements'][0]['settings']['html'] += '\n' + restore


# ---------------------------------------------------------------------------
# 7. Outputs
# ---------------------------------------------------------------------------
os.makedirs(OUT, exist_ok=True)

# --- 7a. paste-sections: one file per section, for building it by hand ---
shutil.rmtree(PASTE, ignore_errors=True)
os.makedirs(PASTE, exist_ok=True)
open(os.path.join(PASTE, '00-engine.html'), 'w', encoding='utf-8').write(engine)
for n, (title, slug, _) in enumerate(slugs, start=1):
    inner = rewrite(dict(sections)[title]).strip()
    open(os.path.join(PASTE, f'{n:02d}-{slug}.html'), 'w', encoding='utf-8').write(
        f'<div class="{SCOPE} {SCOPE}-sec {SCOPE}--{slug}">\n{inner}\n</div>')
open(os.path.join(PASTE, f'{len(slugs)+1:02d}-boot.html'), 'w', encoding='utf-8').write(boot)

# --- 7b. template json ---
tpl = {"content": content, "page_settings": {"template": PAGE_TEMPLATE},
       "version": "0.4", "title": "MYSense SEO Landing", "type": "page"}
tpath = os.path.join(OUT, 'MYSense-SEO-Landing-template.json')
json.dump(tpl, open(tpath, 'w', encoding='utf-8'), ensure_ascii=False)

# --- 7c. kit zip ---
kit = os.path.join(OUT, '_kit')
shutil.rmtree(kit, ignore_errors=True)
os.makedirs(os.path.join(kit, 'content', 'page'), exist_ok=True)
json.dump({"content": content, "settings": {"template": PAGE_TEMPLATE}, "metadata": []},
          open(os.path.join(kit, 'content', 'page', f'{PAGE_ID}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False)
json.dump({"content": [], "metadata": [],
           "settings": {"template": "default", "default_page_template": PAGE_TEMPLATE,
                        "viewport_md": 768, "viewport_lg": 1025}},
          open(os.path.join(kit, 'site-settings.json'), 'w', encoding='utf-8'), ensure_ascii=False)
json.dump({"name": "mysense-seo-landing", "title": "MYSense SEO Landing",
           "description": "SEO Agency Malaysia landing page", "author": "MYSense",
           "version": "1.0", "elementor_version": "3.27.6",
           "created": "2026-09-06 12:00:00", "thumbnail": False, "site": SITE,
           "theme": {"name": "Hello Elementor", "slug": "hello-elementor",
                     "version": "3.4.9", "theme_uri": "https://elementor.com/hello-theme/"},
           "site-settings": {"theme": False, "globalColors": False, "globalFonts": False,
                             "themeStyleSettings": False, "generalSettings": True,
                             "experiments": False, "customCode": False,
                             "customIcons": False, "customFonts": False},
           "plugins": [{"name": "Elementor", "plugin": "elementor/elementor",
                        "pluginUri": "https://elementor.com/", "version": "3.27.6"}],
           "templates": [], "taxonomies": [],
           "content": {"page": {PAGE_ID: {"title": "SEO Landing Page", "excerpt": "",
                                          "doc_type": "wp-page", "thumbnail": False,
                                          "url": f"{SITE}/", "terms": []}}},
           "wp-content": {"page": []}},
          open(os.path.join(kit, 'manifest.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
zpath = os.path.join(OUT, 'MYSense-SEO-Landing.zip')
with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
    for base, _, files in os.walk(kit):
        for f in files:
            full = os.path.join(base, f)
            z.write(full, os.path.relpath(full, kit))
shutil.rmtree(kit, ignore_errors=True)

# --- 7d. assets zip, for /wp-content/uploads/seo-landing/ ---
used = sorted(set(re.findall(r'assets/([A-Za-z0-9._-]+\.(?:jpe?g|png|webp|svg))',
                             html + open(os.path.join(ROOT, 'css', 'sections.css'),
                                         encoding='utf-8').read())))
apath = os.path.join(OUT, 'seo-landing-assets.zip')
missing = []
with zipfile.ZipFile(apath, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in used:
        src = os.path.join(ROOT, 'assets', f)
        if os.path.exists(src):
            z.write(src, f'seo-landing/{f}')
        else:
            missing.append(f)

# ---------------------------------------------------------------------------
print(f"scoped body   : {dropped} moved off body, re-applied on the .{SCOPE} wrapper")
print(f"sections      : {len(sections)}")
for t, s, n in slugs:
    print(f"   {s:<34} {n/1024:6.1f} KB")
print(f"containers    : {len(content)}  (engine + {len(slugs)} sections + boot)")
print(f"class restore : {len(CLASS_MAP)} containers")
print(f"assets        : {len(used)} files" + (f"  MISSING {missing}" if missing else ""))
print(f"template json : {os.path.getsize(tpath)//1024} KB -> {tpath}")
print(f"kit zip       : {os.path.getsize(zpath)//1024} KB -> {zpath}")
print(f"assets zip    : {os.path.getsize(apath)//1024} KB -> {apath}")
print(f"paste files   : {len(slugs)+2} -> {PASTE}")
