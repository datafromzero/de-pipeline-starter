"""Count events in daily event-time windows from a stream of daily files, with a watermark.

    uv run python stream_windows.py 1 hour

The words after the script name are the watermark: how late an event may be, in event time, and still be counted.
"""

import sys
import time

from pyspark.sql import SparkSession, functions as F

watermark = " ".join(sys.argv[1:])
spark = (
    SparkSession.builder.master("local[2]").appName("windows").config("spark.ui.enabled", "false")
    .config("spark.ui.showConsoleProgress", "false").config("spark.sql.shuffle.partitions", "2").getOrCreate()
)
spark.sparkContext.setLogLevel("ERROR")
SCHEMA = "event_id long, user_id long, event_ts timestamp, event_name string, platform string, received_at timestamp"

# One file at a time, in the order the files were written: each file is one trigger of the query.
stream = spark.readStream.schema(SCHEMA).option("maxFilesPerTrigger", 1).parquet("../data/raw/app-events/stream")
counts = stream.withWatermark("event_ts", watermark).groupBy(F.window("event_ts", "1 day").alias("day")).count()
latest = {}


def keep(batch, batch_id):
    """Remember the newest count of each window that this trigger updated."""
    for row in batch.collect():
        latest[row["day"]["start"]] = row["count"]


started = time.time()
query = counts.writeStream.outputMode("update").foreachBatch(keep).trigger(availableNow=True).start()
query.awaitTermination()
print(f"watermark {watermark}: {len(latest)} windows, {sum(latest.values()):,} events counted, {time.time() - started:.0f} s")
