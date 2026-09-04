# MYSense SEO landing page

A standalone landing page for `seo.mysense.com.my`, built as the third sibling of
the digital-marketing landing and the influencer-marketing landing. Same type system, same component grammar, same motion engine, same header
and footer. Different lead colour, so the three read as one family without looking
like the same page three times.

```
DM landing   purple lead
IM landing   pink lead
SEO landing  navy -> blue -> cyan lead, yellow as the action colour, pink as accent
```

## Run it

Serve the folder with anything static:

```bash
python3 -m http.server 9538
```

There is no build step and no dependency. Open `index.html`.

## Files

```
index.html            one page, twelve sections plus header and footer
css/base.css          tokens, type scale, buttons, pills, motion primitives
css/hero.css          the search stage
css/sections.css      brands, numbers, cases, journey, why-us, reviews, FAQ, form
css/reveal.css        the three signature mechanics (problem cards, table, slats)
css/chrome.css        header, the full-screen mobile menu, footer
js/motion.js          the whole motion system, no dependencies
assets/               23 client logos, 2 MYSense logos, 2 award marks, 14 image slots
```

## Section order

| # | id | Ground | What it does |
|---|---|---|---|
| 1 | `#top` | navy → cyan | Hero. The search results stage. |
| 2 | `#brands` | page | Trusted by 300+ brands, two logo rails, the awards plaque, the credentials strip. |
| 3 | `#numbers` | navy → cyan | Four count-up figures. |
| 4 | `#problem` | page | The problem, as three title-first hover cards. |
| 5 | `#method` | navy | The comparison table. |
| 6 | `#services` | page | What MYSense SEO offers, as six expanding slats. |
| 7 | `#work` | page | Two case studies. |
| 8 | `#process` | ink | The five-step journey with a scroll-filled rail. |
| 9 | `#why` | page | Why choose MYSense, three bubble-masked cards. |
| 10 | `#reviews` | white | Two counter-drifting rails of Google reviews. |
| 11 | `#faq` | page | Five questions, accordion. On the light ground on purpose: it is the one section people read word for word, and on dark it also sat against the dark closing CTA. |
| 12 | `#plan` | navy → cyan | Closing CTA and the form. |
| 13 | `.band` | **yellow** | The sign-off marquee. The page's one large yellow field, ink label at 11.91:1. Neither sibling page has one. |

## The four signature moments

**The hero search stage.** A search results page. A query types itself through six
Malaysian searches and the whole set under it changes with the query: the result
count and all three results, with the query terms bolded in each snippet the way a
results page bolds what it matched. The visitor's own site is always the first
result.

It went through two rejected versions, and both failures were the same failure.
The first typed six different queries over one fixed set of generic rows, so the
results never answered the query. The second fixed that but kept rank badges, a
"your brand" legend and a highlighted card for the visitor's row — and a column of
equal bordered boxes under a query field is the shape of a **form**, whatever the
text inside it says. What finally worked was removing the diagram: no rank badges,
no legend, no highlight, no boxes. Results are plain text of natural heights on a
white page, and the visitor's site is identified by its own domain and by being
first.

The layout convention — query field with its tools, result tabs, count, then
favicon + site name + URL + link-coloured title + snippet — is the universal one. No search engine's logo, wordmark or brand colours are reproduced
anywhere in it, which matters because this is a commercial page.

**Problem cards.** At rest, a photograph with the title across the bottom. On
hover a navy sheet wipes up over the picture with `clip-path` and the body copy
expands into it.

**The comparison table.** Rows reveal in sequence at a 90ms stagger. Hovering a
row drops every other row to 40% and sweeps a light band across the MYSense cell.
The MYSense column is lit and the usual-approach column is recessed, because the
panel clips its own overflow and a genuinely raised slab would have to break out
of it. Below 860px the three columns become five stacked comparison cards.

**Offer slats.** Six panels; the open one takes space from its neighbours. A
closed panel is only about 130px wide, so its title runs up the left edge as a
vertical spine. That is the only reason six panels fit in one row at all. Below
1025px the spine goes away and the whole thing becomes a tap accordion.

## The mobile menu

Below 1025px the nav and the header CTA are replaced by a full-screen panel,
carried over from the influencer landing page's `.sitebar__menu` so the three
siblings share one chrome. It is a fixed navy sheet that floods open on a
`clip-path` circle grown from the burger, with oversized uppercase links that
stagger in, contact details in the foot and the CTA on a hairline at the bottom.
The IM page's `--ms-navy` is the same `#001B76` as this page's `--navy`, so only
the nav items and the CTA label actually differ.

`hidden` is toggled alongside the open class, not just the class: the panel is
fixed over the whole page, so leaving it in the tree while invisible would swallow
taps and keep its links in the tab order. `body` scroll is locked while it is open.
It closes on the Close button, on any link, on the CTA and on Escape.

## Touch

`html.is-touch` is set at boot from `(hover: hover) and (pointer: fine)`. The
"Tap to read" chips on the problem cards and the offer slats are pure CSS off that
class, so they never appear on a mouse. Every hover mechanic also has a click
handler, and the two reveal sections use real `<button>` elements, so they work
from the keyboard as well.

## Motion engine

`js/motion.js`, no dependencies. Behaviours 1 to 7 are carried over unchanged from
the DM landing page, where the values were measured off the reference build:

| Hook | What it does |
|---|---|
| `[data-reveal]` `[data-pop]` | 40px rise / 0.72 scale, 1050ms, plays once |
| `[data-marquee="60"]` | px per second, negative drifts the other way, seamless wrap |
| `[data-count]` | count-up on first view, `easeOutExpo` |
| `[data-float]` | continuous bob, per-element phase |
| `[data-accordion]` | single-open FAQ |
| `[data-stack]` | mobile sticky stack, settle-back scale and dim |
| `[data-stage]` | the search stage: types the query, swaps the result set |
| `[data-hovercard]` | title-first cards with a tap fallback |
| `[data-slats]` | the expanding panels |
| `[data-compare]` | table row reveal and hover focus |
| `[data-track]` | the scroll-linked journey rail |

`prefers-reduced-motion` is honoured everywhere: reveals settle open, marquees go
static but stay legible, the climb jumps straight to its landed state.

## Verified

- No horizontal overflow at 320, 360, 390, 414, 480, 600, 768, 820, 900, 1024,
  1180, 1280, 1440 and 1600.
- Zero console errors.
- Every interaction driven and asserted through CDP: card open and single-open
  behaviour with correct `aria-expanded`, slat hover and flex-grow transition,
  table focus and hot row, accordion panel height, journey progress at 0.96 with
  all five steps marked done, all five marquees running.
- All six searches cycle, each painting a result set that matches its own query.
- The mobile menu opens and closes at 390, 768 and 1024 with correct
  `aria-expanded`, and the scroll lock is applied and released every time.
- The hero card is 379px on a 390x844 phone, 45% of the viewport, down from 518px
  and 61% before the mobile pass.
- The 96% chip clears the last snippet at every width across a full float cycle
  (worst case 8px). It is 85px tall once its label wraps, and the card carries
  bottom padding specifically so the chip hooks over white space rather than text.

## Still to do

1. **Fourteen photographs.** Every image slot currently holds a stand-in from the
   MYSense library. Generated art overwrites the same filename in `assets/` and
   the page picks it up with no markup change.
2. ~~The form is a styled placeholder~~ — now the live SenseBeat dual-form
   HubSpot chooser. Real submissions.
3. **WebP conversion** once the final photographs land.
4. **Elementor paste pack**, if this ships as stacked HTML widgets the way the
   sibling landing pages did. Not built yet.

Working notes, the copy inventory and the image briefs are kept outside this
repository.
