// Render the PNG exports of the logo, the social card and the film graphics, plus the animated film
// overlays (ProRes 4444 with alpha). Editorial style, see brand/DESIGN.md.
//
// node brand/tools/render_graphics.js   (Playwright + Chromium, ffmpeg; Geist installed from brand/fonts)
const path = require('path');
const fs = require('fs');
const os = require('os');
const { execFileSync } = require('child_process');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');

const ROOT = path.resolve(__dirname, '..', '..');
const LOGO = path.join(ROOT, 'brand', 'logo');
const GFX = path.join(ROOT, 'marketing', 'film', 'graphics');
const script = JSON.parse(fs.readFileSync(path.join(ROOT, 'marketing', 'film', 'script.json'), 'utf8'));
const svg = (name) => fs.readFileSync(path.join(LOGO, name), 'utf8');
const sized = (markup, height) => markup.replace(/width="[\d.]+" height="[\d.]+"/, `height="${height}"`);

const C = { paper: '#FAFAF7', ink: '#111418', graphite: '#5B6470', rule: '#D9DCE1', teal: '#0F766E', correction: '#D9480F' };
const FPS = 25;

// ---------------------------------------------------------------------------------------------
// Hand-drawn marks: seeded, slightly irregular paths, drawn on with stroke-dashoffset (pathLength=1).

function rng(seed) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 2 ** 32);
}

function smooth(points) {
  // Catmull-Rom through the points, as cubic Béziers.
  let d = `M${points[0][0].toFixed(1)} ${points[0][1].toFixed(1)}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[Math.max(0, i - 1)], p1 = points[i], p2 = points[i + 1], p3 = points[Math.min(points.length - 1, i + 2)];
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += ` C${c1[0].toFixed(1)} ${c1[1].toFixed(1)} ${c2[0].toFixed(1)} ${c2[1].toFixed(1)} ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
  }
  return d;
}

// An ellipse drawn by hand: a bit more than one turn, wobbling radius, the end overshoots the start.
function ringPath(cx, cy, rx, ry, seed) {
  const r = rng(seed);
  const a0 = -2.3 + r() * 0.4, turns = 1.12 + r() * 0.08, f1 = r() * 6, f2 = r() * 6, tilt = (r() - 0.5) * 0.08;
  const pts = [];
  for (let i = 0; i <= 48; i++) {
    const t = i / 48, a = a0 + t * turns * Math.PI * 2;
    const k = 1 + 0.035 * Math.sin(3 * a + f1) + 0.02 * Math.sin(5 * a + f2) + 0.05 * t;
    const x = rx * k * Math.cos(a), y = ry * k * Math.sin(a);
    pts.push([cx + x * Math.cos(tilt) - y * Math.sin(tilt), cy + x * Math.sin(tilt) + y * Math.cos(tilt)]);
  }
  return smooth(pts);
}

// An underline drawn by hand: slight arc and drift, the end lifts a little.
function underlinePath(x, y, w, seed) {
  const r = rng(seed), pts = [];
  for (let i = 0; i <= 10; i++) {
    const t = i / 10;
    pts.push([x + t * w, y + Math.sin(t * Math.PI) * (1.5 + r() * 1.5) - t * t * 4 + (r() - 0.5) * 0.8]);
  }
  return smooth(pts);
}

const stroke = (d, color, width, progress) =>
  `<path d="${d}" pathLength="1" fill="none" stroke="${color}" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1 1" stroke-dashoffset="${(1 - progress).toFixed(4)}"/>`;

const ease = (t) => 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);
const seg = (p, a, b) => ease((p - a) / (b - a));

// ---------------------------------------------------------------------------------------------
// Page scaffolding.

const BASE = `*{box-sizing:border-box;margin:0;padding:0}html,body{background:transparent}
body{font-family:Geist,sans-serif;color:${C.ink};-webkit-font-smoothing:antialiased;font-feature-settings:"ss01"}
svg{display:block}.mono{font-family:"Geist Mono",monospace;letter-spacing:.02em}
.frame{position:relative;overflow:hidden}`;
const page = (w, h, body, css = '') => `<!doctype html><html><head><meta charset="utf-8"><style>${BASE}
.frame{width:${w}px;height:${h}px}${css}</style></head><body>${body}</body></html>`;

// Title card (S04). progress 0..1 animates the rule, logo and tagline.
const TITLE_CSS = `.paper{background:${C.paper}}
.head{position:absolute;left:96px;right:96px;top:56px;display:flex;justify-content:space-between;font-size:15px;color:${C.graphite}}
.top-rule{position:absolute;left:96px;right:96px;top:92px;height:1px;background:${C.rule}}
.logo{position:absolute;left:96px;top:262px}
.tag{position:absolute;left:100px;top:420px;font-size:36px;font-weight:500;letter-spacing:-.6px}
.foot{position:absolute;left:96px;right:96px;bottom:52px;display:flex;justify-content:space-between;font-size:15px;color:${C.graphite}}`;
function title(progress, { background = true, foreground = true } = {}) {
  const ruleP = seg(progress, 0.0, 0.45), logoP = seg(progress, 0.2, 0.65), tagP = seg(progress, 0.45, 0.95);
  const bg = background ? `<div class="head mono"><span>RenovaCheck — 01</span><span>Kontrola dokumentów · Czyste Powietrze</span></div>
    <div class="top-rule"></div><div class="foot mono"><span>${script.small_print.pl}</span><span>2026</span></div>` : '';
  const fg = foreground ? `<div class="logo" style="opacity:${logoP};transform:translateY(${(1 - logoP) * 10}px)">${sized(svg('logo-horizontal.svg'), 104)}</div>
    <div style="position:absolute;left:96px;top:392px;height:2px;width:${(ruleP * 560).toFixed(1)}px;background:${C.ink}"></div>
    <div class="tag" style="opacity:${tagP};transform:translateY(${(1 - tagP) * 8}px)">${script.tagline.pl}</div>` : '';
  return page(1280, 720, `<div class="frame${background ? ' paper' : ''}">${bg}${fg}</div>`, TITLE_CSS);
}

// Margin note (S06–S09): a square paper slip at the top left, mono reference, PL headline, EN line,
// and a hand-drawn underline in the mark colour.
const NOTE_CSS = `.note{position:absolute;left:40px;top:36px;background:${C.paper};padding:16px 24px 18px 20px;border:1px solid ${C.rule};border-left:3px solid ${C.ink}}
.note .ref{font-size:13px;color:${C.graphite};text-transform:uppercase}
.note .pl{font-size:28px;font-weight:600;letter-spacing:-.5px;margin-top:6px;white-space:nowrap}
.note .en{font-size:15px;color:${C.graphite};margin-top:4px}
.note svg{position:absolute;left:20px;top:0;overflow:visible}`;
function note({ ref, pl, en, color, seed }, progress) {
  const slip = seg(progress, 0, 0.35), line = seg(progress, 0.35, 1);
  const width = pl.length * 15.2;
  return page(1280, 720, `<div class="frame"><div class="note" style="opacity:${slip};transform:translateX(${(1 - slip) * -16}px)">
    <div class="ref mono">${ref}</div><div class="pl">${pl}</div><div class="en">${en}</div>
    <svg width="${width + 20}" height="10" style="top:68px">${stroke(underlinePath(0, 6, width, seed), color, 4, line)}</svg></div></div>`, NOTE_CSS);
}

// Trust list (S10): a paper column on the left with three numbered lines between hairlines.
const TRUST = [
  ['Decyzję podejmuje człowiek', 'A person decides'],
  ['Pełna historia: kto i kiedy', 'Full who-and-when history'],
  ['Dane organizacji odseparowane', 'Data isolated per organisation'],
];
const TRUST_CSS = `.col{position:absolute;left:0;top:0;bottom:0;width:600px;background:${C.paper};padding:120px 56px 0 64px}
.col .ref{font-size:13px;color:${C.graphite};text-transform:uppercase;margin-bottom:22px}
.row{display:flex;gap:22px;padding:20px 0;border-top:1px solid ${C.rule}}.row:last-child{border-bottom:1px solid ${C.rule}}
.row .n{font-size:15px;color:${C.teal};padding-top:6px}.row .pl{font-size:26px;font-weight:600;letter-spacing:-.4px}
.row .en{font-size:15px;color:${C.graphite};margin-top:3px}`;
function trust(progress) {
  const col = seg(progress, 0, 0.3);
  const rows = TRUST.map(([pl, en], i) => {
    const p = seg(progress, 0.25 + i * 0.22, 0.5 + i * 0.22);
    return `<div class="row" style="opacity:${p};transform:translateY(${(1 - p) * 8}px)"><div class="n mono">0${i + 1}</div><div><div class="pl">${pl}</div><div class="en">${en}</div></div></div>`;
  }).join('');
  return page(1280, 720, `<div class="frame"><div class="col" style="transform:translateX(${(col - 1) * 600}px)"><div class="ref mono">RenovaCheck — zasady</div>${rows}</div></div>`, TRUST_CSS);
}

// End card (S12).
const END_CSS = `.paper{background:${C.paper}}
.logo{position:absolute;left:96px;top:200px}
.tag{position:absolute;left:100px;top:336px;font-size:44px;font-weight:600;letter-spacing:-1px;line-height:1.08}
.cta{position:absolute;left:100px;top:470px;font-size:26px;font-weight:500;color:${C.teal}}
.cta svg{margin-top:4px;overflow:visible}
.contact{position:absolute;left:100px;top:530px;font-size:18px;color:${C.graphite}}
.head{position:absolute;left:96px;right:96px;top:56px;display:flex;justify-content:space-between;font-size:15px;color:${C.graphite}}
.top-rule{position:absolute;left:96px;right:96px;top:92px;height:1px;background:${C.rule}}
.foot{position:absolute;left:96px;right:96px;bottom:52px;font-size:15px;color:${C.graphite}}`;
const endCard = () => page(1280, 720, `<div class="frame paper">
  <div class="head mono"><span>RenovaCheck — 12</span><span>Kontrola dokumentów · Czyste Powietrze</span></div><div class="top-rule"></div>
  <div class="logo">${sized(svg('logo-horizontal.svg'), 72)}</div>
  <div class="tag">${script.tagline.pl.replace('. ', '.<br>')}</div>
  <div class="cta">${script.cta.pl} →<svg width="260" height="8">${stroke(underlinePath(0, 3, 250, 12), C.teal, 3, 1)}</svg></div>
  <div class="foot mono">${script.small_print.pl}</div></div>`, END_CSS);

// Social card (1200 x 630).
const social = () => page(1200, 630, `<div class="frame paper">
  <div class="head mono"><span>RenovaCheck</span><span>Kontrola dokumentów · Czyste Powietrze</span></div><div class="top-rule"></div>
  <div class="logo">${sized(svg('logo-horizontal.svg'), 60)}</div>
  <div class="tag">${script.tagline.pl.replace('. ', '.<br>')}</div>
  <div class="sub">Spójność wniosku, umowy, faktur i protokołu<br>sprawdzona przed złożeniem rozliczenia.</div>
  <div class="foot mono">${script.small_print.pl}</div></div>`, END_CSS.replace(/96px/g, '80px') + `
  .logo{top:150px}.tag{top:250px;left:84px;font-size:56px}.sub{position:absolute;left:84px;top:400px;font-size:22px;color:${C.graphite};line-height:1.4}`);

// Hand-drawn ring and click mark for manual placement in the edit.
const ring = (progress) => page(360, 220, `<div class="frame"><svg width="360" height="220">${stroke(ringPath(180, 110, 150, 78, 7), C.correction, 5, progress)}</svg></div>`);
const click = () => page(120, 120, `<div class="frame"><svg width="120" height="120">${stroke(ringPath(60, 60, 34, 32, 3), C.correction, 4, 1)}</svg></div>`);
const cursor = () => page(96, 96, `<div class="frame"><svg viewBox="0 0 24 24" width="72" height="72" style="margin:8px">
  <path d="M4 2 L4 19 L8.5 15 L11.5 21.5 L14.5 20.2 L11.6 13.8 L17.5 13.6 Z" fill="#fff" stroke="${C.ink}" stroke-width="1.4" stroke-linejoin="round"/></svg></div>`);

const NOTES = [
  ['G06_note_discrepancy', { ref: '03 — PRD-01 · krytyczne', pl: 'Rozbieżność wykryta', en: 'Discrepancy found', color: C.correction, seed: 61 }],
  ['G07_note_evidence', { ref: '04 — dowód', pl: 'Dowód na stronie dokumentu', en: 'Evidence on the page', color: C.teal, seed: 72 }],
  ['G08_note_decision', { ref: '05 — decyzja', pl: 'Decyzję podejmuje człowiek', en: 'A person decides', color: C.teal, seed: 83 }],
  ['G09_note_report', { ref: '06 — raport', pl: 'Raport kontroli: PDF / CSV', en: 'Control report', color: C.teal, seed: 94 }],
];

// ---------------------------------------------------------------------------------------------

(async () => {
  const browser = await chromium.launch();
  const shoot = async (html, out, w, h, transparent) => {
    const p = await browser.newPage({ viewport: { width: w, height: h } });
    await p.setContent(html, { waitUntil: 'load' });
    await p.evaluate(() => document.fonts.ready);
    fs.mkdirSync(path.dirname(out), { recursive: true });
    await p.screenshot({ path: out, omitBackground: transparent });
    await p.close();
  };
  const still = async (rel, w, h, html, transparent = true) => { await shoot(html, path.join(ROOT, rel), w, h, transparent); console.log(rel); };
  // Animated overlay: render each frame, encode ProRes 4444 with alpha. Only the build-in is animated;
  // the edit holds the matching still afterwards.
  const animate = async (rel, w, h, frames, render) => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'rc-anim-'));
    for (let i = 0; i < frames; i++) await shoot(render(i / (frames - 1)), path.join(dir, `${String(i).padStart(4, '0')}.png`), w, h, true);
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(FPS), '-i', path.join(dir, '%04d.png'),
      '-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le', '-alpha_bits', '16', '-vendor', 'apl0', path.join(ROOT, rel)]);
    fs.rmSync(dir, { recursive: true, force: true });
    console.log(rel);
  };

  // Logo exports.
  await still('brand/logo/png/logo-horizontal-1600w.png', 1600, 296, page(1600, 296, `<div class="frame">${sized(svg('logo-horizontal.svg'), 296)}</div>`));
  await still('brand/logo/png/logo-inverse-1600w.png', 1600, 296, page(1600, 296, `<div class="frame">${sized(svg('logo-inverse.svg'), 296)}</div>`));
  for (const s of [512, 1024]) {
    await still(`brand/logo/png/logo-mark-${s}.png`, s, s, page(s, s, `<div class="frame">${sized(svg('logo-mark.svg'), s)}</div>`));
    await still(`brand/logo/png/app-icon-${s}.png`, s, s, page(s, s, `<div class="frame">${sized(svg('favicon.svg'), s)}</div>`));
  }
  await still('brand/social/social-card-1200x630.png', 1200, 630, social(), false);

  // Film graphics.
  const G = (name) => `marketing/film/graphics/${name}`;
  await still(G('G04_title_bg.png'), 1280, 720, title(1, { foreground: false }), false);
  await still(G('G04_title_logo.png'), 1280, 720, title(1, { background: false }));
  await still(G('G04_title_card.png'), 1280, 720, title(1), false);
  await animate(G('G04_title_logo_in.mov'), 1280, 720, 25, (p) => title(p, { background: false }));
  for (const [name, spec] of NOTES) {
    await still(G(`${name}.png`), 1280, 720, note(spec, 1));
    await animate(G(`${name}_in.mov`), 1280, 720, 15, (p) => note(spec, p));
  }
  await still(G('G10_trust.png'), 1280, 720, trust(1));
  await animate(G('G10_trust_in.mov'), 1280, 720, 40, trust);
  await still(G('G12_end_card.png'), 1280, 720, endCard(), false);
  await still(G('FX_ring.png'), 360, 220, ring(1));
  await animate(G('FX_ring_draw.mov'), 360, 220, 12, ring);
  await still(G('FX_click_mark.png'), 120, 120, click());
  await still(G('FX_cursor.png'), 96, 96, cursor());
  await browser.close();
})();
