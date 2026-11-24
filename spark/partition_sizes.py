"""How many rows land in each partition when the rows are shuffled by a key.

    uv run python partition_sizes.py 4 event_name user_id

The first argument is the number of partitions, the others are the columns to shuffle by. The line "round robin" deals the
rows out one by one, without a key.
"""

import sys

from pyspark.sql import SparkSession, functions as F

partitions, columns = int(sys.argv[1]), sys.argv[2:]
spark = (
    SparkSession.builder.master("local[2]").appName("events").config("spark.ui.enabled", "false")
    .config("spark.ui.showConsoleProgress", "false").getOrCreate()
)
spark.sparkContext.setLogLevel("ERROR")
SCHEMA = "event_id long, user_id long, event_ts timestamp, event_name string, platform string, received_at timestamp"
events = spark.read.csv("../data/raw/app-events/events.csv", header=True, schema=SCHEMA)


def sizes(df):
    """The rows in each partition of df, in order of partition number."""
    counts = {row["partition"]: row["count"] for row in df.groupBy(F.spark_partition_id().alias("partition")).count().collect()}
    return [counts.get(number, 0) for number in range(partitions)]


def report(name, rows):
    """One line: the sizes when there are few partitions, else how many are not empty, and the share of the biggest."""
    shown = rows if partitions <= 8 else f"{sum(1 for n in rows if n)} of {partitions} partitions hold rows"
    print(f"{name}: {shown}, the biggest holds {max(rows) / sum(rows):.1%}")


for column in columns:
    report(f"by {column}", sizes(events.repartition(partitions, column)))
report("round robin", sizes(events.repartition(partitions)))
