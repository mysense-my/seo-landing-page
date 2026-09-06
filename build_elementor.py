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
ASSET_BASE = SITE + "/wp-content/uploads/seo-landing"
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
# All 41 images ship as one folder upload rather than through the media library:
# it is one drag instead of 41, the filenames cannot drift, and nothing depends
# on guessing which /uploads/YYYY/MM/ folder WordPress chose.
# ---------------------------------------------------------------------------
def rewrite(s):
    s = re.sub(r'assets/([A-Za-z0-9._-]+\.(?:jpe?g|png|webp|svg))',
               lambda m: f'{ASSET_BASE}/{m.group(1)}', s)
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
# EVERY scope prefix is `:where(.seo)`, never `.seo`, and that is load-bearing.
# A bare-element rule like `h1{margin:0}` is specificity (0,0,1); rewriting it as
# `.seo h1` makes it (0,1,1), which then BEATS the page's own
# `.hero__title{margin:0 0 20px}` at (0,1,0) and silently flattens the layout.
# `:where(.seo) h1` stays (0,0,1), so the original cascade is preserved exactly
# while still being confined to our markup.
W = f':where(.{SCOPE})'
RESETS = [
    (r'\*,\*::before,\*::after\{box-sizing:border-box\}',
     f'{W},{W} *,{W} *::before,{W} *::after{{box-sizing:border-box}}'),
    (r'\nimg,svg,video\{', f'\n{W} img,{W} svg,{W} video{{'),
    (r'\nbutton\{font:inherit;color:inherit\}', f'\n{W} button{{font:inherit;color:inherit}}'),
    (r'\na\{color:inherit;text-decoration:none\}', f'\n{W} a{{color:inherit;text-decoration:none}}'),
    (r'\nh1,h2,h3,h4,h5\{', f'\n{W} h1,{W} h2,{W} h3,{W} h4,{W} h5{{'),
    (r'\np\{margin:0\}', f'\n{W} p{{margin:0}}'),
    (r'\nhtml\{-webkit-text-size-adjust:100%\}', f'\n.{SCOPE}{{-webkit-text-size-adjust:100%}}'),
]
for pat, rep in RESETS:
    css, n = re.subn(pat, rep, css, count=1)
    if not n:
        raise SystemExit(f"BUILD STOPPED: reset not found, base.css changed shape -> {pat}")

# body -> .seo, MINUS overflow. `overflow-x:clip` on an ancestor makes it a scroll
# container and silently kills position:sticky in its descendants — which this page
# depends on twice (the .plan copy column and the .journey step stack). The page
# gets away with it because the body IS the scroller; a scoped div does not.
_body = re.search(r'\nbody\{(.*?)\n\}', css, re.S)
if not _body:
    raise SystemExit("BUILD STOPPED: body{} rule not found")
# strip CSS comments FIRST: the overflow declaration is preceded by one, and a
# decl that starts with `/*` silently fails a startswith('overflow') test — which
# is exactly how it survived into .seo on the first build
_decls_src = re.sub(r'/\*.*?\*/', '', _body.group(1), flags=re.S)
decls = [d.strip() for d in _decls_src.replace('\n', ' ').split(';') if d.strip()]
dropped = [d for d in decls if d.startswith('overflow')]
decls = [d for d in decls if not d.startswith('overflow')]
if not dropped:
    raise SystemExit("BUILD STOPPED: expected an overflow declaration on body{} to drop")
css = css[:_body.start()] + '\n.' + SCOPE + '{' + ';'.join(decls) + '}' + css[_body.end():]

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

/* The page relies on the document scroller for its own horizontal clipping,
   which the scoped rule above had to give up. Put it back at the one level that
   is guaranteed not to sit above a sticky element. */
.{SCOPE}-clip{{overflow-x:clip}}
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
                         {"_element_id": f"{SCOPE}-engine"}))

slugs = []
for title, markup in sections:
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') or 'section'
    inner = rewrite(markup).strip()
    wrapped = f'<div class="{SCOPE} {SCOPE}-sec {SCOPE}--{slug}">\n{inner}\n</div>'
    content.append(container(
        eid('c-' + slug),
        [html_widget(eid('w-' + slug), wrapped)],
        {"_css_classes": f"{SCOPE}-sec-con", "_element_id": f"{SCOPE}-{slug}"}))
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
                         {"_element_id": f"{SCOPE}-boot"}))


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
print(f"scoped body   : dropped {dropped} (kills position:sticky under a scoped div)")
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
