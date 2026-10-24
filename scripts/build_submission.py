"""Build the Trio HTML/PDF handoff from editable content and current model views.

Dependencies for PDFs: reportlab, pypdf, Pillow; optional qrcode for the final slide.
Assets: scripts/capture_submission.cjs, scripts/make_infographics.py, scripts/deck_assets.py.
Run from the repository root with Python 3. Fonts default to Windows Arial;
set LASSARD_FONT_DIR to a directory containing arial.ttf and arialbd.ttf elsewhere.
"""
from pathlib import Path
import html
import json
import os
import re
import shutil

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.utils import ImageReader

from deck_assets import RED as BRAND_RED, INK, MID, LIGHT, PALE, asset_or_placeholder, plan_slide, qr_code

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output'
ASSETS = OUT / 'assets'
PDF = OUT / 'pdf'
DATA = json.loads((ROOT / 'submission/content.json').read_text(encoding='utf-8'))
SLIDE_COUNT = len(DATA['slides'])
# RED/DARK keep the explanatory note unchanged; the deck uses the brand palette from deck_assets.
RED = '#c8102e'
DARK = '#14161a'
FONT_DIR = Path(os.environ.get('LASSARD_FONT_DIR', 'C:/Windows/Fonts'))
PLAN_SLIDES = [('plan-zones.png', 'slide-plan-zones.png', False), ('plan-flows.png', 'slide-plan-flows.png', True), ('plan-safety.png', 'slide-plan-safety.png', False)]
PAGE_W, PAGE_H, MARGIN = 960, 540, 38
CONTENT_FLOOR = 48   # PDF content must end above the footer rule


def esc(value):
    return html.escape(str(value))


def footer_text(s):
    return f'{s["source"]} {DATA["assumption_note"]}.'


def page_label(i):
    return f'Трио · {i:02d} / {SLIDE_COUNT}'


def table_html(rows):
    return '<table>' + ''.join('<tr>' + ''.join(f'<{"th" if i == 0 else "td"}>{esc(c)}</{"th" if i == 0 else "td"}>' for c in row) + '</tr>' for i, row in enumerate(rows)) + '</table>'


CSS = '''
:root{--red:#DD191C;--ink:#4A4A4A;--mid:#7F7F7F;--light:#E7E6E6;--pale:#F5F5F5}
*{box-sizing:border-box}html{background:var(--light);color:var(--ink);font-family:Arial,sans-serif}body{margin:0}
.slide{width:1280px;height:720px;background:#fff;padding:22px 52px 0;margin:28px auto;position:relative;overflow:hidden;border-top:8px solid var(--red)}
.top{display:flex;justify-content:space-between;align-items:center;height:36px;margin-bottom:12px}
.tag{border:2px solid var(--red);color:var(--red);font-size:15px;font-weight:700;letter-spacing:1px;padding:5px 12px;text-transform:uppercase}
.logos{display:flex;gap:20px;align-items:center}.logos img{height:26px}
.slide h1{font-size:40px;line-height:1.08;margin:0 0 8px;font-weight:700}
.lead{font-size:25px;line-height:1.22;color:var(--red);margin:0 0 20px}
.body{display:flex;gap:32px;align-items:flex-start}.copy{flex:1;min-width:0}
.copy p{font-size:20px;line-height:1.3;margin:0 0 14px;padding-left:16px;border-left:4px solid var(--light)}
.copy p.note{font-size:15px;color:var(--mid);border:0;padding:0}
.image .body>img{width:746px;height:420px;object-fit:contain;background:var(--pale)}
.plan .body>img{width:920px;height:460px;object-fit:contain}.plan .copy p{font-size:16px}
.image-table .body>img{width:693px;height:400px;object-fit:contain}.image-table td,.image-table th{font-size:15px;padding:7px 10px}
.duo .pics{display:flex;gap:26px}.duo .pics img{width:575px;height:323px;object-fit:contain;background:var(--pale)}.duo .copy{margin-top:16px}
.slide table{border-collapse:collapse;width:100%;font-size:19px}.slide td,.slide th{padding:10px 14px;border-bottom:1px solid var(--light);text-align:left;vertical-align:top;line-height:1.22}.slide th{background:var(--light);color:var(--ink);font-size:17px;text-transform:uppercase;letter-spacing:.5px}
.table .copy{margin-top:18px}.table .copy p{font-size:20px}.table .body{display:block}
.budget .copy{flex:none;width:700px}.budget td,.budget th{padding:5px 10px;font-size:15px}.budget td:last-child,.budget th:last-child{width:70px;text-align:right}.budget tr:last-child td{font-weight:700;color:var(--red);border-bottom:0}.budget .copy p.note{margin-top:10px;font-size:15px;color:var(--ink)}
.steps{flex:1}.steps h2{font-size:19px;margin:0 0 14px;text-transform:uppercase;letter-spacing:.5px}.steps ol{list-style:none;margin:0;padding:0;counter-reset:s}.steps li{counter-increment:s;font-size:17px;line-height:1.28;margin:0 0 16px;padding-left:52px;position:relative}.steps li b{display:block;color:var(--red);font-size:17px;margin-bottom:2px}.steps li::before{content:counter(s);position:absolute;left:0;top:-4px;width:36px;height:36px;border-radius:50%;background:var(--red);color:#fff;font-weight:700;display:flex;align-items:center;justify-content:center}
.slide footer{position:absolute;left:52px;right:52px;bottom:14px;font-size:13px;line-height:1.3;color:var(--mid);display:flex;gap:24px;align-items:flex-end;border-top:1px solid var(--light);padding-top:8px}.slide footer span:first-child{flex:1}.page{white-space:nowrap}
.cover h1,.final h1{font-size:84px;margin-top:40px}.cover .lead,.final .lead{font-size:32px;max-width:600px}.cover .copy p,.final .copy p{font-size:20px;border:0;padding:0;max-width:560px}
.cover .body>img{position:absolute;right:52px;top:120px;width:560px;height:315px;object-fit:cover}
.final .body>img{position:absolute;right:90px;top:130px;width:300px;height:300px}
.beam{position:absolute;left:0;right:0;bottom:92px;height:10px;background:var(--red)}
nav{position:fixed;right:12px;bottom:10px;z-index:20;display:flex;gap:8px}nav button,nav a{background:var(--red);color:#fff;border:0;padding:10px 16px;border-radius:4px;font:16px Arial;text-decoration:none;cursor:pointer}button:focus-visible,a:focus-visible{outline:3px solid var(--ink);outline-offset:3px}
@media print{@page{size:1280px 720px;margin:0}html{background:#fff}.slide{margin:0;break-after:page;print-color-adjust:exact}.slide:last-of-type{break-after:auto}nav{display:none}}
'''


def slide_body_html(s):
    layout = s['layout']
    paras = ''.join(f'<p>{esc(p)}</p>' for p in s.get('body', []))
    if s.get('note'):
        paras += f'<p class="note">{esc(s["note"])}</p>'
    picture = f'<img src="assets/{esc(s["image"])}" alt="{esc(s["title"])}">' if s.get('image') else ''
    if layout == 'duo':
        pics = ''.join(f'<img src="assets/{esc(name)}" alt="{esc(s["title"])}">' for name in s['images'])
        return f'<div class="pics">{pics}</div><div class="copy">{paras}</div>'
    if layout == 'table':
        return f'<div class="body"><div class="copy">{table_html(s["table"])}</div><div class="copy">{paras}</div></div>'
    if layout == 'budget':
        steps = ''.join(f'<li><b>{esc(q["queue"])}</b>{esc(q["text"])}</li>' for q in s['roadmap'])
        return f'<div class="body"><div class="copy">{table_html(s["table"])}<p class="note">{esc(s["note"])}</p></div><div class="steps"><h2>{esc(s["roadmap_title"])}</h2><ol>{steps}</ol></div></div>'
    if layout == 'image-table':
        return f'<div class="body">{picture}<div class="copy">{table_html(s["table"])}</div></div>'
    beam = '<div class="beam"></div>' if layout in ('cover', 'final') else ''
    return f'<div class="body">{picture}<div class="copy">{paras}</div></div>{beam}'


def build_html(logos):
    logo_html = ''.join(f'<img src="assets/{esc(name)}" alt="{esc(label)}">' for name, label in logos)
    slides = []
    for i, s in enumerate(DATA['slides'], 1):
        slides.append(f'<section class="slide {esc(s["layout"])}" id="slide-{i}"><div class="top"><span class="tag">{esc(s["tag"])}</span><div class="logos">{logo_html}</div></div><h1>{esc(s["title"])}</h1><div class="lead">{esc(s.get("lead", ""))}</div>{slide_body_html(s)}<footer><span>{esc(footer_text(s))}</span><span class="page">{page_label(i)}</span></footer></section>')
    js = '''let current=0;const slides=[...document.querySelectorAll('.slide')];function go(delta){current=Math.max(0,Math.min(slides.length-1,current+delta));slides[current].scrollIntoView({behavior:'smooth',block:'start'});}document.querySelector('#prev').onclick=()=>go(-1);document.querySelector('#next').onclick=()=>go(1);document.querySelector('#print').onclick=()=>print();document.addEventListener('keydown',e=>{if(['ArrowRight','PageDown'].includes(e.key)){e.preventDefault();go(1);}if(['ArrowLeft','PageUp'].includes(e.key)){e.preventDefault();go(-1);}});const observer=new IntersectionObserver(entries=>{for(const e of entries)if(e.isIntersecting)current=slides.indexOf(e.target);},{threshold:.5});slides.forEach(s=>observer.observe(s));'''
    document = f'<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=1280"><title>Трио — {esc(DATA["title"])}</title><style>' + CSS + '</style><main>' + ''.join(slides) + '</main><nav aria-label="Управление презентацией"><button id="prev">←</button><button id="next">→</button><button id="print">Печать</button><a href="index.html">Материалы</a></nav><script>' + js + '</script></html>'
    (OUT / 'presentation.html').write_text(document, encoding='utf-8')


def pstyle(name, size, color=DARK, leading=None, bold=False):
    if color == '#fff': color = '#ffffff'
    return ParagraphStyle(name, fontName='ArialBold' if bold else 'Arial', fontSize=size, leading=leading or size*1.28, textColor=colors.HexColor(color), alignment=TA_LEFT, spaceAfter=0)


def para_draw(c, text, x, top, width, size=18, color=DARK, bold=False):
    p = Paragraph(esc(text), pstyle('p', size, color, bold=bold))
    _, height = p.wrap(width, 2000)
    p.drawOn(c, x, top-height)
    return top-height


def image_fit(c, name, x, y, w, h):
    image = ImageReader(str(ASSETS / name))
    iw, ih = image.getSize()
    ratio = min(w/iw, h/ih)
    dw, dh = iw*ratio, ih*ratio
    c.drawImage(image, x+(w-dw)/2, y+(h-dh)/2, dw, dh, mask='auto')
    return y+(h-dh)/2


def pdf_table(rows, widths, size=14, total_row=False, right_col=False):
    formatted = [[Paragraph(esc(cell), pstyle('cell', size, INK, bold=i == 0 or (total_row and i == len(rows)-1))) for cell in row] for i, row in enumerate(rows)]
    t = Table(formatted, colWidths=widths, hAlign='LEFT')
    style = [('BACKGROUND',(0,0),(-1,0),colors.HexColor(LIGHT)),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,1),(-1,-1),.6,colors.HexColor(LIGHT))]
    if right_col:
        style.append(('ALIGN',(-1,0),(-1,-1),'RIGHT'))
    if total_row:
        style.append(('TEXTCOLOR',(0,-1),(-1,-1),colors.HexColor(BRAND_RED)))
    t.setStyle(TableStyle(style))
    return t


def draw_table(c, rows, x, top, widths, size, slide_no, total_row=False, right_col=False):
    table = pdf_table(rows, widths, size, total_row, right_col)
    _, h = table.wrap(sum(widths), 500)
    table.drawOn(c, x, top-h)
    if top-h < CONTENT_FLOOR: raise ValueError(f'Table overflow on slide {slide_no}')
    return top-h


def draw_paragraphs(c, paras, x, top, width, size, slide_no, rule=True):
    cursor = top
    for p in paras:
        bottom = para_draw(c, p, x+(10 if rule else 0), cursor, width-(10 if rule else 0), size, INK)
        if rule:
            c.setFillColor(colors.HexColor(LIGHT)); c.rect(x, bottom, 3, cursor-bottom, fill=1, stroke=0)
        cursor = bottom-size*.6
    if cursor < CONTENT_FLOOR: raise ValueError(f'Text overflow on slide {slide_no}')
    return cursor


def draw_chrome(c, s, i, logos):
    c.setFillColor(colors.white); c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(colors.HexColor(BRAND_RED)); c.rect(0, PAGE_H-6, PAGE_W, 6, fill=1, stroke=0)
    tag = s['tag'].upper()
    width = pdfmetrics.stringWidth(tag, 'ArialBold', 10.5)+18
    c.setStrokeColor(colors.HexColor(BRAND_RED)); c.setLineWidth(1.4); c.rect(MARGIN, PAGE_H-42, width, 21, fill=0, stroke=1)
    c.setFillColor(colors.HexColor(BRAND_RED)); c.setFont('ArialBold', 10.5); c.drawString(MARGIN+9, PAGE_H-35, tag)
    x = PAGE_W-MARGIN
    for name, _ in reversed(logos):
        iw, ih = ImageReader(str(ASSETS/name)).getSize()
        w = 19*iw/ih; x -= w
        c.drawImage(str(ASSETS/name), x, PAGE_H-41, w, 19, mask='auto'); x -= 15
    c.setStrokeColor(colors.HexColor(LIGHT)); c.setLineWidth(.8); c.line(MARGIN, 36, PAGE_W-MARGIN, 36)
    para_draw(c, footer_text(s), MARGIN, 31, 790, 8.5, MID)
    c.setFont('Arial', 9.5); c.setFillColor(colors.HexColor(MID)); c.drawRightString(PAGE_W-MARGIN, 22, page_label(i))


def draw_cover(c, s, i):
    top = para_draw(c, s['title'], MARGIN, 450, 440, 60, INK, True)
    top = para_draw(c, s['lead'], MARGIN, top-14, 440, 24, BRAND_RED)
    for p in s.get('body', []):
        top = para_draw(c, p, MARGIN, top-14, 440, 15.5, INK)
    if s['layout'] == 'final':
        image_fit(c, s['image'], 690, 210, 205, 205)
    else:
        image_fit(c, s['image'], 500, 196, 422, 237)
    c.setFillColor(colors.HexColor(BRAND_RED)); c.rect(0, 72, PAGE_W, 7, fill=1, stroke=0)
    if top < 90: raise ValueError(f'Cover overflow on slide {i}')


def draw_content(c, s, i):
    top = para_draw(c, s['title'], MARGIN, PAGE_H-54, 884, 29, INK, True)
    top = para_draw(c, s.get('lead', ''), MARGIN, top-6, 884, 18.5, BRAND_RED) - 14
    layout, body = s['layout'], s.get('body', [])
    if layout == 'image':
        image_fit(c, s['image'], MARGIN, top-315, 560, 315)
        cursor = draw_paragraphs(c, body, 620, top, 302, 15, i)
        if s.get('note'): draw_paragraphs(c, [s['note']], 620, cursor-4, 302, 11, i, rule=False)
    elif layout == 'plan':
        image_fit(c, s['image'], MARGIN, top-345, 690, 345)
        draw_paragraphs(c, body, 744, top, 178, 12.5, i)
    elif layout == 'image-table':
        image_fit(c, s['image'], MARGIN, top-300, 520, 300)
        draw_table(c, s['table'], 578, top, [112, 232], 11.5, i)
    elif layout == 'duo':
        for k, name in enumerate(s['images']):
            image_fit(c, name, MARGIN+k*452, top-243, 432, 243)
        draw_paragraphs(c, body, MARGIN, top-258, 884, 15, i)
    elif layout == 'table':
        bottom = draw_table(c, s['table'], MARGIN, top, [380, 504], 15.5, i)
        draw_paragraphs(c, body, MARGIN, bottom-20, 884, 15.5, i)
    elif layout == 'budget':
        bottom = draw_table(c, s['table'], MARGIN, top, [450, 66], 11.5, i, total_row=True, right_col=True)
        draw_paragraphs(c, [s['note']], MARGIN, bottom-10, 516, 11.5, i, rule=False)
        para_draw(c, s['roadmap_title'].upper(), 596, top, 326, 12.5, INK, True)
        cursor = top-30
        for k, q in enumerate(s['roadmap'], 1):
            c.setFillColor(colors.HexColor(BRAND_RED)); c.circle(609, cursor-8, 13, fill=1, stroke=0)
            c.setFillColor(colors.white); c.setFont('ArialBold', 13); c.drawCentredString(609, cursor-12.5, str(k))
            cursor = para_draw(c, q['queue'], 634, cursor, 288, 12.5, BRAND_RED, True)-3
            cursor = para_draw(c, q['text'], 634, cursor, 288, 12, INK)-18
        if cursor < CONTENT_FLOOR: raise ValueError(f'Roadmap overflow on slide {i}')
    else:
        raise ValueError(f'Unknown layout {layout} on slide {i}')


def build_presentation_pdf(logos):
    c = canvas.Canvas(str(PDF / 'trio-presentation.pdf'), pagesize=(PAGE_W, PAGE_H), pageCompression=1)
    c.setTitle(f'Трио — {DATA["title"]} — концепция шоурума ЛАССАРД')
    c.setAuthor('Команда Трио')
    for i, s in enumerate(DATA['slides'], 1):
        draw_chrome(c, s, i, logos)
        if s['layout'] in ('cover', 'final'):
            draw_cover(c, s, i)
        else:
            draw_content(c, s, i)
        c.showPage()
    c.save()


def build_note_pdf():
    body=(ROOT/'submission/explanatory-note.md').read_text(encoding='utf-8')
    sections=re.split(r'^## ',body,flags=re.M)[1:]
    story=[]
    title=pstyle('heading',21,DARK,27,True)
    text=pstyle('body',11,DARK,16)
    for i,section in enumerate(sections):
        heading,_,rest=section.partition('\n')
        if i:story.append(PageBreak())
        story.append(Paragraph('ТРИО / ПУТЬ СТАНКА',pstyle('brand',11,RED,bold=True)))
        story.append(Spacer(1,14));story.append(Paragraph(esc(heading),title));story.append(Spacer(1,20))
        for p in rest.strip().split('\n\n'):
            if p.startswith('###'):
                story.append(Paragraph(esc(p.lstrip('# ').strip()),pstyle('sub',14,DARK,19,True)));story.append(Spacer(1,8));continue
            if p.startswith('|'):
                rows=[[c.strip() for c in line.strip().strip('|').split('|')] for line in p.split('\n') if not set(line)<=set('|-: ')]
                small=pstyle('cell',8.5,DARK,11)
                data=[[Paragraph(esc(c),pstyle('cellh',8.5,DARK,11,True) if r==0 else small) for c in row] for r,row in enumerate(rows)]
                t=Table(data,colWidths=[100,45,60,298.28],repeatRows=1)
                t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E7E6E6')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.5,colors.HexColor('#cbd0d4')),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
                story.append(t);story.append(Spacer(1,11));continue

            # HTML line breaks help long source URLs stay within the page.
            safe=esc(p.replace('\n',' '))
            story.append(Paragraph(safe,text));story.append(Spacer(1,11))
        if i in (2,4):
            name='plan-zones.png' if i==2 else 'overview.png'
            from PIL import Image as PillowImage
            w,h=PillowImage.open(ASSETS/name).size
            story.append(Image(str(ASSETS/name),width=470,height=470*h/w))
    def footer(c,doc):
        c.setFont('Arial',8);c.setFillColor(colors.HexColor('#626a73'))
        c.drawString(45,30,'Трио · Концепция после CP2 · 24.10.2026')
        c.drawRightString(550,30,str(doc.page))
    doc=SimpleDocTemplate(str(PDF/'trio-explanatory-note.pdf'),pagesize=(595.28,841.89),rightMargin=45,leftMargin=45,topMargin=44,bottomMargin=50,title='Трио — Путь станка — пояснительная записка',author='Команда Трио')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)


def build_index():
    links=[('../','Интерактивная 3D-модель'),('presentation.html',f'Презентация HTML · {SLIDE_COUNT} слайдов'),('pdf/trio-presentation.pdf','Презентация PDF'),('pdf/trio-explanatory-note.pdf','Пояснительная записка PDF'),('teaser.mp4','Тизер MP4 · 30 секунд'),('teaser.txt','Текст тизера'),('trio-submission.zip','Весь комплект ZIP'),('https://github.com/Oxord/lassard-hackathon','Исходные материалы решения')]
    body=''.join(f'<a href="{esc(url)}">{esc(label)} <span>↗</span></a>' for url,label in links)
    page=f'''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Трио · {esc(DATA["title"])} · Материалы решения</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#fff;color:{INK};font-family:Arial,sans-serif;border-top:8px solid {BRAND_RED}}}main{{max-width:1040px;margin:auto;padding:68px 28px}}small{{font-size:17px;color:{BRAND_RED};letter-spacing:2px}}h1{{font-size:clamp(42px,7vw,78px);line-height:1;margin:28px 0}}p{{font-size:21px;line-height:1.5;max-width:850px}}.links{{margin:36px 0;border-top:2px solid {BRAND_RED}}}.links a{{display:flex;justify-content:space-between;gap:20px;padding:20px 0;border-bottom:1px solid {LIGHT};color:{INK};text-decoration:none;font-size:21px}}.links a:hover{{color:{BRAND_RED}}}.status{{font-size:16px;color:{MID}}}video{{width:100%;background:{PALE};margin-top:28px}}a:focus-visible{{outline:3px solid {BRAND_RED}}}</style><main><small>ТРИО / ОТКРОЙ МОСПРОМ</small><h1>{esc(DATA["title"])}</h1><p>Концепция шоурума ЛАССАРД: идите по лучу — от кристалла до станка и до стекла в цех.</p><div class="links">'''+body+f'''</div><video controls preload="metadata" poster="assets/overview.png"><source src="teaser.mp4" type="video/mp4">Видео доступно по ссылке выше.</video><p class="status">{esc(DATA["version"])}. {esc(DATA["assumption_note"])}.</p></main></html>'''
    (OUT/'index.html').write_text(page,encoding='utf-8')
    scenes=' '.join(f'{s["title"]}: {s["text"]}.' for s in DATA['teaser'])
    (OUT/'teaser.txt').write_text(f'Трио · «{DATA["title"]}»\n\nКонцепция шоурума ЛАССАРД: красный луч ведёт гостя от кристалла до станка. {scenes} Тизер показывает концептуальную 3D-модель команды; {DATA["assumption_note"].lower()}.\n',encoding='utf-8')


def build_teaser_html():
    slides=[]
    for i,s in enumerate(DATA['teaser']):
        slides.append(f'<section id="teaser-{i}" style="background-image:url(assets/{esc(s["image"])})"><div><small>ТРИО / ЛАССАРД</small><h1>{esc(s["title"])}</h1><p>{esc(s["text"])}</p></div><footer>Трио · {esc(DATA["title"])} · концептуальная 3D-модель</footer></section>')
    private=ROOT/'tmp/submission-build';private.mkdir(parents=True,exist_ok=True)
    style=f'*{{box-sizing:border-box}}body{{margin:0;background:#fff;color:{INK};font-family:Arial}}section{{width:1280px;height:720px;background-size:cover;background-position:center;position:relative;overflow:hidden}}section div{{position:absolute;left:0;right:0;bottom:60px;padding:30px 48px;background:rgba(255,255,255,.94);border-left:12px solid {BRAND_RED}}}h1{{font-size:46px;line-height:1.08;margin:12px 0}}p{{font-size:27px;margin:0;max-width:1140px}}small{{font-size:18px;color:{BRAND_RED};letter-spacing:2px}}footer{{position:absolute;bottom:0;padding:18px 48px;font-size:15px;color:{MID};background:#fff;width:100%;height:60px;border-top:6px solid {BRAND_RED}}}'
    (private/'teaser-frames.html').write_text(('<!doctype html><html lang="ru"><meta charset="utf-8"><style>'+style+'</style>'+''.join(slides)+'</html>').replace('url(assets/','url(/solution/assets/'),encoding='utf-8')


def prepare_assets():
    """Derived plans, QR code and logos (or placeholders); returns [(asset name, label)] for logos."""
    for name in ['plan-zones.png','plan-flows.png','plan-safety.png']:
        shutil.copyfile(ROOT/'plan'/name,ASSETS/name)
    for src, dst, legend in PLAN_SLIDES:
        plan_slide(ROOT/'plan'/src, ASSETS/dst, FONT_DIR, legend)
    if not qr_code(DATA['pages_url'], ASSETS/'qr-pages.png'):
        print('qrcode package missing: QR placeholder used')
    logos = [(asset_or_placeholder(ASSETS, logo['file'], logo['label'], (480, 120), FONT_DIR), logo['label']) for logo in DATA['logos']]
    for s in DATA['slides']:
        if s.get('image'): s['image'] = asset_or_placeholder(ASSETS, s['image'], s['title'], (1280, 720), FONT_DIR)
        if s.get('images'): s['images'] = [asset_or_placeholder(ASSETS, name, s['title'], (1280, 720), FONT_DIR) for name in s['images']]
    return logos


def main():
    PDF.mkdir(parents=True,exist_ok=True)
    ASSETS.mkdir(parents=True,exist_ok=True)
    pdfmetrics.registerFont(TTFont('Arial',str(FONT_DIR/'arial.ttf')))
    pdfmetrics.registerFont(TTFont('ArialBold',str(FONT_DIR/'arialbd.ttf')))
    logos=prepare_assets()
    for s in DATA['slides']:
        assert s.get('tag'), f'missing tag: {s["title"]}'
    build_html(logos);build_presentation_pdf(logos);build_note_pdf();build_index();build_teaser_html()
    print(f'Built {SLIDE_COUNT}-slide HTML and PDF, explanatory note PDF, material index and teaser text')


if __name__=='__main__':main()
