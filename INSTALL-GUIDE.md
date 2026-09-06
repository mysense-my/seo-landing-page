# MYSense SEO Landing — Elementor install

Target: **seo.mysense.com.my**, page **420** (currently the empty draft "Elementor #420").

Built against what the site actually runs, checked over HTTP on 6 Sep 2026:
WordPress 7.0.4, **Elementor 3.27.6**, Hello Elementor, CSS print method `external`,
`e_element_cache` on.

Structure is the same as the IM and DM landings: **one container per section, one
HTML widget inside each**, so every section can be reordered, hidden or deleted in
the editor without touching the others.

```
container  seo-engine            <style> — the whole stylesheet, display:none
container  seo-00-header         header
container  seo-1-hero            hero + search results stage
container  seo-2-trusted-by…     logo rails + awards plaque
container  seo-3-track-record    the four counters
container  seo-4-the-problem…    three hover cards
container  seo-5-the-comparison  the comparison table
container  seo-6-what-mysense…   six expanding slats
container  seo-7-case-studies    Klinik Suzana + Baagus
container  seo-8-the-mysense…    the five-step journey
container  seo-9-why-choose…     three cards
container  seo-10-reviews        two review rails
container  seo-11-faq            six-question accordion
container  seo-12-final-cta-form closing CTA + HubSpot form
container  seo-multi-discipl…    the yellow sign-off marquee
container  seo-footer            footer
container  seo-boot              <script> — the motion engine, display:none
```

17 containers, 17 HTML widgets.

---

## Already done on seo.mysense.com.my (6 Sep 2026)

Steps 1–3 below have been **carried out on the live site**; they are recorded here
for a rebuild or a second environment.

- All 41 images are in the media library at `/wp-content/uploads/2026/09/`.
- The template is in **Templates → Saved Templates** as *MYSense SEO Landing*
  (id 471). A duplicate from a double-submit was moved to Trash.
- Page **420** holds the 17 containers and is set to **Elementor Canvas**.
- The page is still a **DRAFT**. Nothing has been published.

Two things worth knowing about what is on the server:

1. Five images collided with an earlier upload attempt and WordPress appended
   `-1` to them (`svc-onpage-1.jpg`, `svc-reporting-1.jpg`, `why-data-1.jpg`,
   `why-expertise-1.jpg`, `why-tailored-1.jpg`). The originals are correct and
   byte-identical to source, and the page uses the clean names. The five `-1`
   copies are unused duplicates and can be binned.
2. The images were uploaded by fetching each one from the GitHub Pages copy
   inside the logged-in admin page and POSTing it to `/wp-json/wp/v2/media`, so
   the URLs baked into the template were read back from the API rather than
   guessed.

---

## Step 1 — upload the images

`elementor/seo-landing-assets.zip` holds all 41 images. Either unzip it into
`/wp-content/uploads/seo-landing/` **or** drag all 41 into the Media Library.
Whichever you choose, `ASSET_BASE` at the top of `build_elementor.py` must match,
and the build bakes that base into every image URL.

Watch for WordPress appending `-1` to any filename that collides with something
already in the library — if an image is missing, that is why.

## Step 2 — import the template

1. **Templates → Saved Templates → Import Templates**
2. Upload `elementor/MYSense-SEO-Landing-template.json`
3. Open the page in Elementor
4. Folder icon (Add Template) → **My Templates** → insert **MYSense SEO Landing**

The import posts to `admin-ajax.php` and then redirects, so the list can look
unchanged for a few seconds. **Reload the Saved Templates list before importing
again** — submitting twice is what produced the duplicate on this site.

## Step 3 — set the page layout to Canvas

This page ships its **own header and footer**, so the theme's must be off or you
get two of each.

**Elementor → Page Settings (gear, bottom-left) → Page Layout → Elementor Canvas**

The template file asks for canvas, but Elementor only applies `page_settings`
when a template is imported *as a page*; inserting it into an existing page does
not carry them over. So set it by hand.

## Step 4 — check it

On the published page, in the browser console:

```js
document.querySelectorAll('.seo-sec').length        // 15
document.querySelectorAll('[data-seo]').length      // 15  (container classes restored)
document.querySelectorAll('[data-reveal].is-in').length  // grows as you scroll, ends 47
```

Then scroll the whole page once and confirm: the logo rails and review rails drift,
the four counters count up, the journey line fills, the hero query retypes and swaps
its results, and the closing CTA's copy column pins while the form scrolls past it.

---

## What the build does to the page, and why

**`overflow-x:clip` is dropped from the scoped body rule.** On the standalone page
the body is the scroller, so clipping there is free. Inside a scoped `<div>` it
would make that div a clipping ancestor and kill `position:sticky` in its
descendants — which this page depends on twice, in the closing CTA's copy column
and the journey step stack.

**Container padding is zeroed by a `:has()` rule, not by `:where()`.** Elementor's
own `.e-con` padding is (0,1,0); a `:where()` version at (0,0,0) loses to it and
every section sits in a 10px stripe of the wrong background colour.

**Container CSS classes are re-applied by a small script in the engine widget.**
Elementor's importer drops `_css_classes` on containers while keeping them on
widgets, and keeps element ids on both — so the classes are restored at parse time,
keyed by id. Same fix the IM build needed.

**`--display` is called `--ff-display`.** Elementor defines `--display:flex` on
`.e-con`, and it cascades into every section wrapper inside it. With the original
name, every `font-family:var(--display)` inside a container resolved to the word
`flex` and each heading fell back to the browser default — no error, no warning.
The build now fails outright if any of the page's 45 custom properties collides
with an Elementor container variable.

**The stylesheet is scoped, and the scoping is asserted.** Every selector gets
exactly one `.seo ` prefix. Uniformity is the point: the whole sheet moves up by
the same (0,1,0), so the page's internal cascade is untouched, while
`.seo .display` at (0,2,0) clears the kit. Comments are stripped first — the
selector splitter is not comment-aware, and a `/* … */` block parsed as a
selector silently shredded the stylesheet on the first attempt. The build checks
for a handful of rules by name afterwards and stops rather than shipping a sheet
that quietly lost half its rules.

**Colour and font-family are handed back to inheritance on text elements.** The
page colours text by setting `color` on a section and letting it inherit, but
inheritance only applies when nothing matches the element itself — and the kit
matches every `p` and heading directly. That painted the hero headline near-black
and re-wrapped body copy in the theme's face. Headings are excluded from the
`font-family:inherit` rule on purpose: the page sets their face itself at the
same weight, and the compat rule would land later in the file and beat it.

---

## Verified before hand-off

The generated template was rendered into a harness reproducing Elementor's real
frontend DOM (`.e-con.e-con-full` → `.elementor-widget-html` →
`.elementor-widget-container` → our section) and compared against the standalone
page at `localhost:9538`:

- All **16 sections identical** in height, width, background and padding.
- Total document height **13982px on both**, to the pixel.
- Full-page pixel diff: **0.26% of pixels differ, and every differing band is a
  marquee** — the logo rails, the review rails and the yellow sign-off band, all
  caught mid-scroll at a different phase. No layout differences anywhere.
- Zero console errors. No horizontal overflow at 390, 768, 1024, 1280, 1440, 1600.
- `position:sticky` still pins under the Elementor wrappers, with no clipping
  ancestor above it.
- All 47 reveals fire, the four counters reach their targets, the journey track
  fills to 1.0 with all five steps done, the comparison table reveals all five rows.
- Accordion opens with correct `aria-expanded` and single-open behaviour, hover
  cards open, slats switch, the mobile menu opens and closes with the scroll lock
  applied and released.

## Rebuilding

```bash
python3 build_elementor.py                    # regenerate everything
python3 preview_elementor.py <preview-dir>    # render the Elementor DOM harness
```

`build_elementor.py` stops the build rather than shipping something wrong if
`base.css` changes shape — if a reset it rewrites is renamed or the `body{}` rule
loses its `overflow` declaration, it raises instead of silently producing a page
with the wrong cascade.
