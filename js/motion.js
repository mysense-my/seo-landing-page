/* ---------------------------------------------------------------------------
   Motion engine — MYSense SEO landing page.

   The first eight behaviours are carried over unchanged from the DM landing
   page's engine, where every value was measured off the reference build:
     reveal   opacity 0->1 + translateY 40px->0 over 1050ms on
              cubic-bezier(.16,1,.3,1), fires when the element's top crosses the
              viewport bottom (IntersectionObserver threshold 0), plays ONCE.
     marquee  px/second, negative speed drifts the other way, seamless wrap.
     counters count up from 0 on first view, easeOutExpo.

   The rest are new and specific to this page: the hero search typewriter, the
   rank climb, the two title-first reveal patterns (cards and slats), the
   comparison table, and the journey progress line.
--------------------------------------------------------------------------- */
(() => {
  'use strict';

  const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const CAN_HOVER = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  if (!CAN_HOVER) document.documentElement.classList.add('is-touch');

  /* -- 1. scroll-in reveal -------------------------------------------------- */
  function initReveal() {
    const items = document.querySelectorAll('[data-reveal],[data-pop]');
    if (REDUCED || !('IntersectionObserver' in window)) {
      items.forEach(el => el.classList.add('is-in'));
      return;
    }
    const io = new IntersectionObserver((entries, obs) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        const delay = parseFloat(el.dataset.revealDelay || el.dataset.pop || 0);
        if (delay) el.style.transitionDelay = delay + 'ms';
        el.classList.add('is-in');
        obs.unobserve(el);
      });
    }, { threshold: 0 });
    items.forEach(el => io.observe(el));
  }

  /* -- 2. marquee ----------------------------------------------------------- */
  /* Duplicate the track until it covers twice the viewport, translate by exactly
     one track width, reset. Every copy is identical so the reset is invisible. */
  function initMarquee() {
    document.querySelectorAll('[data-marquee]').forEach(root => {
      const track = root.firstElementChild;
      if (!track) return;
      const speed = parseFloat(root.dataset.marquee) || 60;   // px/s, + = leftward
      let unitW = track.scrollWidth;
      if (!unitW) return;

      const fill = () => {
        const want = Math.ceil((window.innerWidth * 2) / unitW) + 1;
        while (root.children.length > want) root.lastElementChild.remove();
        while (root.children.length < want) {
          const c = track.cloneNode(true);
          c.setAttribute('aria-hidden', 'true');
          root.appendChild(c);
        }
      };
      fill();

      /* Re-measure once the webfont lands. Montserrat is much wider than the
         fallback, so a width taken at DOMContentLoaded is wrong and the loop
         shows a visible seam. The single most common way a marquee ships
         broken. A ResizeObserver covers late images too. */
      const remeasure = () => {
        const w = track.scrollWidth;
        if (!w || Math.abs(w - unitW) < 1) return;
        unitW = w; fill();
      };
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(remeasure);
      if ('ResizeObserver' in window) new ResizeObserver(remeasure).observe(track);

      if (REDUCED) return;

      let x = 0, last = null, paused = false;
      root.addEventListener('mouseenter', () => { paused = true; });
      root.addEventListener('mouseleave', () => { paused = false; });

      const step = now => {
        if (last === null) last = now;
        const dt = Math.min(now - last, 100) / 1000;    // clamp tab-switch jumps
        last = now;
        if (!paused) {
          x -= speed * dt;
          if (-x >= unitW) x += unitW;                  // wrap leftward
          if (x > 0) x -= unitW;                        // wrap rightward
          root.style.setProperty('--marquee-x', x.toFixed(2) + 'px');
        }
        requestAnimationFrame(step);
      };
      requestAnimationFrame(step);

      window.addEventListener('resize', () => { unitW = track.scrollWidth; });
    });
  }

  /* -- 3. count-up ---------------------------------------------------------- */
  const easeOutExpo = t => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t));

  const fmtNum = (v, dec) => {
    if (dec > 0) return v.toFixed(dec);
    return Math.round(v).toLocaleString('en-MY');
  };

  function runCount(el) {
    const target = parseFloat(el.dataset.count);
    if (isNaN(target)) return;
    const dur = parseFloat(el.dataset.countDur || 1600);
    const dec = parseInt(el.dataset.countDec || 0, 10);
    const pre = el.dataset.countPre || '';
    const suf = el.dataset.countSuf || '';
    const t0 = performance.now();
    const tick = now => {
      const p = Math.min((now - t0) / dur, 1);
      el.textContent = pre + fmtNum(target * easeOutExpo(p), dec) + suf;
      if (p < 1) requestAnimationFrame(tick);
      else el.textContent = pre + fmtNum(target, dec) + suf;
    };
    requestAnimationFrame(tick);
  }

  function initCounters() {
    const els = document.querySelectorAll('[data-count]');
    const settle = el => {
      const d = parseInt(el.dataset.countDec || 0, 10);
      el.textContent = (el.dataset.countPre || '') +
        fmtNum(parseFloat(el.dataset.count), d) + (el.dataset.countSuf || '');
    };
    if (REDUCED || !('IntersectionObserver' in window)) { els.forEach(settle); return; }
    const io = new IntersectionObserver((entries, obs) => {
      entries.forEach(e => {
        if (!e.isIntersecting) return;
        runCount(e.target); obs.unobserve(e.target);
      });
    }, { threshold: 0 });
    els.forEach(el => {
      el.textContent = (el.dataset.countPre || '') + '0' + (el.dataset.countSuf || '');
      io.observe(el);
    });
  }

  /* -- 4. floating chips ---------------------------------------------------- */
  function initFloat() {
    if (REDUCED) return;
    const chips = [...document.querySelectorAll('[data-float]')];
    if (!chips.length) return;
    const cfg = chips.map((el, i) => ({
      el,
      amp: parseFloat(el.dataset.float) || 10,
      period: parseFloat(el.dataset.floatPeriod || 4200),
      phase: (parseFloat(el.dataset.floatPhase) || i * 0.37) * Math.PI * 2
    }));
    const tick = now => {
      cfg.forEach(c => {
        const y = Math.sin((now / c.period) * Math.PI * 2 + c.phase) * c.amp;
        c.el.style.setProperty('--float-y', y.toFixed(2) + 'px');
      });
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  /* -- 5. accordion (FAQ) --------------------------------------------------- */
  function initAccordion() {
    document.querySelectorAll('[data-accordion]').forEach(root => {
      const items = [...root.querySelectorAll('[data-acc-item]')];
      items.forEach(item => {
        const btn = item.querySelector('[data-acc-btn]');
        const panel = item.querySelector('[data-acc-panel]');
        if (!btn || !panel) return;
        btn.setAttribute('aria-expanded', 'false');
        panel.style.height = '0px';
        btn.addEventListener('click', () => {
          const open = item.classList.contains('is-open');
          items.forEach(o => {                       // single-open accordion
            o.classList.remove('is-open');
            const p = o.querySelector('[data-acc-panel]');
            const b = o.querySelector('[data-acc-btn]');
            if (p) p.style.height = '0px';
            if (b) b.setAttribute('aria-expanded', 'false');
          });
          if (!open) {
            item.classList.add('is-open');
            panel.style.height = panel.scrollHeight + 'px';
            btn.setAttribute('aria-expanded', 'true');
          }
        });
      });
      window.addEventListener('resize', () => {
        root.querySelectorAll('.is-open [data-acc-panel]').forEach(p => {
          p.style.height = p.scrollHeight + 'px';
        });
      });
    });
  }

  /* -- 6. site header ------------------------------------------------------- */
  function initHeader() {
    const head = document.querySelector('.site-head');
    if (!head) return;
    const nav = document.querySelector('.site-nav');
    const burger = document.querySelector('[data-nav-toggle]');

    const onScroll = () => head.classList.toggle('is-stuck', window.scrollY > 24);
    onScroll();
    addEventListener('scroll', onScroll, { passive: true });

    if (burger && nav) {
      const setOpen = open => {
        nav.classList.toggle('is-open', open);
        burger.setAttribute('aria-expanded', String(open));
      };
      burger.addEventListener('click', () => setOpen(!nav.classList.contains('is-open')));
      nav.addEventListener('click', e => { if (e.target.closest('a')) setOpen(false); });
      addEventListener('keydown', e => { if (e.key === 'Escape') setOpen(false); });
    }
  }

  /* -- 7. mobile sticky card stack ------------------------------------------ */
  /* The pinning itself is pure CSS. This only adds the depth cue: as the next
     card slides over a pinned one, the pinned card settles back and dims in
     proportion to how far it is covered. */
  function initStack() {
    const mq = window.matchMedia('(max-width:767px)');
    const cards = [...document.querySelectorAll('[data-stack] > *')];
    if (REDUCED || cards.length < 2) return;

    let ticking = false;
    const paint = () => {
      ticking = false;
      if (!mq.matches) {
        cards.forEach(c => {
          c.style.removeProperty('--stack-s');
          c.style.removeProperty('--stack-d');
          c.style.removeProperty('opacity');
        });
        return;
      }
      for (let i = 0; i < cards.length - 1; i++) {
        const mine = cards[i].getBoundingClientRect();
        const next = cards[i + 1].getBoundingClientRect();
        const p = Math.min(1, Math.max(0, (mine.bottom - next.top) / mine.height));
        cards[i].style.setProperty('--stack-s', (1 - 0.06 * p).toFixed(4));
        /* The dim is a scrim INSIDE the card, not the card's own opacity.
           Fading the element itself makes it translucent, and since every card
           is also covering the one behind it, the card underneath shows
           straight through. */
        cards[i].style.setProperty('--stack-d', (0.42 * p).toFixed(3));
      }
    };
    const onScroll = () => { if (!ticking) { ticking = true; requestAnimationFrame(paint); } };
    addEventListener('scroll', onScroll, { passive: true });
    addEventListener('resize', onScroll);
    paint();
  }

  /* =========================================================================
     NEW BEHAVIOURS FOR THIS PAGE
     ========================================================================= */

  /* -- 8. search typewriter -------------------------------------------------
     Types a query, holds, deletes, types the next. The full list is also in
     the DOM as visually-hidden text so the queries are still readable to a
     screen reader and to Google. Pauses while off screen so it is not burning
     frames the whole page long. */
  function initType() {
    document.querySelectorAll('[data-type]').forEach(el => {
      const words = (el.dataset.type || '').split('|').map(s => s.trim()).filter(Boolean);
      if (!words.length) return;
      const out = el.querySelector('[data-type-out]') || el;
      if (REDUCED) { out.textContent = words[0]; return; }

      const SPEED_IN = 62, SPEED_OUT = 28, HOLD = 1700, GAP = 380;
      let w = 0, i = 0, dir = 1, t = 0, visible = true;

      if ('IntersectionObserver' in window) {
        new IntersectionObserver(es => es.forEach(e => { visible = e.isIntersecting; }),
          { threshold: 0 }).observe(el);
      }

      const tick = now => {
        if (!t) t = now;
        if (visible && now - t >= (dir > 0 ? SPEED_IN : SPEED_OUT)) {
          t = now;
          i += dir;
          const word = words[w];
          if (i >= word.length) { i = word.length; dir = -1; t = now + HOLD; }
          else if (i <= 0) { i = 0; dir = 1; w = (w + 1) % words.length; t = now + GAP; }
          out.textContent = words[w].slice(0, i);
        }
        requestAnimationFrame(tick);
      };
      out.textContent = '';
      requestAnimationFrame(tick);
    });
  }

  /* -- 9. rank climb --------------------------------------------------------
     The SERP stack in the hero. The rows sit in the DOM at their FINAL order,
     so the markup reads correctly to a screen reader and to a crawler whatever
     the animation is doing. The climb is expressed only as translateY on each
     row, so nothing ever reflows: the brand row walks up one slot at a time
     and each row it passes drops one slot to make room. */
  function initClimb() {
    document.querySelectorAll('[data-climb]').forEach(stage => {
      const rows = [...stage.querySelectorAll('[data-climb-row]')];
      const hero = stage.querySelector('[data-climb-hero]');
      const badge = stage.querySelector('[data-climb-badge]');
      if (rows.length < 2 || !hero) return;

      const from = Math.min(parseInt(stage.dataset.climbFrom || rows.length, 10), rows.length);
      const to = Math.max(parseInt(stage.dataset.climbTo || 1, 10), 1);
      let pos = from;

      /* The step is taken from the --row-h custom property first and only
         measured as a fallback. A measured step is fragile once this markup is
         pasted into a page whose theme can change a row's line-height after
         boot: the rows and the rank badge desync silently, on the single most
         important object on the page. */
      const step = () => {
        const cs = getComputedStyle(stage);
        const declared = parseFloat(cs.getPropertyValue('--row-h'));
        const gap = parseFloat(cs.rowGap) || 0;
        const h = declared || hero.getBoundingClientRect().height;
        return h + gap;
      };

      const place = p => {
        pos = p;
        const s = step();
        rows.forEach((row, i) => {
          if (row === hero) {
            row.style.setProperty('--y', ((p - 1) * s).toFixed(1) + 'px');
            return;
          }
          const natural = i + 1;                       // its resting position
          const displaced = natural <= p;              // the brand is below it
          row.style.setProperty('--y', displaced ? (-s).toFixed(1) + 'px' : '0px');
          const shown = displaced ? natural - 1 : natural;
          const rank = row.querySelector('.serp__rank');
          if (rank) rank.textContent = '#' + shown;
        });
        if (badge) badge.textContent = '#' + p;
      };

      place(from);
      if (REDUCED) { place(to); stage.classList.add('is-landed'); return; }

      let played = false;
      const run = () => {
        if (played) return;
        played = true;
        const hop = () => {
          place(pos - 1);
          stage.classList.add('is-hopping');
          setTimeout(() => stage.classList.remove('is-hopping'), 620);
          if (pos > to) setTimeout(hop, 900);
          else setTimeout(() => stage.classList.add('is-landed'), 500);
        };
        setTimeout(hop, 1100);
      };

      if ('IntersectionObserver' in window) {
        const io = new IntersectionObserver((es, obs) => {
          es.forEach(e => { if (e.isIntersecting) { run(); obs.unobserve(e.target); } });
        }, { threshold: .35 });
        io.observe(stage);
      } else { run(); }

      // the row height is font-dependent, so re-place once the webfont lands
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => place(pos));
      window.addEventListener('resize', () => place(pos));
    });
  }

  /* -- 10. title-first reveal cards ----------------------------------------
     Used by "The problem most brands face". At rest only the title shows; the
     body is revealed on hover with a fine pointer, and on tap otherwise. The
     tap affordance is a class on the card, so the "Tap to read" chip is pure
     CSS and never appears on a mouse device. Focus counts as hover for
     keyboard users, and Escape closes an open card. */
  function initHoverCards() {
    const cards = [...document.querySelectorAll('[data-hovercard]')];
    if (!cards.length) return;

    const close = except => cards.forEach(c => { if (c !== except) c.classList.remove('is-open'); });

    cards.forEach(card => {
      const btn = card.querySelector('[data-hovercard-btn]') || card;
      btn.setAttribute('aria-expanded', 'false');

      const setOpen = open => {
        card.classList.toggle('is-open', open);
        btn.setAttribute('aria-expanded', String(open));
      };

      btn.addEventListener('click', e => {
        e.preventDefault();
        const open = !card.classList.contains('is-open');
        close(card);
        setOpen(open);
      });

      // keyboard: focus opens, blur closes, matching the hover behaviour
      btn.addEventListener('focus', () => { if (CAN_HOVER) { close(card); setOpen(true); } });
      btn.addEventListener('blur', () => { if (CAN_HOVER) setOpen(false); });
    });

    document.addEventListener('keydown', e => { if (e.key === 'Escape') close(null); });
    // tapping anywhere else closes the open card on touch
    document.addEventListener('click', e => {
      if (!e.target.closest('[data-hovercard]')) close(null);
    });
  }

  /* -- 11. expanding slats --------------------------------------------------
     Used by "What MYSense SEO offers". A horizontal accordion: at rest every
     slat shows only its title, hovering one expands it and compresses the
     rest. Below the tablet breakpoint the same markup becomes a vertical
     accordion driven by tap. One slat is open by default so the section never
     reads as a row of empty columns.                                          */
  function initSlats() {
    document.querySelectorAll('[data-slats]').forEach(root => {
      const slats = [...root.querySelectorAll('[data-slat]')];
      if (!slats.length) return;
      const startIndex = parseInt(root.dataset.slats || 0, 10);

      const open = el => {
        slats.forEach(s => {
          const on = s === el;
          s.classList.toggle('is-open', on);
          const btn = s.querySelector('[data-slat-btn]');
          if (btn) btn.setAttribute('aria-expanded', String(on));
        });
      };

      slats.forEach((slat, i) => {
        const btn = slat.querySelector('[data-slat-btn]') || slat;
        btn.setAttribute('aria-expanded', String(i === startIndex));
        btn.addEventListener('click', e => {
          e.preventDefault();
          open(slat.classList.contains('is-open') && !CAN_HOVER ? null : slat);
        });
        if (CAN_HOVER) {
          slat.addEventListener('mouseenter', () => open(slat));
          btn.addEventListener('focus', () => open(slat));
        }
      });

      open(slats[startIndex] || slats[0]);
      if (CAN_HOVER) {
        root.addEventListener('mouseleave', () => open(slats[startIndex] || slats[0]));
      }
    });
  }

  /* -- 12. comparison table -------------------------------------------------
     Rows reveal in sequence as the table scrolls in, and hovering a row lifts
     it while dimming the others. The dimming lives on the table, not on each
     row, so there is one class toggle per pointer move rather than N.        */
  function initCompare() {
    document.querySelectorAll('[data-compare]').forEach(table => {
      const rows = [...table.querySelectorAll('[data-compare-row]')];
      if (!rows.length) return;

      if (REDUCED || !('IntersectionObserver' in window)) {
        rows.forEach(r => r.classList.add('is-in'));
      } else {
        const io = new IntersectionObserver((es, obs) => {
          es.forEach(e => {
            if (!e.isIntersecting) return;
            const i = rows.indexOf(e.target);
            e.target.style.transitionDelay = (i * 90) + 'ms';
            e.target.classList.add('is-in');
            obs.unobserve(e.target);
          });
        }, { threshold: .2 });
        rows.forEach(r => io.observe(r));
      }

      if (!CAN_HOVER) return;
      rows.forEach(row => {
        row.addEventListener('mouseenter', () => {
          table.classList.add('is-focusing');
          rows.forEach(r => r.classList.toggle('is-hot', r === row));
        });
      });
      table.addEventListener('mouseleave', () => {
        table.classList.remove('is-focusing');
        rows.forEach(r => r.classList.remove('is-hot'));
      });
    });
  }

  /* -- 13. journey progress line -------------------------------------------
     A scroll-linked line that fills as the five steps pass the middle of the
     viewport, and marks each step done as the line reaches it. Horizontal on
     desktop, vertical below the tablet breakpoint: the same 0..1 progress
     value drives both, only the CSS differs. */
  function initTrack() {
    document.querySelectorAll('[data-track]').forEach(track => {
      const steps = [...track.querySelectorAll('[data-track-step]')];
      if (!steps.length) return;
      let ticking = false;

      const paint = () => {
        ticking = false;
        const r = track.getBoundingClientRect();
        const mid = window.innerHeight * 0.62;
        const p = Math.min(1, Math.max(0, (mid - r.top) / Math.max(1, r.height)));
        track.style.setProperty('--track-p', p.toFixed(4));
        steps.forEach((s, i) => {
          s.classList.toggle('is-done', p >= (i + 0.35) / steps.length);
        });
      };
      const onScroll = () => { if (!ticking) { ticking = true; requestAnimationFrame(paint); } };
      addEventListener('scroll', onScroll, { passive: true });
      addEventListener('resize', onScroll);
      paint();
    });
  }

  /* -- 14. tabbed case studies ---------------------------------------------- */
  function initTabs() {
    document.querySelectorAll('[data-tabs]').forEach(root => {
      const btns = [...root.querySelectorAll('[data-tab-btn]')];
      const panes = [...root.querySelectorAll('[data-tab-pane]')];
      if (!btns.length) return;
      const select = i => {
        btns.forEach((b, n) => {
          b.classList.toggle('is-on', n === i);
          b.setAttribute('aria-selected', String(n === i));
          b.tabIndex = n === i ? 0 : -1;
        });
        panes.forEach((p, n) => { p.hidden = n !== i; p.classList.toggle('is-on', n === i); });
      };
      btns.forEach((b, i) => {
        b.addEventListener('click', () => select(i));
        b.addEventListener('keydown', e => {
          if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
          e.preventDefault();
          const n = (i + (e.key === 'ArrowRight' ? 1 : -1) + btns.length) % btns.length;
          btns[n].focus(); select(n);
        });
      });
      select(0);
    });
  }

  /* -- boot ----------------------------------------------------------------- */
  const boot = () => {
    initReveal(); initMarquee(); initCounters(); initFloat();
    initAccordion(); initHeader(); initStack();
    initType(); initClimb(); initHoverCards(); initSlats();
    initCompare(); initTrack(); initTabs();
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else { boot(); }
})();
