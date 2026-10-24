"""Инфографика для слайдов (16:9, 1920x1080): SVG + PNG в output/assets/infographics/.

Цифры и даты — дословно из facts/facts.md §1–3. Цвета бренда: красный DD191C
(brand-dna.pptx), серые; чёрный не используется.
Карта: внешние геоданные не подключаются; контуры России и Беларуси нарисованы
вручную по опорным координатам (собственная схематичная работа, лицензионных
ограничений нет). Не в масштабе.
PNG рендерится headless Chrome/Edge (cairo на Windows недоступен).
Запуск: python scripts/make_infographics.py
"""
import shutil
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

W, H = 1920, 1080
RED = "#DD191C"
INK = "#4A4A4A"
MID = "#7F7F7F"
LIGHT = "#E7E6E6"
PALE = "#F5F5F5"
WHITE = "#FFFFFF"
FONT = "Arial, Helvetica, sans-serif"
OUT = Path(__file__).resolve().parent.parent / "output" / "assets" / "infographics"
BROWSERS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "chromium", "chrome", "msedge",
)


def text(x, y, s, size=32, fill=INK, weight="normal", anchor="start"):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>')


def svg_doc(title, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}"><title>{escape(title)}</title>'
            f'<rect width="{W}" height="{H}" fill="{WHITE}"/>{body}</svg>')


def heading(s):
    return text(96, 130, s, 56, INK, "bold") + f'<rect x="96" y="152" width="120" height="8" fill="{RED}"/>'


def footnote(s):
    return text(96, 1020, s, 20, MID)


def wrap(s, limit):
    lines, line = [], ""
    for word in s.split():
        if line and len(line) + len(word) + 1 > limit:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    lines.append(line)
    return lines


def timeline():
    events = [
        ("2015", "Полный цикл производства; основание в Калуге", "Кейс ЛАССАРД, слайд 3; lassard.ru"),
        ("2021", "Победа в конкурсе Минпромторга на ОКР «Листопад» (08.11)", "kommersant.ru/doc/5065569"),
        ("2023", "Запуск производства в ОЭЗ «Технополис Москва» (весна)", "photonics.su"),
        ("03.2026", "Проект «Лазерный класс» (24.03)", "lassard.ru/news/laser-room"),
        ("05.2026", "17 моделей оборудования ЛАССАРД в реестре Минпромторга (26.05)", "mos.ru"),
    ]
    y = 500
    parts = [heading("История «Лассард»"),
             f'<rect x="96" y="{y - 3}" width="1728" height="6" fill="{LIGHT}"/>']
    step = 1728 / len(events)
    for i, (date, desc, src) in enumerate(events):
        cx = 96 + step * i + step / 2
        last = i == len(events) - 1
        parts.append(f'<circle cx="{cx}" cy="{y}" r="22" fill="{RED if last else WHITE}" stroke="{RED}" stroke-width="8"/>')
        parts.append(text(cx, y - 70, date, 54, RED, "bold", "middle"))
        lines = wrap(desc, 16)
        for j, ln in enumerate(lines):
            parts.append(text(cx, y + 90 + j * 38, ln, 28, INK, "normal", "middle"))
        parts.append(text(cx, y + 110 + len(lines) * 38, src, 20, MID, "normal", "middle"))
    parts.append(footnote("Источники: Кейс ЛАССАРД, слайд 3; lassard.ru; kommersant.ru; photonics.su; mos.ru."))
    return svg_doc("История Лассард", "".join(parts))


def numbers():
    tiles = [
        ("600+", "сотрудников", ""),
        ("14 400 м²", "производственных площадей", ""),
        ("30+", "видов станков", ""),
        ("100+", "оптико-механических изделий", ""),
        ("400+", "единиц оборудования в год", ""),
        ("80%", "локализации", ""),
        ("Реестр", "Минпромторга РФ", ""),
    ]
    parts = [heading("«Лассард» в цифрах")]
    tw, th, gap = 400, 330, 24
    for i, (big, small, note) in enumerate(tiles):
        row, col = divmod(i, 4)
        n_in_row = 4 if row == 0 else 3
        x0 = 96 + (1728 - (n_in_row * tw + (n_in_row - 1) * gap)) / 2
        x = x0 + col * (tw + gap)
        y = 230 + row * (th + gap)
        accent = i in (0, 1, 4)
        parts.append(f'<rect x="{x}" y="{y}" width="{tw}" height="{th}" fill="{PALE}"/>')
        parts.append(f'<rect x="{x}" y="{y}" width="10" height="{th}" fill="{RED if accent else MID}"/>')
        parts.append(text(x + 40, y + 140, big, 84 if len(big) < 7 else 64, RED if accent else INK, "bold"))
        for j, ln in enumerate(wrap(small, 20)):
            parts.append(text(x + 40, y + 200 + j * 40, ln, 32, INK))
        if note:
            for j, ln in enumerate(wrap(note, 40)):
                parts.append(text(x + 40, y + th - 50 + j * 24, ln, 18, MID))
    parts.append(footnote("Источник: Кейс ЛАССАРД, слайд 3."))
    return svg_doc("Лассард в цифрах", "".join(parts))


RUSSIA = [(28, 69.5), (33, 69.3), (41, 67), (44, 68.5), (53, 68.5), (60, 69), (68, 71), (73, 73),
          (80, 73), (87, 75), (100, 77), (113, 74), (130, 71), (140, 72), (160, 70), (170, 70),
          (180, 68), (180, 65), (178, 63), (165, 60), (163, 57), (156, 51), (155, 57), (160, 61),
          (150, 59), (140, 54), (135, 48), (131, 43), (127, 50), (120, 53), (108, 50), (98, 51),
          (88, 49), (80, 51), (70, 55), (61, 54), (55, 51), (47, 49), (47, 46), (48, 42), (40, 43),
          (37, 45), (38, 47), (39.5, 49), (35, 52), (32, 53), (31.5, 56), (28, 57), (28, 60),
          (30, 62), (30, 67)]
BELARUS = [(23.5, 51.5), (32, 52), (31.5, 53.5), (30, 55.5), (28, 56.2), (26, 55.7),
           (23.5, 53.9), (23.7, 52.5)]
MAP_LON0, MAP_LAT0, MAP_SX, MAP_SY = 20, 80, 7.6, 14.0   # схематичная проекция


def proj(lon, lat):
    return 560 + (lon - MAP_LON0) * MAP_SX, 190 + (MAP_LAT0 - lat) * MAP_SY


def poly(pts, fill):
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in (proj(*q) for q in pts))
    return f'<polygon points="{p}" fill="{fill}" stroke="{WHITE}" stroke-width="3" stroke-linejoin="round"/>'


def geo_map():
    parts = [heading("Где «Лассард»"), poly(RUSSIA, LIGHT), poly(BELARUS, MID)]
    # (город, подпись, lon, lat, y карточки); карточки слева внизу, выноски к точкам
    cities = [("Калуга", "старт, 2015", 36.26, 54.51, 260),
              ("Обнинск", "лазеры и компоненты", 36.6, 55.1, 390),
              ("Москва", "Технополис · Варшавское шоссе", 37.6, 55.75, 520)]
    card_x, card_w = 96, 400
    for name, sub, lon, lat, cy in cities:
        x, y = proj(lon, lat)
        parts.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{card_x + card_w}" y2="{cy + 43}" stroke="{MID}" stroke-width="2"/>')
        parts.append(f'<rect x="{card_x}" y="{cy}" width="{card_w}" height="86" fill="{WHITE}" stroke="{RED}" stroke-width="3"/>')
        parts.append(text(card_x + 16, cy + 38, name, 30, RED, "bold"))
        parts.append(text(card_x + 16, cy + 70, sub, 20, INK))
    for name, sub, lon, lat, cy in cities:
        x, y = proj(lon, lat)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="{RED}" stroke="{WHITE}" stroke-width="3"/>')
    bx, by = proj(27.5, 51.3)
    parts.append(text(bx, by + 36, "Беларусь", 24, MID, "bold", "middle"))
    parts.append(f'<rect x="1020" y="840" width="804" height="150" fill="{RED}"/>')
    parts.append(text(1422, 920, "Москва + 40 регионов + Беларусь", 46, WHITE, "bold", "middle"))
    parts.append(text(1422, 962, "поставки: Москва, 40 регионов России, экспорт в Беларусь", 22, WHITE, "normal", "middle"))
    parts.append(footnote("Не в масштабе. Источник: Кейс ЛАССАРД, слайд 3; lassard.ru/about/company."))
    return svg_doc("Карта присутствия", "".join(parts))


def cycle():
    # Диоды/источники ↔ площадки — ДОПУЩЕНИЕ по кейсу: Обнинск — лазеры и компоненты, Варшавка — лазеры.
    nodes = [("Кристалл", "выращивание", "Обнинск"),
             ("Квантрон / диод", "накачка", "Обнинск"),
             ("Источник", "лазер", "Варшавское ш. — волоконные; Обнинск — твердотельные"),
             ("Оптика", "оптомеханика", "Обнинск"),
             ("Станок", "резка · гравировка · сварка", "Технополис Москва")]
    y, bw, bh = 450, 290, 170
    gap = (1728 - 5 * bw) / 4
    mid_y = y + bh / 2
    parts = [heading("Полный цикл: от кристалла до станка"),
             f'<rect x="96" y="{mid_y - 6}" width="1728" height="12" fill="{RED}"/>',
             f'<polygon points="1824,{mid_y - 30} 1880,{mid_y} 1824,{mid_y + 30}" fill="{RED}"/>',
             text(96, 330, "Луч проходит весь путь на собственных площадках", 30, MID)]
    for i, (name, sub, site) in enumerate(nodes):
        x = 96 + i * (bw + gap)
        last = i == len(nodes) - 1
        parts.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="{RED if last else WHITE}" stroke="{RED}" stroke-width="6"/>')
        parts.append(text(x + bw / 2, y + 85, name, 30, WHITE if last else RED, "bold", "middle"))
        parts.append(text(x + bw / 2, y + 125, sub, 22, WHITE if last else INK, "normal", "middle"))
        parts.append(f'<line x1="{x + bw / 2}" y1="{y + bh}" x2="{x + bw / 2}" y2="{y + bh + 70}" stroke="{MID}" stroke-width="3"/>')
        parts.append(f'<rect x="{x}" y="{y + bh + 70}" width="{bw}" height="70" fill="{PALE}"/>')
        parts.append(f'<rect x="{x}" y="{y + bh + 70}" width="{bw}" height="8" fill="{MID}"/>')
        parts.append(text(x + bw / 2, y + bh + 120, site, 26, INK, "bold", "middle"))
    parts.append(footnote("Источник: lassard.ru/about/company, photonics.su."))
    return svg_doc("Цикл производства", "".join(parts))


def render_png(svg_path, png_path):
    browser = next((b for b in BROWSERS if shutil.which(b) or Path(b).exists()), None)
    if browser is None:
        sys.exit("Не найден Chrome/Edge для рендера PNG")
    subprocess.run([browser, "--headless", "--disable-gpu", "--hide-scrollbars",
                    f"--window-size={W},{H}", f"--screenshot={png_path}", svg_path.resolve().as_uri()],
                   check=True, capture_output=True, timeout=120)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, build in (("timeline", timeline), ("numbers", numbers), ("map", geo_map), ("cycle", cycle)):
        svg = OUT / f"{name}.svg"
        svg.write_text(build(), encoding="utf-8")
        render_png(svg, OUT / f"{name}.png")
        print("ok", name)


if __name__ == "__main__":
    main()
