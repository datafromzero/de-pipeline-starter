"""The nightly job as a DAG. The order of the steps and the schedule live here; the work lives in pipeline.daily."""

from datetime import datetime, timedelta

from airflow.sdk import CronDataIntervalTimetable, dag, task


def alert(context):
    """Runs when a task has failed for good. A real one would send a message; this one prints the line the message would carry."""
    ti = context["task_instance"]
    print(f"ALERT: {ti.dag_id}.{ti.task_id} failed on try {ti.try_number}, day {context['data_interval_start']:%Y-%m-%d}")


@dag(
    schedule=CronDataIntervalTimetable("0 0 * * *", timezone="UTC"),
    start_date=datetime(2026, 4, 30),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(seconds=5), "on_failure_callback": alert},
)
def cafe_pipeline():
    @task
    def extract(data_interval_start=None):
        from pipeline import daily

        daily.run_step("extract", data_interval_start.date())

    @task
    def check(data_interval_start=None):
        from pipeline import daily

        daily.run_step("check", data_interval_start.date())

    @task
    def publish(data_interval_start=None):
        from pipeline import daily

        daily.run_step("publish", data_interval_start.date())

    extract() >> check() >> publish()


cafe_pipeline()
