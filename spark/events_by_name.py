"""Count the events of each name: transformations build a plan, and an action runs it."""

import contextlib
import io
import re
import time

from pyspark.sql import SparkSession, functions as F

spark = (
    SparkSession.builder.master("local[2]").appName("events").config("spark.ui.enabled", "false")
    .config("spark.ui.showConsoleProgress", "false").config("spark.sql.shuffle.partitions", "4").getOrCreate()
)
spark.sparkContext.setLogLevel("ERROR")
SCHEMA = "event_id long, user_id long, event_ts timestamp, event_name string, platform string, received_at timestamp"


def jobs_run():
    """How many Spark jobs this program has run so far."""
    return len(spark.sparkContext.statusTracker().getJobIdsForGroup())


def operators(df):
    """The operators of the physical plan, from the top one down, without their details."""
    text = io.StringIO()
    with contextlib.redirect_stdout(text):
        df.explain()
    lines = [line for line in text.getvalue().splitlines() if line.strip() and not line.startswith("==")]
    return " > ".join(re.match(r"[ +:\-|]*(\w+)", line).group(1) for line in lines)


events = spark.read.csv("../data/raw/app-events/events.csv", header=True, schema=SCHEMA)
by_name = events.groupBy("event_name").agg(F.count("*").alias("events")).orderBy(F.desc("events"))
print("after the transformations:", jobs_run(), "jobs")
print("plan:", operators(by_name))
print("after explain:", jobs_run(), "jobs")
started = time.time()
rows = by_name.collect()
print(f"after collect: {jobs_run()} jobs, {time.time() - started:.1f} s")
for row in rows:
    print(f"{row['event_name']:<22}{row['events']:>7,}")
