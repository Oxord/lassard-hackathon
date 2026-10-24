const fs = require('node:fs/promises');
const path = require('node:path');
const http = require('node:http');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.LASSARD_PLAYWRIGHT || 'playwright');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'output');
const qa = path.join(root, 'tmp/submission-build/qa');

(async () => {
  await fs.mkdir(qa, { recursive: true });
  const server = http.createServer(async (req, res) => {
    try {
      let rel = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
      if (rel === '/qa/teaser-frames.html') {
        res.setHeader('Content-Type','text/html; charset=utf-8');
        res.end(await fs.readFile(path.join(root,'tmp/submission-build/teaser-frames.html')));return;
      }
      const base = rel.startsWith('/solution/') ? out : path.join(root, '3d/dist');
      rel = rel.startsWith('/solution/') ? rel.slice('/solution/'.length) : rel.replace(/^\/+/, '');
      if (!rel || rel.endsWith('/')) rel += 'index.html';
      const file = path.resolve(base, rel);
      if (!file.startsWith(base + path.sep)) throw Error('path');
      const types = { '.js': 'text/javascript', '.html': 'text/html; charset=utf-8', '.png': 'image/png', '.mp4': 'video/mp4', '.pdf': 'application/pdf', '.txt': 'text/plain; charset=utf-8' };
      res.setHeader('Content-Type', types[path.extname(file)] || 'application/octet-stream');
      const bytes=await fs.readFile(file);
      res.setHeader('Accept-Ranges','bytes');
      const range=/^bytes=(\d+)-(\d*)$/.exec(req.headers.range||'');
      if(range){
        const start=Number(range[1]),end=Math.min(bytes.length-1,range[2]?Number(range[2]):bytes.length-1);
        res.writeHead(206,{'Content-Range':`bytes ${start}-${end}/${bytes.length}`,'Content-Length':end-start+1});res.end(bytes.subarray(start,end+1));
      }else{res.setHeader('Content-Length',bytes.length);res.end(bytes);}
    } catch { res.statusCode = 404; res.end(); }
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  let browser;
  try {
    browser = await chromium.launch({ channel: 'msedge', headless: true });
    const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    const base = 'http://127.0.0.1:' + server.address().port;
    await page.goto(base + '/solution/presentation.html', { waitUntil: 'networkidle' });
    assert.equal(await page.locator('.slide').count(), 17);
    const imagesOk = await page.locator('img').evaluateAll(images => images.every(i => i.complete && i.naturalWidth));
    assert(imagesOk);
    await page.addStyleTag({ content: 'nav{display:none!important}' });
    const overflow = [];
    for (let i = 0; i < 17; i++) {
      const slide = page.locator('.slide').nth(i);
      const bad = await slide.evaluate(el => {
        const rect = el.getBoundingClientRect(); const footer = el.querySelector('footer').getBoundingClientRect();
        return [...el.querySelectorAll('h1,.lead,.copy,table')].filter(child => {
          const r = child.getBoundingClientRect();
          return r.right > rect.right-20 || r.left < rect.left || r.bottom > footer.top-8;
        }).map(el => el.tagName + ':' + el.className);
      });
      if (bad.length) overflow.push({ slide: i+1, elements: bad });
      await slide.screenshot({ path: path.join(qa, `html-slide-${String(i+1).padStart(2,'0')}.png`) });
    }
    await page.goto(base + '/solution/presentation.html', { waitUntil: 'networkidle' });
    await page.keyboard.press('ArrowRight'); await page.waitForTimeout(400);
    assert(await page.evaluate(() => window.scrollY > 500), 'slide keyboard navigation');
    await page.goto(base + '/qa/teaser-frames.html', { waitUntil: 'networkidle' });
    for(let i=0;i<6;i++)await page.locator('section').nth(i).screenshot({path:path.join(qa,`teaser-${i}.png`)});
    await page.goto(base + '/solution/', { waitUntil: 'networkidle' });
    if (await fs.stat(path.join(out,'teaser.mp4')).then(()=>true,()=>false)) {
      await page.waitForFunction(()=>document.querySelector('video').readyState>=1);
      assert.equal(await page.locator('video').evaluate(v=>Math.round(v.duration)),30);
      for(let i=0;i<6;i++){
        await page.locator('video').evaluate((v,t)=>{v.currentTime=t;},i*5+2.5);
        await page.waitForFunction(t=>{const v=document.querySelector('video');return !v.seeking&&v.readyState>=2&&Math.abs(v.currentTime-t)<.1;},i*5+2.5);
        await page.locator('video').screenshot({path:path.join(qa,`encoded-video-${i}.png`)});
      }
    }
    await page.setViewportSize({ width: 390, height: 844 });
    assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)), 'material page narrow layout');
    await page.screenshot({ path: path.join(qa, 'material-index.png'), fullPage: true });
    assert.deepEqual(errors, []);
    await fs.writeFile(path.join(qa,'html-checks.json'), JSON.stringify({ slides:17, imagesOk, overflow, keyboard:true, pageErrors:errors },null,2));
    console.log(JSON.stringify({slides:17,imagesOk,overflow,keyboard:true,pageErrors:errors}));
    if(overflow.length)process.exitCode=1;
  } finally {
    if(browser)await browser.close();await new Promise(r=>server.close(r));
  }
})().catch(e=>{console.error(e);process.exitCode=1;});
