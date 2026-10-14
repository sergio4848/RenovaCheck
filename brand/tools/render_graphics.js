// Render the PNG exports of the logo and the film/social graphics with Chromium.
// node brand/tools/render_graphics.js   (Playwright with Chromium; Inter installed)
const path = require('path');
const fs = require('fs');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');

const ROOT = path.resolve(__dirname, '..', '..');
const LOGO = path.join(ROOT, 'brand', 'logo');
const FILM = path.join(ROOT, 'marketing', 'film');
const script = JSON.parse(fs.readFileSync(path.join(FILM, 'script.json'), 'utf8'));
const svg = (name) => fs.readFileSync(path.join(LOGO, name), 'utf8');

const C = { teal: '#0F766E', ink: '#0B1F33', amber: '#F59E0B', paper: '#F6F8FB', tealLight: '#5EEAD4' };
const BASE = `*{box-sizing:border-box;margin:0}html,body{background:transparent}
body{font-family:Inter,"Segoe UI",Arial,sans-serif;-webkit-font-smoothing:antialiased}
svg{display:block}`;

const page = (w, h, body, css = '') => `<!doctype html><html><head><meta charset="utf-8"><style>${BASE}
.frame{width:${w}px;height:${h}px;position:relative;overflow:hidden}${css}</style></head><body>${body}</body></html>`;

const sized = (markup, height) => markup.replace(/width="[\d.]+" height="[\d.]+"/, `height="${height}"`);

const pill = (text, sub) => `<div class="pill"><span class="dot"></span><div><div class="t">${text}</div>${sub ? `<div class="s">${sub}</div>` : ''}</div></div>`;
const PILL_CSS = `.pill{display:inline-flex;align-items:center;gap:14px;padding:14px 22px 14px 18px;border-radius:16px;
background:rgba(11,31,51,.92);color:#fff;box-shadow:0 10px 30px rgba(11,31,51,.35)}
.pill .dot{width:14px;height:14px;border-radius:50%;background:${C.amber};box-shadow:0 0 0 5px rgba(245,158,11,.25)}
.pill .t{font-size:24px;font-weight:700;letter-spacing:-.2px}.pill .s{font-size:16px;color:#B6C2D1;margin-top:2px}`;

const jobs = [];
const add = (out, w, h, html, transparent = true) => jobs.push({ out, w, h, html, transparent });

// Logo exports.
add('brand/logo/png/logo-horizontal-1600w.png', 1600, 304, page(1600, 304, `<div class="frame">${sized(svg('logo-horizontal.svg'), 304)}</div>`));
add('brand/logo/png/logo-inverse-1600w.png', 1600, 304, page(1600, 304, `<div class="frame">${sized(svg('logo-inverse.svg'), 304)}</div>`));
for (const s of [512, 1024]) {
  add(`brand/logo/png/logo-mark-${s}.png`, s, s, page(s, s, `<div class="frame">${sized(svg('logo-mark.svg'), s)}</div>`));
  add(`brand/logo/png/app-icon-${s}.png`, s, s, page(s, s, `<div class="frame">${sized(svg('favicon.svg'), s)}</div>`));
}

// Social card.
add('brand/social/social-card-1200x630.png', 1200, 630, page(1200, 630, `<div class="frame card">
  <div class="logo">${sized(svg('logo-inverse.svg'), 76)}</div>
  <h1>${script.tagline.pl.replace('. ', '.<br>')}</h1><p>Kontrola spójności dokumentów termomodernizacji<br>w programie Czyste Powietrze.</p>
  <div class="foot">${script.small_print.pl}</div></div>`, `.card{background:radial-gradient(1200px 600px at 85% 20%,#134e4a 0%,${C.ink} 60%);padding:72px 80px;color:#fff}
  .card h1{font-size:64px;line-height:1.05;letter-spacing:-1.5px;margin-top:70px;max-width:900px}
  .card p{font-size:26px;color:#B6C2D1;margin-top:22px;max-width:860px}.card .foot{position:absolute;bottom:44px;left:80px;font-size:18px;color:#7F8EA3}`), false);

// Film: title card (end frame of the logo reveal) and end card.
const titleCss = `.t{background:radial-gradient(900px 500px at 50% 45%,#12403f 0%,${C.ink} 70%);display:flex;flex-direction:column;align-items:center;justify-content:center;color:#fff}
.t .tag{font-size:30px;color:#CFE9E5;margin-top:26px;letter-spacing:.2px}`;
add('marketing/film/graphics/G04_title_card.png', 1280, 720, page(1280, 720, `<div class="frame t">${sized(svg('logo-inverse.svg'), 92)}<div class="tag">${script.tagline.pl}</div></div>`, titleCss), false);
// Logo reveal: an empty background (V1) and the logo with the tagline on a transparent layer (V2) to animate.
add('marketing/film/graphics/G04_title_bg.png', 1280, 720, page(1280, 720, `<div class="frame t"></div>`, titleCss), false);
add('marketing/film/graphics/G04_logo_transparent.png', 1280, 720, page(1280, 720, `<div class="frame" style="display:flex;flex-direction:column;align-items:center;justify-content:center">
  ${sized(svg('logo-inverse.svg'), 92)}<div class="tag">${script.tagline.pl}</div></div>`, `.tag{font-size:30px;color:#CFE9E5;margin-top:26px;letter-spacing:.2px}`));
add('marketing/film/graphics/G12_end_card.png', 1280, 720, page(1280, 720, `<div class="frame t">${sized(svg('logo-inverse.svg'), 84)}
  <div class="tag">${script.tagline.pl}</div><div class="cta">${script.cta.pl} <span>→</span></div>
  <div class="small">${script.small_print.pl}</div></div>`, titleCss + `
  .cta{margin-top:44px;background:${C.amber};color:${C.ink};font-weight:800;font-size:28px;padding:16px 34px;border-radius:999px}
  .small{position:absolute;bottom:34px;font-size:16px;color:#7F8EA3}`), false);

// Overlays for the product part (transparent, full frame so they drop onto V2 without positioning).
const overlay = (inner, css = '') => page(1280, 720, `<div class="frame">${inner}</div>`, PILL_CSS + css);
const callouts = [
  ['G06_callout_discrepancy', 'Rozbieżność wykryta', 'Discrepancy found'],
  ['G07_callout_evidence', 'Dowód na stronie dokumentu', 'Evidence on the page'],
  ['G08_callout_decision', 'Decyzję podejmuje człowiek', 'A person decides'],
  ['G09_callout_report', 'Raport kontroli: PDF / CSV', 'Control report'],
];
for (const [name, pl, en] of callouts) {
  add(`marketing/film/graphics/${name}.png`, 1280, 720, overlay(`<div style="position:absolute;left:48px;top:44px">${pill(pl, en)}</div>`));
}
add('marketing/film/graphics/G10_trust_chips.png', 1280, 720, overlay(`<div class="chips">
  ${pill('Decyzję podejmuje człowiek', 'A person decides')}${pill('Pełna historia: kto i kiedy', 'Full who-and-when history')}${pill('Dane organizacji odseparowane', 'Data isolated per organisation')}</div>`,
  `.chips{position:absolute;left:48px;top:44px;display:flex;flex-direction:column;gap:14px;align-items:flex-start}`));

// Highlight ring, cursor and click ripple for the screen recordings.
add('marketing/film/graphics/FX_highlight_ring.png', 320, 320, page(320, 320, `<div class="frame"><div class="ring"></div></div>`,
  `.ring{position:absolute;inset:20px;border:8px solid ${C.amber};border-radius:24px;box-shadow:0 0 0 10px rgba(245,158,11,.25)}`));
add('marketing/film/graphics/FX_cursor.png', 96, 96, page(96, 96, `<div class="frame"><svg viewBox="0 0 24 24" width="72" height="72" style="margin:8px">
  <path d="M4 2 L4 19 L8.5 15 L11.5 21.5 L14.5 20.2 L11.6 13.8 L17.5 13.6 Z" fill="#fff" stroke="${C.ink}" stroke-width="1.4" stroke-linejoin="round"/></svg></div>`));
add('marketing/film/graphics/FX_click_ripple.png', 160, 160, page(160, 160, `<div class="frame"><div class="r1"></div><div class="r2"></div></div>`,
  `.r1,.r2{position:absolute;border-radius:50%;border:5px solid ${C.amber}}.r1{inset:20px;opacity:.9}.r2{inset:50px;background:rgba(245,158,11,.35);border:none}`));

(async () => {
  const browser = await chromium.launch();
  for (const job of jobs) {
    const p = await browser.newPage({ viewport: { width: job.w, height: job.h } });
    await p.setContent(job.html, { waitUntil: 'load' });
    await p.evaluate(() => document.fonts.ready);
    const out = path.join(ROOT, job.out);
    fs.mkdirSync(path.dirname(out), { recursive: true });
    await p.screenshot({ path: out, omitBackground: job.transparent });
    await p.close();
    console.log(job.out);
  }
  await browser.close();
})();
