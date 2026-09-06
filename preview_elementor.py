#!/usr/bin/env python3
"""
Render the generated Elementor template into a standalone HTML page that
reproduces Elementor's real frontend DOM, so the import can be checked BEFORE it
touches the live site.

Elementor wraps our markup in two boxes we do not control:

    .e-con.e-con-full            the container   (flex column, its own padding)
      .elementor-widget-html     the widget      (position:relative)
        .elementor-widget-container
          <div class="seo …">    our section

Every layout rule written as `parent > child` inside a section is unaffected,
but anything relying on the section being a child of <body> is not — which is
exactly what this harness is here to catch.

Writes elementor-preview.html into the scratchpad preview folder and points the
asset URLs back at the local copies so it renders offline.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TPL  = os.path.join(ROOT, 'elementor', 'MYSense-SEO-Landing-template.json')
DEST = sys.argv[1] if len(sys.argv) > 1 else ROOT
# keep in step with ASSET_BASE in build_elementor.py
LIVE_BASE = "https://seo.mysense.com.my/wp-content/uploads/2026/09"

tpl = json.load(open(TPL, encoding='utf-8'))

# Elementor's own frontend rules, trimmed to the ones that can affect our layout,
# PLUS a stand-in for the site's Elementor Kit.
#
# The kit matters more than the container CSS and is easy to forget: on
# seo.mysense.com.my the kit styles bare elements at class-level specificity
# (`.elementor-kit-50 h1{...}` is (0,1,1)), which beats a page's own `.display`
# at (0,1,0) and silently repaints every heading in the theme's font, colour and
# text-transform. A harness without a kit renders perfectly and proves nothing —
# this one deliberately reproduces the hazard, with a loud font and colour so a
# regression is obvious on sight rather than something you have to measure.
# The container padding is likewise left at Elementor's 10px default so the
# build's `:has()` reset has something real to cancel.
ELEMENTOR_CSS = """
.elementor-kit-50 h1,.elementor-kit-50 h2,.elementor-kit-50 h3,
.elementor-kit-50 h4,.elementor-kit-50 h5,.elementor-kit-50 h6{
  font-family:"Nunito Sans",serif;text-transform:capitalize;color:#100739}
.elementor-kit-50 h1{font-size:2.5rem;line-height:1.3;font-weight:600}
.elementor-kit-50 h2{font-size:2rem}
.elementor-kit-50 h3{font-size:1.5rem}
.elementor-kit-50 p{margin-bottom:1.2em;color:#4a4a4a;font-family:"Nunito Sans",serif}
.elementor-kit-50 a{color:#c36;text-decoration:underline}
.elementor-kit-50 ul,.elementor-kit-50 ol{margin:0 0 1.2em 2em;list-style:disc}
.elementor-kit-50 button{font-family:"Nunito Sans",serif;text-transform:uppercase}
.elementor-kit-50{font-family:"Nunito Sans",serif;color:#4a4a4a;line-height:1.7}

*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;padding:0}
body{background:#fff}
.elementor,.elementor *{}
.e-con{
  --container-max-width:1140px;
  --padding-top:10px;--padding-bottom:10px;--padding-left:0px;--padding-right:0px;
  position:relative;display:flex;flex-direction:column;align-items:stretch;
  width:100%;max-width:100%;min-height:0;
  padding:var(--padding-top) var(--padding-right) var(--padding-bottom) var(--padding-left);
}
.e-con-full{--content-width:100%}
.elementor-element{}
.elementor-widget{position:relative;width:100%}
.elementor-widget-container{}
"""

def widgets(el):
    if el['elType'] == 'widget':
        return (f'<div class="elementor-element elementor-element-{el["id"]} '
                f'elementor-widget elementor-widget-{el["widgetType"]}" '
                f'data-element_type="widget" data-widget_type="{el["widgetType"]}.default">'
                f'<div class="elementor-widget-container">{el["settings"]["html"]}</div></div>')
    inner = "".join(widgets(c) for c in el.get('elements', []))
    st = el.get('settings', {})
    eid = st.get('_element_id', '')
    cls = st.get('_css_classes', '')
    return (f'<div class="e-con e-con-full e-flex elementor-element '
            f'elementor-element-{el["id"]} {cls}"'
            + (f' id="{eid}"' if eid else '') +
            f' data-element_type="container">{inner}</div>')

body = "".join(widgets(c) for c in tpl['content'])
# render against the local assets so this works with no network
body = body.replace(LIVE_BASE, 'assets')

page = f"""<!doctype html>
<html lang="en-MY"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Elementor DOM harness — MYSense SEO Landing</title>
<style>{ELEMENTOR_CSS}</style>
</head>
<body class="elementor-page elementor-template-canvas elementor-kit-50">
<div class="elementor elementor-420">{body}</div>
</body></html>"""

out = os.path.join(DEST, 'elementor-preview.html')
open(out, 'w', encoding='utf-8').write(page)
print(f"containers {len(tpl['content'])}  ->  {out}  ({len(page)//1024} KB)")
