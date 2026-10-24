"""Build the Trio HTML/PDF handoff from editable content and current model views.

Dependencies for PDFs: reportlab, pypdf. Assets: scripts/capture_submission.cjs.
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

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output'
ASSETS = OUT / 'assets'
PDF = OUT / 'pdf'
DATA = json.loads((ROOT / 'submission/content.json').read_text(encoding='utf-8'))
RED = '#c8102e'
DARK = '#14161a'
FONT_DIR = Path(os.environ.get('LASSARD_FONT_DIR', 'C:/Windows/Fonts'))


def esc(value):
    return html.escape(str(value))


def table_html(rows):
    return '<table>' + ''.join('<tr>' + ''.join(f'<{"th" if i == 0 else "td"}>{esc(c)}</{"th" if i == 0 else "td"}>' for c in row) + '</tr>' for i, row in enumerate(rows)) + '</table>'


CSS = '''
*{box-sizing:border-box}html{background:#111318;color:#14161a;font-family:Arial,sans-serif}body{margin:0}
.slide{width:1280px;height:720px;background:#f5f5f3;padding:44px 52px 38px;margin:28px auto;position:relative;overflow:hidden}
.slide h1{font-size:44px;line-height:1.08;margin:0 0 14px;max-width:1150px;font-weight:700}
.lead{font-size:28px;line-height:1.22;color:#a60e28;margin:0 0 26px;max-width:1120px}
.body{display:flex;gap:30px;align-items:flex-start}.copy{flex:1;min-width:0}.copy p{font-size:25px;line-height:1.3;margin:0 0 18px}
.body>img{width:680px;height:382px;object-fit:contain;background:#14161a}.no-image .copy{max-width:1060px}.no-image .copy p{font-size:31px;margin:0 0 25px}
.slide table{border-collapse:collapse;width:100%;font-size:24px;margin:18px 0}.slide td,.slide th{padding:15px 18px;border-bottom:1px solid #cbd0d4;text-align:left;vertical-align:top;line-height:1.22}.slide th{background:#14161a;color:white;font-size:23px}
.slide footer{position:absolute;left:52px;right:52px;bottom:23px;font-size:14px;line-height:1.3;color:#59616b;display:flex;gap:24px;align-items:flex-end}.slide footer span:first-child{flex:1}.page{white-space:nowrap}
.cover{background:#14161a;color:#fff}.cover h1{font-size:82px;margin-top:8px;position:relative;z-index:1}.cover .lead{color:#fff;font-size:35px;position:relative;z-index:1;max-width:1080px}.cover .copy p{font-size:28px;color:#fff;position:relative;z-index:1;max-width:1000px}.cover .body>img{position:absolute;inset:180px 0 0;width:1280px;height:540px;object-fit:cover;opacity:.55}.cover footer{color:#d0d4d8}.cover .copy{padding-top:6px}.cover .brand{color:#ff536a;font-size:22px;letter-spacing:3px;margin-bottom:18px}
.plan .body{display:block}.plan .body>img{width:1176px;height:405px;object-fit:contain;background:#fff}.plan .copy{display:flex;gap:28px}.plan .copy p{font-size:20px;flex:1;margin-top:8px}.plan .lead{margin-bottom:12px;font-size:25px}
.has-table .copy p{font-size:23px}.has-table .body{display:block}.has-table table{margin-top:0}.has-table td,.has-table th{padding:11px 16px}
nav{position:fixed;right:12px;bottom:10px;z-index:20;display:flex;gap:8px}nav button,nav a{background:#c8102e;color:white;border:0;padding:10px 16px;border-radius:4px;font:16px Arial;text-decoration:none;cursor:pointer}button:focus-visible,a:focus-visible{outline:3px solid #ffbf47;outline-offset:3px}
@media(max-width:1280px){.slide{margin:12px auto;transform-origin:top left}}
@media print{@page{size:1280px 720px;margin:0}html{background:white}.slide{margin:0;break-after:page;print-color-adjust:exact}.slide:last-of-type{break-after:auto}nav{display:none}}
'''


def build_html():
    slides = []
    for i, s in enumerate(DATA['slides'], 1):
        classes = 'slide' + (' cover' if s.get('cover') else '') + (' plan' if s.get('plan') else '') + (' no-image' if not s.get('image') else '') + (' has-table' if s.get('table') else '')
        picture = f'<img src="assets/{esc(s["image"])}" alt="{esc(s["title"])} — концептуальная модель">' if s.get('image') else ''
        body = ''.join(f'<p>{esc(p)}</p>' for p in s.get('body', []))
        if s.get('table'):
            body = table_html(s['table']) + body
        brand = '<div class="brand">ТРИО / ОТКРОЙ МОСПРОМ</div>' if s.get('cover') else ''
        slides.append(f'<section class="{classes}" id="slide-{i}">{brand}<h1>{esc(s["title"])}</h1><div class="lead">{esc(s.get("lead",""))}</div><div class="body">{picture}<div class="copy">{body}</div></div><footer><span>{esc(s["source"])}</span><span class="page">Трио · {i:02d} / 17</span></footer></section>')
    js = '''let current=0;const slides=[...document.querySelectorAll('.slide')];function go(delta){current=Math.max(0,Math.min(slides.length-1,current+delta));slides[current].scrollIntoView({behavior:'smooth',block:'start'});}document.querySelector('#prev').onclick=()=>go(-1);document.querySelector('#next').onclick=()=>go(1);document.querySelector('#print').onclick=()=>print();document.addEventListener('keydown',e=>{if(['ArrowRight','PageDown'].includes(e.key)){e.preventDefault();go(1);}if(['ArrowLeft','PageUp'].includes(e.key)){e.preventDefault();go(-1);}});new IntersectionObserver(entries=>{for(const e of entries)if(e.isIntersecting)current=slides.indexOf(e.target);},{threshold:.5}).observe(slides[0]);'''
    # Observe every slide so manual scrolling and buttons stay in sync.
    js = js.replace("new IntersectionObserver(entries=>", "const observer=new IntersectionObserver(entries=>").replace("}).observe(slides[0]);", "});slides.forEach(s=>observer.observe(s));")
    document = '<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=1280"><title>Трио — Путь станка</title><style>' + CSS + '</style><main>' + ''.join(slides) + '</main><nav aria-label="Управление презентацией"><button id="prev">←</button><button id="next">→</button><button id="print">Печать</button><a href="index.html">Материалы</a></nav><script>' + js + '</script></html>'
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


def pdf_table(rows, widths, size=17):
    formatted = [[Paragraph(esc(cell), pstyle('cell', size, '#fff' if i == 0 else DARK, bold=i == 0)) for cell in row] for i, row in enumerate(rows)]
    t = Table(formatted, colWidths=widths, hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor(DARK)),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10),('LINEBELOW',(0,1),(-1,-1),.6,colors.HexColor('#cbd0d4'))]))
    return t


def build_presentation_pdf():
    c = canvas.Canvas(str(PDF / 'trio-presentation.pdf'), pagesize=(960,540), pageCompression=1)
    c.setTitle('Трио — Путь станка — концепция шоурума ЛАССАРД')
    c.setAuthor('Команда Трио')
    for i,s in enumerate(DATA['slides'],1):
        cover = s.get('cover',False)
        background = DARK if cover else '#f5f5f3'
        foreground = '#ffffff' if cover else DARK
        c.setFillColor(colors.HexColor(background));c.rect(0,0,960,540,fill=1,stroke=0)
        if cover:
            image_fit(c,s['image'],0,45,960,370)
            c.setFillColor(colors.HexColor(DARK));c.rect(0,365,960,175,fill=1,stroke=0)
            top=para_draw(c,'ТРИО / ОТКРОЙ МОСПРОМ',38,516,884,17,'#ff536a',True)
            top=para_draw(c,s['title'],38,top-15,884,48,foreground,True)
            top=para_draw(c,s['lead'],38,top-12,884,26,foreground)
            for p in s.get('body',[]):
                top=para_draw(c,p,38,top-14,870,20,foreground)
        else:
            top=para_draw(c,s['title'],38,510,884,32,DARK,True)
            top=para_draw(c,s.get('lead',''),38,top-12,884,22,RED)
            if s.get('plan'):
                image_fit(c,s['image'],38,115,884,top-124)
                text=' '.join(s.get('body',[]))
                bottom=para_draw(c,text,38,103,884,13.5,DARK)
                if bottom<50:raise ValueError(f'Plan caption overflow on slide {i}')
            elif s.get('table'):
                widths=[884/len(s['table'][0])]*len(s['table'][0])
                table=pdf_table(s['table'],widths,17)
                _,h=table.wrap(884,500);table.drawOn(c,38,top-18-h); top-=h+30
                for p in s.get('body',[]):top=para_draw(c,p,38,top-10,884,17,DARK)
                if top<55:raise ValueError(f'Table overflow on slide {i}')
            else:
                if s.get('image'): image_fit(c,s['image'],38,100,520,top-105)
                x,width,size=(586,336,18) if s.get('image') else (38,850,24)
                cursor=top-22
                for p in s.get('body',[]):cursor=para_draw(c,p,x,cursor,width,size,DARK)-16
                if cursor<65:raise ValueError(f'Text overflow on slide {i}')
        para_draw(c,s['source'],38,40,805,9,'#d0d4d8' if cover else '#59616b')
        c.setFont('Arial',10);c.setFillColor(colors.HexColor('#d0d4d8' if cover else '#59616b'));c.drawRightString(922,24,f'Трио · {i:02d} / 17')
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
    links=[('../','Интерактивная 3D-модель'),('presentation.html','Презентация HTML · 17 слайдов'),('pdf/trio-presentation.pdf','Презентация PDF'),('pdf/trio-explanatory-note.pdf','Пояснительная записка PDF'),('teaser.mp4','Тизер MP4 · 30 секунд'),('teaser.txt','Текст тизера'),('trio-submission.zip','Весь комплект ZIP'),('https://github.com/Oxord/lassard-hackathon','Исходные материалы решения')]
    body=''.join(f'<a href="{esc(url)}">{esc(label)} <span>↗</span></a>' for url,label in links)
    page='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Трио · Путь станка · Материалы решения</title><style>*{box-sizing:border-box}body{margin:0;background:#f5f5f3;color:#14161a;font-family:Arial,sans-serif}main{max-width:1040px;margin:auto;padding:68px 28px}small{font-size:17px;color:#b50d2a;letter-spacing:2px}h1{font-size:clamp(42px,7vw,78px);line-height:1;margin:28px 0}p{font-size:21px;line-height:1.5;max-width:850px}.links{margin:36px 0;border-top:2px solid #14161a}.links a{display:flex;justify-content:space-between;gap:20px;padding:20px 0;border-bottom:1px solid #cbd0d4;color:#14161a;text-decoration:none;font-size:21px}.links a:hover{color:#c8102e}.status{font-size:16px;color:#59616b}video{width:100%;background:#14161a;margin-top:28px}a:focus-visible{outline:3px solid #c8102e}</style><main><small>ТРИО / ОТКРОЙ МОСПРОМ</small><h1>Путь станка</h1><p>Концепция шоурума ЛАССАРД: компоненты, компактное оборудование, образцы и задача посетителя.</p><div class="links">'''+body+'''</div><video controls preload="metadata" poster="assets/overview.png"><source src="teaser.mp4" type="video/mp4">Видео доступно по ссылке выше.</video><p class="status">Версия после CP2 · 24.10.2026. Планировка, входы и состав оборудования предлагаются командой. Инженерные решения требуют согласования. Стоимость не оценена.</p></main></html>'''
    (OUT/'index.html').write_text(page,encoding='utf-8')
    (OUT/'teaser.txt').write_text('Трио · «Путь станка»\n\nКонцепция шоурума ЛАССАРД связывает компоненты, компактное оборудование и задачу посетителя. Гость знакомится с процессами, сравнивает образцы и фиксирует следующий шаг в карте визита. В экспозиции предложены компактные установки, цифровой показ роботизации, учебные места и открытая зона обсуждения. Тизер показывает концептуальную модель после CP2; размеры, оборудование и защитные решения требуют согласования. Стоимость не оценена.\n',encoding='utf-8')


def build_teaser_html():
    slides=[]
    for i,s in enumerate(DATA['teaser']):
        slides.append(f'<section id="teaser-{i}" style="background-image:url(assets/{esc(s["image"])})"><div><small>ТРИО / ЛАССАРД</small><h1>{esc(s["title"])}</h1><p>{esc(s["text"])}</p></div><footer>Концептуальная модель · оборудование и защитные решения требуют согласования</footer></section>')
    private=ROOT/'tmp/submission-build';private.mkdir(parents=True,exist_ok=True)
    (private/'teaser-frames.html').write_text(('<!doctype html><html lang="ru"><meta charset="utf-8"><style>*{box-sizing:border-box}body{margin:0;background:#14161a;color:#fff;font-family:Arial}section{width:1280px;height:720px;background-size:cover;background-position:center;position:relative;overflow:hidden}section div{position:absolute;left:0;right:0;bottom:60px;padding:30px 48px;background:rgba(20,22,26,.94)}h1{font-size:46px;line-height:1.08;margin:12px 0}p{font-size:27px;margin:0;max-width:1140px}small{font-size:18px;color:#ff536a;letter-spacing:2px}footer{position:absolute;bottom:0;padding:18px 48px;font-size:15px;background:#14161a;width:100%;height:60px}</style>'+''.join(slides)+'</html>').replace('url(assets/','url(/solution/assets/'),encoding='utf-8')


def main():
    PDF.mkdir(parents=True,exist_ok=True)
    ASSETS.mkdir(parents=True,exist_ok=True)
    for name in ['plan-zones.png','plan-flows.png','plan-safety.png']:
        shutil.copyfile(ROOT/'plan'/name,ASSETS/name)
    for s in DATA['slides']:
        if s.get('image'):assert (ASSETS/s['image']).exists(),s['image']
    assert len(DATA['slides'])==17
    pdfmetrics.registerFont(TTFont('Arial',str(FONT_DIR/'arial.ttf')))
    pdfmetrics.registerFont(TTFont('ArialBold',str(FONT_DIR/'arialbd.ttf')))
    build_html();build_presentation_pdf();build_note_pdf();build_index();build_teaser_html()
    print('Built 17-slide HTML and PDF, explanatory note PDF, material index and teaser text')


if __name__=='__main__':main()
