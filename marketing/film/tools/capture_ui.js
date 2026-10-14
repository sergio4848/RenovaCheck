// Records the product part of the film from the running stack (make up), with synthetic case SYN-2026-012.
//
// node marketing/film/tools/capture_ui.js <documents dir> <out dir>
//
// Use an empty demo organisation (default: the owner of Beta Dokumentacja). Four background cases from the
// synthetic set are uploaded first, off camera, so the case list shows a realistic mix of statuses.
//
// Each segment is captured from Chrome's screencast (JPEG frames with timestamps) and written by ffmpeg as
// 1280x720, 25 fps H.264. A drawn cursor and click ripple exist only in this capture browser (bypassCSP);
// the application itself is unchanged. Stills are taken at 2x for zooms in the edit.
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');

const BASE = process.env.BASE_URL || 'http://localhost:8080';
const [docsDir, outDir] = process.argv.slice(2);
const SYNTH = path.resolve(docsDir, '..', '..');
const BACKGROUND = [
  ['CP/2026/0377', 'Docieplenie ścian i pompa ciepła – Wieliczka', 'SYN-2026-001'],
  ['CP/2026/0391', 'Pompa ciepła i instalacja c.o. – Tarnów', 'SYN-2026-013'],
  ['CP/2026/0402', 'Wymiana źródła ciepła – Bochnia', 'SYN-2026-007'],
  ['CP/2026/0408', 'Pompa ciepła z aneksem do umowy – Myślenice', 'SYN-2026-009'],
];
const W = 1280;
const H = 720;
fs.mkdirSync(outDir, { recursive: true });

const CURSOR = () => {
  const cursor = document.createElement('div');
  const ripple = document.createElement('div');
  for (const [el, css] of [
    [cursor, 'position:fixed;z-index:2147483647;left:0;top:0;width:22px;height:22px;pointer-events:none;transform:translate(-3px,-2px);'
      + 'background:no-repeat url("data:image/svg+xml;utf8,<svg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27>'
      + '<path d=%27M4 2 L4 19 L8.5 15 L11.5 21.5 L14.5 20.2 L11.6 13.8 L17.5 13.6 Z%27 fill=%27white%27 stroke=%27%230B1F33%27 stroke-width=%271.5%27/></svg>");background-size:22px 22px'],
    [ripple, 'position:fixed;z-index:2147483646;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;pointer-events:none;'
      + 'border:3px solid #F59E0B;background:rgba(245,158,11,.25);opacity:0;transition:opacity .45s, transform .45s;transform:scale(.4)'],
  ]) { el.style.cssText = css; }
  const mount = () => document.body && !cursor.isConnected && document.body.append(ripple, cursor);
  document.addEventListener('DOMContentLoaded', mount);
  window.addEventListener('mousemove', (e) => { mount(); cursor.style.left = e.clientX + 'px'; cursor.style.top = e.clientY + 'px'; }, true);
  window.addEventListener('mousedown', (e) => {
    mount();
    ripple.style.left = e.clientX + 'px'; ripple.style.top = e.clientY + 'px';
    ripple.style.transition = 'none'; ripple.style.opacity = '1'; ripple.style.transform = 'scale(.4)';
    requestAnimationFrame(() => { ripple.style.transition = 'opacity .5s, transform .5s'; ripple.style.opacity = '0'; ripple.style.transform = 'scale(1.6)'; });
  }, true);
};

class Recorder {
  constructor(page) { this.page = page; }

  async start(name) {
    this.name = name;
    this.frames = [];
    this.dir = fs.mkdtempSync(path.join(outDir, `.${name}-`));
    this.cdp = await this.page.context().newCDPSession(this.page);
    this.cdp.on('Page.screencastFrame', async ({ data, metadata, sessionId }) => {
      const file = path.join(this.dir, `${String(this.frames.length).padStart(5, '0')}.jpg`);
      fs.writeFileSync(file, Buffer.from(data, 'base64'));
      this.frames.push({ file, t: metadata.timestamp });
      await this.cdp.send('Page.screencastFrameAck', { sessionId }).catch(() => {});
    });
    await this.cdp.send('Page.startScreencast', { format: 'jpeg', quality: 95, maxWidth: W, maxHeight: H, everyNthFrame: 1 });
    this.t0 = Date.now() / 1000;
  }

  async stop() {
    await this.page.waitForTimeout(300);
    await this.cdp.send('Page.stopScreencast');
    const end = Date.now() / 1000;
    await this.cdp.detach();
    // Frames arrive only when the page changes: hold each one until the next (ffconcat durations).
    const lines = ['ffconcat version 1.0'];
    this.frames.forEach((f, i) => {
      const next = i + 1 < this.frames.length ? this.frames[i + 1].t : end;
      lines.push(`file '${path.basename(f.file)}'`, `duration ${Math.max(0.04, next - f.t).toFixed(3)}`);
    });
    lines.push(`file '${path.basename(this.frames[this.frames.length - 1].file)}'`);
    const list = path.join(this.dir, 'frames.ffconcat');
    fs.writeFileSync(list, lines.join('\n') + '\n');
    const out = path.join(outDir, `${this.name}.mp4`);
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list,
      '-vf', `scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:color=white,fps=25,format=yuv420p`,
      '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-movflags', '+faststart', out]);
    fs.rmSync(this.dir, { recursive: true, force: true });
    console.log(`${this.name}.mp4  ${this.frames.length} frames, ${(end - this.frames[0].t).toFixed(1)} s`);
  }
}

async function glide(page, locator, opts = {}) {
  // Bring the element to the middle of the viewport first, smoothly, so the cursor never leaves the frame.
  const visible = await locator.evaluate((el) => {
    const r = el.getBoundingClientRect();
    return r.top >= 60 && r.bottom <= window.innerHeight - 40;
  });
  if (!visible) {
    await locator.evaluate((el) => el.scrollIntoView({ behavior: 'smooth', block: 'center' }));
    await page.waitForTimeout(900);
  }
  const box = await locator.boundingBox();
  if (!box) throw new Error('element not visible');
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: opts.steps || 30 });
  await page.waitForTimeout(opts.pause ?? 250);
}

async function click(page, locator, opts = {}) {
  await glide(page, locator, opts);
  await page.mouse.down();
  await page.mouse.up();
}

async function smoothScroll(page, selector) {
  await page.evaluate((sel) => document.querySelector(sel).scrollIntoView({ behavior: 'smooth', block: 'start' }), selector);
  await page.waitForTimeout(1400);
}

(async () => {
  // The full Chromium build carries the Polish UI strings (file picker); the headless shell does not.
  const browser = await chromium.launch({ channel: 'chromium', args: ['--lang=pl'], env: { ...process.env, LANG: 'pl_PL.UTF-8', LANGUAGE: 'pl' } });
  const context = await browser.newContext({ viewport: { width: W, height: H }, bypassCSP: true, colorScheme: 'light', locale: 'pl-PL' });
  await context.addInitScript(CURSOR);
  const page = await context.newPage();
  const rec = new Recorder(page);
  const still = async (name) => {
    const hi = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 2, storageState: await context.storageState() });
    const p = await hi.newPage();
    await p.goto(page.url());
    await p.waitForLoadState('networkidle');
    await p.screenshot({ path: path.join(outDir, `${name}.png`) });
    await hi.close();
  };

  await page.goto(`${BASE}/login`);
  await page.fill('input[name=email]', process.env.CAPTURE_EMAIL || 'wlasciciel@beta.test');
  await page.fill('input[name=password]', process.env.DEMO_USER_PASSWORD || 'renova-demo');
  await Promise.all([page.waitForNavigation(), page.click('button[type=submit]')]);
  for (const [reference, title, synthCase] of BACKGROUND) {
    await page.goto(`${BASE}/cases`);
    await page.click('text=Nowa sprawa');
    await page.fill('#reference', reference);
    await page.fill('#title', title);
    await Promise.all([page.waitForNavigation(), page.click('text=Utwórz sprawę')]);
    const dir = path.join(SYNTH, synthCase, 'documents');
    await page.setInputFiles('input[type=file]', fs.readdirSync(dir).filter((f) => f.endsWith('.pdf')).map((f) => path.join(dir, f)));
    await Promise.all([page.waitForNavigation(), page.click('button:has-text("Wgraj")')]);
  }
  await page.goto(`${BASE}/cases`);
  await page.mouse.move(W / 2, H / 2);
  await page.click('text=Nowa sprawa');
  await page.fill('#reference', process.env.CASE_REF || 'CP/2026/0412');
  await page.fill('#title', 'Pompa ciepła – dom jednorodzinny, Kraków');
  await Promise.all([page.waitForNavigation(), page.click('text=Utwórz sprawę')]);
  await page.waitForTimeout(600);

  // UI01: choose six PDFs and upload; the page refreshes itself while the documents are analysed.
  const files = fs.readdirSync(docsDir).filter((f) => f.endsWith('.pdf')).sort().map((f) => path.join(docsDir, f));
  await rec.start('UI01_upload');
  await glide(page, page.locator('input[type=file]'), { steps: 40, pause: 400 });
  await page.setInputFiles('input[type=file]', files);
  await page.waitForTimeout(700);
  await click(page, page.locator('button:has-text("Wgraj")'));
  await page.waitForLoadState('load');
  await page.waitForTimeout(1500);
  await rec.stop();
  for (let i = 0; i < 90; i++) {
    if (await page.locator('a.fw-bold[href*="/findings/"]').count() > 0 && await page.locator('[data-refresh]').count() === 0) break;
    await page.waitForTimeout(1000);
  }
  await page.reload();
  await page.mouse.move(W - 200, 160);

  // UI02: the processed documents, then the findings with severity and reasons.
  await rec.start('UI02_findings');
  await page.waitForTimeout(600);
  await smoothScroll(page, '.card:has(a.fw-bold[href*="/findings/"])');
  await glide(page, page.locator('a.fw-bold[href*="/findings/"]').first(), { steps: 45, pause: 900 });
  await rec.stop();
  await still('UI02_findings_still');
  const caseUrl = page.url();

  // UI03: the review screen; hovering the evidence rows highlights the boxes on the page image.
  await Promise.all([page.waitForNavigation(), page.locator('a.fw-bold[href*="/findings/"]').first().click()]);
  await page.waitForLoadState('networkidle');
  await page.mouse.move(W - 260, H - 120);
  await rec.start('UI03_evidence');
  await page.waitForTimeout(700);
  const rows = page.locator('.evidence-row');
  for (let i = 0; i < Math.min(await rows.count(), 3); i++) await glide(page, rows.nth(i), { steps: 30, pause: 900 });
  await rec.stop();
  await page.locator('.evidence-row').first().hover();
  await still('UI03_evidence_still');

  // UI04: a person decides: "Rozbieżność" with a comment, saved to the history.
  await rec.start('UI04_decision');
  await click(page, page.locator('input[name=decision][value=rozbieznosc]'), { steps: 35 });
  await click(page, page.locator('#comment'), { steps: 25 });
  await page.keyboard.type('Model na karcie produktu (B) różni się od umowy (A) – poproszono o właściwą kartę.', { delay: 28 });
  await page.waitForTimeout(400);
  await click(page, page.locator('button:has-text("Zapisz decyzję")'));
  await page.waitForLoadState('load');
  await page.waitForTimeout(1200);
  await rec.stop();

  // Remaining (non-critical) findings are confirmed off camera.
  for (let i = 0; i < 10; i++) {
    if (await page.locator('input[name=decision]:checked').count() > 0) break;
    const severity = await page.locator('.col-lg-5 [data-severity]').first().getAttribute('data-severity');
    if (severity === 'critical') break;
    await page.check('input[name=decision][value=zgodne]');
    await Promise.all([page.waitForNavigation(), page.click('button:has-text("Zapisz decyzję")')]);
  }

  // UI05: close the case and download the control report.
  await page.goto(caseUrl);
  await page.mouse.move(W / 2, H / 2);
  await rec.start('UI05_close_report');
  await page.waitForTimeout(500);
  await click(page, page.locator('button:has-text("Zamknij sprawę")'), { steps: 35 });
  await page.waitForLoadState('load');
  await page.waitForTimeout(900);
  const alert = await page.locator('.alert').first().innerText();
  if (!/zamknięta/i.test(alert)) throw new Error(`case not closed: ${alert}`);
  await glide(page, page.locator('[data-report-links] a:has-text("PDF")'), { steps: 35, pause: 300 });
  const [download] = await Promise.all([page.waitForEvent('download'), page.locator('[data-report-links] a:has-text("PDF")').click()]);
  await page.waitForTimeout(900);
  await rec.stop();
  await download.saveAs(path.join(outDir, 'UI05_report.pdf'));
  await still('UI05_closed_still');

  // UI06: case list with severity badges (B-roll), once the background cases are analysed.
  for (let i = 0; i < 120; i++) {
    await page.goto(`${BASE}/cases`);
    // A case stays "Nowa" until its documents are analysed and the rules have run.
    if (await page.locator('table tbody .badge', { hasText: /^Nowa$/ }).count() === 0) break;
    await page.waitForTimeout(1500);
  }
  await page.goto(`${BASE}/cases`);
  await page.mouse.move(W - 120, H - 80);
  await rec.start('UI06_case_list');
  await page.waitForTimeout(800);
  await glide(page, page.locator('table tbody tr').first(), { steps: 50, pause: 1200 });
  await rec.stop();
  await still('UI06_case_list_still');

  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
