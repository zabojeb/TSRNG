# TSRNG FastAPI — MVP with Collectors

[Ссылка на скринкаст](https://storage.yandexcloud.net/tsrng-demo/screencast.mov)
[Презентация](https://storage.yandexcloud.net/tsrng-demo/1_merged.pdf)

## New endpoint
`POST /sources/collect-and-commit` — собирает листья из реальных источников (маяки, котировки, погода, вики/гитхаб, изображения) и сразу делает Commit.

### Пример запроса
```json
{
  "round_label": "tsrng",
  "leaf_size_bytes": 64,
  "counts": { "beacons":8, "quotes":32, "weather":16, "text":16, "images":8 },
  "beacons": { "generic": ["https://drand.cloudflare.com/public/latest"] },
  "quotes": {
    "coinbase": ["BTC-USD","ETH-USD"],
    "stooq": ["AAPL.US","MSFT.US","GOOGL.US"],
    "fx_base": ["USD"],
    "fx_symbols": ["EUR","GBP","JPY","RUB"]
  },
  "weather_locations": null,
  "textfeeds": { "wikipedia_en_limit": 100, "github_events": 100 },
  "images": ["https://upload.wikimedia.org/wikipedia/commons/3/3f/HST-SM4.jpeg"]
}
```
Ответ — такой же, как у `/rounds/commit`.

## Дополнительные API
- `POST /rounds/{round_id}/beacon` — фиксирует внешний сид и VDF-параметры (поддерживаются hex/base64/JSON от маяков).
- `POST /rounds/{round_id}/finalize` — выбирает листья, формирует Merkle-доказательства, вычисляет выход и запускает встроенный анализ случайности. В ответе поле `analysis` содержит результаты базовых тестов.
- `GET /rounds/{round_id}/output.txt` — возвращает текстовый файл (`0`/`1`) с результом заданной длины (например, 1 000 000 бит).
- `POST /rounds/{round_id}/random-range` — генерирует `count` уникальных чисел в диапазоне `[start, end]`, детерминированно на основе того же сид/меркл‑корня.
- `GET /rounds` — список раундов с этапами и метаданными.
- `GET /rounds/{round_id}/manifest` — полный JSON-манифест.
- `GET /rounds/{round_id}/analysis/latest` — последние результаты статистических тестов.
- `GET /rounds/{round_id}/analysis/history` / `GET /rounds/{round_id}/analysis/history/{entry}` — история повторных прогонов и подробные записи.
- `POST /analysis/round/{round_id}/heavy` — запуск тяжёлого теста (`dieharder`) над финальным выводом.
- `POST /analysis/round/{round_id}/compare` — сверка раунда с эталонными генераторами (Python random, os.urandom).
- `GET /rounds/{round_id}/raw/summary` и `GET /rounds/{round_id}/raw/{stream}/{index}` — доступ к зафиксированным источникам энтропии (с optional `include_raw=true` для base64-полезной нагрузки).
- `GET /rounds/{round_id}/random-range/history` — журнал всех запросов на генерацию диапазонов.
- `GET /rounds/{round_id}/selected` — карты выбранных индексов и метаданные листьев.
- `GET /rounds/{round_id}/vdf` — параметры VDF-проведения.
- `GET /rounds/{round_id}/package.zip` — готовый артефакт с листьями, доказательствами, VDF и (если включено) сырыми данными.
- `POST /analysis/round/{round_id}` — повторный запуск статистики по финальному выходу (с опциональным ограничением числа бит).
- `POST /analysis/sequence` — проверка произвольных последовательностей (поддерживаются `data_hex`, `data_base64`, `data_bits`, `data_numbers` с массивом байт или бит).
- `POST /analysis/upload` — загрузка файла с последовательностью (например, `output.bin`), опционально с `limit_bits`.
- `POST /verify` — проверка загруженного `package.zip`.

Параметры позволяют менять конфиг сборщика (`--config`), выключать загрузку артефакта (`--skip-artifact`) и настраивать VDF (`--vdf-T`, `--modulus-bits`).

## Анализ внешних последовательностей
- Пример запроса к `/analysis/sequence` с массивом байтов:
  ```json
  {
    "data_numbers": [12, 34, 56, 78, 90],
    "limit_bits": 40
  }
  ```
- Пример отправки битовой последовательности:
  ```json
  { "data_bits": "0101010011", "limit_bits": 10 }
  ```
- Генерация уникальных чисел из диапазона `[a, b]`:
  ```bash
  curl -X POST http://127.0.0.1:8000/rounds/<round_id>/random-range \
    -H "Content-Type: application/json" \
    -d '{"start": 1, "end": 100, "count": 10, "domain": "demo-draw"}'
  ```
  Ответ содержит `numbers`, а параметры запроса логируются в `data/rounds/<round_id>/random_ranges.jsonl`.
- Загрузка файла `output.bin` (1 000 000 бит) для анализа:
  ```bash
  curl -X POST "http://127.0.0.1:8000/analysis/upload?limit_bits=1000000" \
    -F "file=@output.bin;type=application/octet-stream"
  ```
  Ответ содержит поле `tests` с результатами базовых проверок (monobit, runs, block frequency и др.).
- Получение текстового файла с 1 000 000 бит:
  ```bash
  curl -o output_bits.txt http://127.0.0.1:8000/rounds/<round_id>/output.txt
  ```
  В файле будет строка из `0`/`1` длиной, равной `output_bits` из раунда.
- Просмотр журналов прозрачности:
  ```bash
  curl http://127.0.0.1:8000/rounds/<round_id>/manifest
  curl http://127.0.0.1:8000/rounds/<round_id>/analysis/latest
  curl http://127.0.0.1:8000/rounds/<round_id>/analysis/history
  curl http://127.0.0.1:8000/rounds/<round_id>/raw/summary
  curl "http://127.0.0.1:8000/rounds/<round_id>/random-range/history?limit=5"
  ```
- Запуск Dieharder на финальном выходе:
  ```bash
  curl -X POST http://127.0.0.1:8000/analysis/round/<round_id>/heavy \
    -H "Content-Type: application/json" \
    -d '{"test":"dieharder","dieharder_args":["-a","-g","201"]}'
  ```
  Возвращается результат, а подробный отчёт сохраняется в `data/rounds/<round_id>/analysis/heavy/`.
- Сравнение с базовыми ГСЧ:
  ```bash
  curl -X POST http://127.0.0.1:8000/analysis/round/<round_id>/compare \
    -H "Content-Type: application/json" \
    -d '{"baselines":["secrets","python_random"],"limit_bits":1000000}'
  ```
  В ответе — метрики текущего раунда и эталонных генераторов.

## Запуск Backend

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

## Frontend (RandomTrust UI)
React/Vite SPA находится в каталоге `frontend/` и предоставляет четыре страницы: «Главная», «Генерация», «Анализ», «Как это работает?». Интерфейс обращается к backend по прокси `/api`.

### Запуск
```bash
cd frontend
npm install
npm run dev
```

По умолчанию клиент доступен на `http://localhost:5173`. Все запросы к `/api/*` проксируются на `http://127.0.0.1:8000`.
