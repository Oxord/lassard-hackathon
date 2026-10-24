# Трио · Луч ЛАССАРД · комплект после CP3

Для загрузки: презентация `pdf/trio-presentation.pdf` (13 слайдов), записка `pdf/trio-explanatory-note.pdf` (8 страниц), тизер `teaser.mp4` (30 секунд, 6 сцен) и `teaser.txt`.

Интерактивная презентация — `presentation.html`; изображения лежат в `assets/` (инфографика — `assets/infographics/`, планы для слайдов — `assets/slide-plan-*.png`, заглушки — `assets/placeholders/`). Общая страница материалов — `index.html`. При публикации эта папка размещается в `/solution/`, модель — в корне сайта.

Сборка: `python scripts/build_submission.py`, затем `node scripts/verify_submission.cjs` (число слайдов берётся из `submission/content.json`; проверяются белый фон, тег критерия, отсутствие запрещённых формулировок и скобок, кроме `[СМЕТА]`), затем `python scripts/build_teaser.py`.

Допущения — записка, разд. 8.

Публичные адреса: модель — https://oxord.github.io/lassard-hackathon/ , материалы — https://oxord.github.io/lassard-hackathon/solution/ . Перед передачей ссылок открыть их без авторизации. Подробнее: `docs/upload-instructions.md` в репозитории.
