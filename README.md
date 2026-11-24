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
