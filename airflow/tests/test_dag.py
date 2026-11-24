from pathlib import Path

from airflow.dag_processing.dagbag import DagBag

DAGS = Path(__file__).resolve().parents[1] / "dags"


def load_dag():
    bag = DagBag(dag_folder=str(DAGS))
    assert bag.import_errors == {}
    return bag.dags["cafe_pipeline"]


def test_the_dag_loads_and_the_steps_run_in_order():
    dag = load_dag()
    assert dag.task_dict["extract"].downstream_task_ids == {"check"}
    assert dag.task_dict["check"].downstream_task_ids == {"publish"}
    assert dag.task_dict["publish"].downstream_task_ids == set()


def test_only_one_run_at_a_time_writes_the_table():
    assert load_dag().max_active_runs == 1


def test_every_task_retries_twice_and_raises_the_alert_when_it_gives_up():
    dag = load_dag()
    for task in dag.tasks:
        assert task.retries == 2
        assert task.on_failure_callback
