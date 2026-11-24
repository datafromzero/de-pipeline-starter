# de-pipeline-starter

The starter repository of the [datafromzero](https://datafromzero.github.io) Data Engineer track. You build one small
pipeline across the lessons: land data from an API and from files, stage it, load it without ever loading a line twice,
and test it. Everything runs on your own laptop (VS Code, Git, uv); GitHub Codespaces is the fallback.

Code is MIT (see `LICENSE`). The cafe-sales data in `mock_api_data/` and `source_files/` is CC BY 4.0:
credit datafromzero, https://datafromzero.github.io.

## Start

```bash
git clone https://github.com/datafromzero/de-pipeline-starter.git
cd de-pipeline-starter
uv sync
uv run check_environment.py
uv run pytest -q
```

In a codespace: open the repository on GitHub, choose Code, then Codespaces, then create one. The dev container
installs uv and runs `uv sync` for you; from lesson 16 on it also installs Java 21, which the Spark lesson needs. A codespace
created before that has no Java: fetch the new file with
`git show de-16-done:.devcontainer/devcontainer.json > .devcontainer/devcontainer.json`, open the Command Palette
and choose Codespaces: Rebuild Container. A stopped codespace is deleted after 30 days, so push your work.

Start the mock API in its own terminal and leave it running while you work:

```bash
uv run python mock_api.py
```

## Layout

```text
mock_api.py            the outside world: a sales API on localhost (a source you do not control)
mock_api_data/         the API's own database (orders and their lines); not yours to read
source_files/          two files a partner drops: products.csv and stores.csv
contracts/            what the data must be: the contract of order_lines, and the checks that come from it
src/pipeline/          your code, one module for each stage of the pipeline
tests/                 pytest tests
dbt/                   the dbt project: models, snapshots, macros, tests and the profiles (dev, scratch, ci, ci_defer)
sql/                   the physical design of the cafe tables and the layout experiment of DE12
ci/                    the script that the CI workflow runs: the dbt build from nothing
.github/workflows/     the CI workflow for pull requests
airflow/               Airflow in an environment of its own: the DAG, its tests and env.sh
spark/                 PySpark in an environment of its own (it needs Java): the jobs of the Spark lesson
scripts/               small scripts the lessons run (tour, arrivals, seed check, break the data, stage a day, partner files, fetch the app events)
data/raw/              landing zone 1: bytes exactly as they arrived (Git ignores what is inside)
data/staging/          landing zone 2: typed, cleaned tables
data/serving/          landing zone 3: what other people query
data/ci/               where the CI script builds, from nothing (Git ignores what is inside)
check_environment.py   tells you what is missing on your computer and how to fix it
```

Airflow lives in `airflow/`, with its own `pyproject.toml` and `uv.lock`, so that `uv sync` in the main folder stays
light and works on Windows. Set it up with `cd airflow`, `uv sync`, `source env.sh` and `uv run airflow db migrate`.
Airflow does not run natively on Windows: its documentation says it runs on POSIX-compliant operating systems and that on
Windows you can run it through WSL2 or Linux containers, so on Windows use a codespace or WSL2 for the Airflow lessons.
dbt (dbt-core with dbt-duckdb) is in the main environment: run it from the `dbt/` folder with `uv run dbt build`.
PySpark is in `spark/`, with its own `pyproject.toml` and `uv.lock`: it needs Java 17, 21 or 25 on your path (the dev container of lesson 16 installs 21), and `uv sync` there builds it from a source archive. Run its jobs from that folder, with `uv run python NAME.py`.

## Checkpoints

Each lesson names a tag, so that you can catch up or compare:

| Tag | What it holds |
| --- | --- |
| `de-01-start` | the starter as it is on first clone |
| `de-NN-done` | the repository after lesson NN, with the files that lesson saves |
| `de-NN-start` | the same commit as `de-(NN-1)-done` |

To catch up before lesson 3, run `git checkout de-03-start`. To return to your own work, `git switch -`. A checkout
replaces your files: commit or stash what you want to keep first.

## The mock API

`mock_api.py` uses only the Python standard library (`http.server`). The Python documentation says `http.server` is
not recommended for production, so this server binds to `127.0.0.1` only. Start it with
`uv run python mock_api.py` (options: `--port`, `--seed`, `--retry-after`, `--verbose`).

### The data

It serves the order lines of cafe-sales version 1 (3,287 lines of 1,800 orders, January 1 to June 30, 2026), and adds
what a live source has and a file does not:

- `updated_at`: the time the till posted the version of the line, five minutes after the order time, as
  `YYYY-MM-DD HH:MM:SS` in the cafes' local time (no time zone). All times in the API use this format.
- 12 corrected lines: each has a second version with a later `updated_at` and another `quantity`. One is the line with the
  extra zero (order item 6952, quantity 20 corrected to 2, two days later); the other 11 are chosen by the seed and
  get `quantity + 1` one to three days later. These changes exist only in the API, not in cafe-sales.
- `channel` (`counter` or `app`), invented and chosen by the seed for each order, on versions updated from
  2026-05-01 00:00:00 on.

### GET /order-lines

| Parameter | Meaning |
| --- | --- |
| `limit` | lines in a page, 1 to 100, default 100 |
| `cursor` | the `next_cursor` of the previous page; leave it out for the first page |
| `since` | only versions updated after this time (exclusive) |
| `until` | the world as of this time: versions updated up to this time (inclusive) |

A good answer is `200` with JSON: `{"data": [...], "next_cursor": "..."}`. `next_cursor` is `null` on the last page.
A cursor is opaque: pass it back as it is. The API serves the latest version of each line as of `until`, ordered by
`updated_at` and then `order_item_id`.

Fields of a line (a line is one row of `order_lines`):

| Field | Type | Notes |
| --- | --- | --- |
| `order_item_id` | integer | the key of the line |
| `order_id` | integer | |
| `ordered_at` | text | local time |
| `store_id` | integer | |
| `customer_id` | integer or `null` | `null` for a walk-in |
| `status` | text | `completed` or `canceled` |
| `payment_method` | text | `card`, `mobile` or `cash` |
| `product_id` | integer | |
| `quantity` | integer | |
| `discount_usd` | text | a decimal with two digits, such as `"0.00"` |
| `updated_at` | text | local time |
| `channel` | text | only on versions updated from 2026-05-01 on |

Other answers: `400` for a bad `limit`, `cursor`, `since` or `until`; `404` for any other path; `GET /health` answers
`{"status": "ok"}`.

### Faults, on purpose

Every fault is a pure function of the seed (default 2026), so a run reproduces. `uv run python scripts/seed_check.py`
prints where seed 2026 sits among 20 other seeds.

- **429 and 500.** For each page, the seed decides whether its first request fails (about 1 page in 10 gets a `429`
  with a `Retry-After` header of 1 second, about 1 in 20 a `500`), and whether the second request fails the same
  way (3 times in 10). The third request always succeeds, and a success resets the count for that page. A
  full pull of 33 pages with seed 2026 meets 5 failed requests: a 429 on page 4, a 500 twice on page 15 and a 429
  twice on page 21.
- **A repeated record.** One line is sent twice, as the last record of one page and the first of the next (for seed 2026
  the last line of page 10, `order_item_id` 6000). A full pull has 3,288 records of 3,287 lines.
- **A column added partway through.** From the 20th page of a full pull, records carry `channel`; the 20th page holds
  both kinds.
- **Corrections.** The 12 corrected lines above arrive twice over a full history, and once in a full pull (the latest
  version).

## Tests

`uv run pytest -q` runs the contract of the API and the tests of the lessons. They need no network: the tests start the
API themselves, on a free port, with `Retry-After: 0`.

## What this repository builds

The sales of a three-cafe chain, from a sales API and two partner files, into a DuckDB database: land the lines, stage them as
Parquet, build a star schema with dbt, test every model, and rebuild everything from nothing in CI. From a clean clone, run
`uv sync --locked` and then `bash ci/dbt_ci.sh`: it builds in a folder of its own, `data/ci/`, and ends with all 46 dbt nodes passing.
`bash scripts/clean_clone_check.sh` does the clone for you.

## The grain of each table

| Table | One row is | Key | Answers questions about |
| --- | --- | --- | --- |
| `stg_order_lines` | the newest version of one order line | `order_line_id` | nothing a reader asks: it renames and types the staged file |
| `stg_products` | one product on the menu | `product_id` | nothing a reader asks: a renamed copy of the staged products |
| `stg_stores` | one store | `store_id` | nothing a reader asks: a renamed copy of the staged stores |
| `int_order_lines_priced` | one order line, with its product's price and its amount | `order_line_id` | nothing a reader asks: the amount of each line, for the marts that sum it |
| `dim_product` | one version of a product (type 2) | `product_key` | what a product was and cost, and its category on a given date |
| `dim_store` | one store as it is now (type 1) | `store_key` | where a store is and when it opened |
| `fct_order_lines` | one order line, with the keys that were true when it was ordered | `order_line_id` | any question about lines: sales by store or by category as sold, by status |
| `fct_store_daily_sales` | one store and one day with a sale | `store_id` and `order_date` | sales by store and day, and how they trend |
| `fct_store_status_amounts` | one store | `store_id` | completed against canceled dollars of a store |
| `fct_store_discounts` | one store | `store_id` | list price, discounts and net amount of a store's completed lines |

## Why these keys

`order_line_id` is the sales API's own number, so a line that arrives twice replaces itself. The two dimensions have surrogate keys,
because a product changes category and its old lines must keep the category true when they were ordered. The store-day table has a
two-part key because its grain is two things.

## Backfill

To rebuild a past range, from `airflow/`: `uv run airflow backfill create --dag-id cafe_pipeline --from-date 2026-05-01 --to-date 2026-05-05 --max-active-runs 1`.
One run at a time, because DuckDB lets one process write. Every run loads by key, so a rerun changes nothing; prove it with
`uv run python scripts/range_fingerprint.py 2026-05-01 2026-05-05` before and after, and the two fingerprints must be equal.
If one run fails, read the last line of its error first, fix the cause, and run the same command with `--reprocess-behavior failed`:
it creates runs again only for the days that failed. Afterwards the fingerprint of the range must equal the one that a single
incremental load of the same days gives.

## Cost

The counts come from the CI build of 2026-11-24 (`bash ci/dbt_ci.sh`). A view stores nothing; a table is rebuilt in full on every run.

| Model | A run reads | A run writes | Needs a full rebuild when |
| --- | --- | --- | --- |
| `stg_order_lines` (view) | the staged file, 62,362 bytes, when something reads the view | nothing | never |
| `stg_products` (view) | the staged file of 16 products | nothing | never |
| `stg_stores` (view) | the staged file of 3 stores | nothing | never |
| `int_order_lines_priced` (incremental, merge on `order_line_id`) | the lines posted since the newest one it holds, and the 16 products | those lines: 3,287 on the first build | what a row means changes (`--full-refresh`) |
| `products_snapshot` (snapshot) | the partner's file | a row for each product that changed: 18 rows | never: a rebuilt snapshot loses its history |
| `dim_product` (table) | the 18 rows of the snapshot | 18 rows | every run |
| `dim_store` (table) | the 3 stores | 3 rows | every run |
| `fct_order_lines` (table) | 3,287 lines, 18 product versions, 3 stores | 3,287 rows | every run |
| `fct_store_daily_sales` (table) | 5 of the 10 columns of `int_order_lines_priced`, 167,636 bytes for 3,287 lines, and the 3 stores | 453 rows, one for each store and day | every run |
| `fct_store_status_amounts` (table) | 3 columns of the 3,287 lines of `int_order_lines_priced` | 3 rows | every run |
| `fct_store_discounts` (table) | 3,287 lines and 16 products | 3 rows | every run |

The bytes are DuckDB's, counted with BigQuery's type sizes, and BigQuery was not run. No price is used. The cheaper rewrite is for
`fct_store_daily_sales`: on a warehouse partition it by `order_date` and rebuild only the days a run changes.

## Known limits

- One writer: DuckDB lets one process write, so a backfill of 5 days is 5 runs in a row, never at once.
- A line is loaded late only because the load overlaps by one hour (DE4): a line posted with a time more than an hour before the
  newest line loaded is missed by the nightly load, and only a full replay finds it.
- The products come from one partner file whose history is invented (3 versions, 2 category moves), and the dollars are reconciled
  between two tables of this repository (3,286 completed lines, $22,625.75), not with the API.
- The star has no customer: a question about what a customer bought cannot be answered from it.
- Airflow needs Linux or WSL2, and the backfill was run in DE8, not again here.
