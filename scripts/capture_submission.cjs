// npm dependencies: the existing local Playwright installation used for visual QA.
const fs = require('node:fs/promises');
const path = require('node:path');
const http = require('node:http');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.LASSARD_PLAYWRIGHT || 'playwright');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'output', 'assets');
const dist = path.join(root, '3d', 'dist');

(async () => {
  await fs.mkdir(out, { recursive: true });
  const server = http.createServer(async (req, res) => {
    try {
      let rel = new URL(req.url, 'http://localhost').pathname.replace(/^\/+/, '');
      if (!rel) rel = 'index.html';
      const file = path.resolve(dist, rel);
      if (!file.startsWith(dist + path.sep)) throw Error('path');
      res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript' : 'text/html; charset=utf-8');
      res.end(await fs.readFile(file));
    } catch { res.statusCode = 404; res.end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  const errors = [];
  try {
    browser = await chromium.launch({ channel: 'msedge', headless: true, args: ['--enable-unsafe-swiftshader'] });
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
    page.on('pageerror', error => errors.push(error.message));
    const base = 'http://127.0.0.1:' + server.address().port + '/';
    await page.goto(base, { waitUntil: 'networkidle' });
    await page.waitForFunction(() => window.__renderAt && document.querySelector('canvas'));
    for (const button of await page.locator('#bar-scn button[data-id]').all()) {
      await button.click();
      assert(await button.evaluate(el => el.classList.contains('on')));
    }
    await page.getByRole('button', { name: 'Все зоны', exact: true }).click();
    await page.addStyleTag({ content: '#controls,#bar-top,#bar-scn,#hint,#caption,#card{display:none!important}' });
    await page.screenshot({ path: path.join(out, 'overview.png') });
    await page.evaluate(() => document.querySelector('#btn-top').click());
    await page.waitForTimeout(250);
    await page.screenshot({ path: path.join(out, 'top.png') });
    await page.goto(base + '?tour=1&clean=1', { waitUntil: 'networkidle' });
    await page.waitForFunction(() => window.__renderAt);
    await page.addStyleTag({ content: '#caption{display:none!important}' });
    for (const [name, t] of [['components',12],['optics',28],['cutting',32],['marking',36],['samples',44],['booth',48],['classroom',56],['discussion',64]]) {
      await page.evaluate(t => window.__renderAt(t), t);
      await page.screenshot({ path: path.join(out, name + '.png') });
    }
    assert.deepEqual(errors, []);
    await fs.writeFile(path.join(root, 'tmp/submission-build/browser-checks.json'), JSON.stringify({ scenarios: 4, screenshots: 10, pageErrors: errors }, null, 2));
    console.log('10 model views captured; 4 scenarios checked; no JavaScript errors');
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
