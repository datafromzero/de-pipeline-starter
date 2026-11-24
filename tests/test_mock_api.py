"""The contract of the mock API (see README.md): the numbers a lesson prints rest on these."""

import base64

import mock_api
import requests


def cursor(offset):
    return base64.urlsafe_b64encode(f"o:{offset}".encode()).decode()


def pull_all(get_page, **params):
    """Follow next_cursor to the end; return the records of every page."""
    pages, token = [], None
    while True:
        extra = {"cursor": token} if token else {}
        body = get_page(**params, **extra).json()
        pages.append(body["data"])
        token = body["next_cursor"]
        if token is None:
            return pages


def test_health(api_url):
    assert requests.get(f"{api_url}/health", timeout=10).json() == {"status": "ok"}


def test_a_full_pull_has_33_pages_and_3288_records_of_3287_lines(get_page):
    pages = pull_all(get_page)
    records = [r for page in pages for r in page]
    assert len(pages) == 33
    assert len(records) == 3288
    assert len({r["order_item_id"] for r in records}) == 3287


def test_the_repeated_record_ends_one_page_and_starts_the_next(get_page):
    pages = pull_all(get_page)
    repeats = [i for i in range(len(pages) - 1) if pages[i][-1] == pages[i + 1][0]]
    assert len(repeats) == 1


def test_a_column_is_added_partway_through(get_page):
    pages = pull_all(get_page)
    with_channel = [i for i, page in enumerate(pages) if any("channel" in r for r in page)]
    without_channel = [i for i, page in enumerate(pages) if any("channel" not in r for r in page)]
    assert with_channel[0] == 19  # the 20th page, the first one that holds a record updated from 2026-05-01
    assert without_channel[-1] == with_channel[0]  # the page where it appears holds both kinds


def test_the_faults_follow_the_seed():
    plan = [mock_api.planned_fault(2026, offset, 0) for offset in range(0, 3300, 100)]
    assert plan.count(429) == 2 and plan.count(500) == 1
    assert [mock_api.planned_fault(2026, 1400, n) for n in range(3)] == [500, 500, None]
    assert mock_api.planned_fault(2026, 1400, 0) == mock_api.planned_fault(2026, 1400, 0)


def test_a_429_carries_retry_after_and_a_500_does_not(api_url):
    first = requests.get(f"{api_url}/order-lines", params={"cursor": cursor(300)}, timeout=10)
    assert first.status_code == 429 and first.headers["Retry-After"] == "0"
    server_error = requests.get(f"{api_url}/order-lines", params={"cursor": cursor(1400)}, timeout=10)
    assert server_error.status_code == 500 and "Retry-After" not in server_error.headers


def test_since_and_until_cut_the_window_by_updated_at(get_page):
    until = "2026-05-31 23:59:59"
    early = [r for page in pull_all(get_page, until=until) for r in page]
    late = [r for page in pull_all(get_page, since=until) for r in page]
    assert max(r["updated_at"] for r in early) <= until
    assert min(r["updated_at"] for r in late) > until
    assert len({r["order_item_id"] for r in early}) == 2643  # the repeated record is in this window too
    assert len(late) == 645  # lines first sent after May 31, plus lines corrected after it


def test_the_extra_zero_line_is_corrected_later(get_page):
    before = [r for page in pull_all(get_page, until="2026-05-02 00:00:00") for r in page]
    after = [r for page in pull_all(get_page) for r in page]
    assert [r["quantity"] for r in before if r["order_item_id"] == 6952] == [20]
    assert [r["quantity"] for r in after if r["order_item_id"] == 6952] == [2]


def test_a_bad_request_gets_400(get_page):
    assert get_page(limit=0).status_code == 400
    assert get_page(cursor="not-a-cursor").status_code == 400

