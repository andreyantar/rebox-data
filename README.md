# rebox-data

Открытые данные точек раздельного сбора отходов для приложения **ReBox**.

- `data/<city>/sites.json` — нормализованный список площадок (id, координаты, адрес, фракции, тип контейнера).
- `data/<city>/meta.json` — метаданные: источник, дата сбора, число точек, `sha256` текста `sites.json`.
- `data/<city>/raw.geojson` — сырая выгрузка источника.

Приложение тянет `meta.json`/`sites.json` напрямую с `raw.githubusercontent.com` и обновляет данные без релиза в стор (сверяет `sha256`).

`scripts/fetch_and_normalize.py` + GitHub Action (`refresh-data.yml`, еженедельно) перегенерируют и коммитят данные.

Города: **Калининград** (`kaliningrad`).
