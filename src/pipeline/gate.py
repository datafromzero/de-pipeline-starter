"""Let the clean lines through, hold the rest in quarantine, or stop the run."""

import logging

from pipeline.checks import CheckFailed, load_contract, row_checks

log = logging.getLogger("pipeline.gate")


def gate(con, rows, contract=None):
    """Return the lines that pass the contract's row checks. A failed stop rule raises; a failed quarantine rule holds its lines back."""
    contract = contract or load_contract()
    rows.create_view("batch", replace=True)
    checks = row_checks(contract)
    for name, action, sql in checks:  # stop rules first, before anything is written
        bad = con.execute(f"SELECT count(*) FROM ({sql.format(t='batch')})").fetchall()[0][0]
        if bad and action == "stop":
            raise CheckFailed(f"{name}: {bad} bad lines, the run stops")
    held = " UNION ALL ".join(
        f"SELECT '{name}' AS check_name, order_item_id, updated_at, to_json(b)::VARCHAR AS line FROM ({sql.format(t='batch')}) b"
        for name, action, sql in checks
        if action == "quarantine"
    )
    con.execute(f"CREATE OR REPLACE TEMP TABLE held AS {held}")
    clean = con.sql("""
        SELECT b.* FROM batch b
        ANTI JOIN held h ON h.order_item_id = b.order_item_id AND h.updated_at = b.updated_at
    """)
    read = con.execute("SELECT count(*) FROM batch").fetchall()[0][0]
    kept = clean.count("*").fetchall()[0][0]
    if read - kept > contract["max_quarantine_share"] * read:
        raise CheckFailed(f"{read - kept} of {read} lines would be quarantined, over the share the contract allows: look at the rule before the data")
    con.execute("""
        CREATE TABLE IF NOT EXISTS quarantine (
            check_name VARCHAR, order_item_id BIGINT, updated_at TIMESTAMP, line VARCHAR,
            PRIMARY KEY (check_name, order_item_id, updated_at)
        )
    """)
    con.execute("INSERT INTO quarantine SELECT * FROM held ON CONFLICT DO NOTHING")
    log.info("%d lines read, %d clean, %d quarantined", read, kept, read - kept)
    return clean
