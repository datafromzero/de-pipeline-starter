export AIRFLOW_HOME="$PWD/home"
export AIRFLOW__CORE__DAGS_FOLDER="$PWD/dags"
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export PYTHONPATH="$PWD/../src"
export PYTHONWARNINGS=ignore

# Airflow prints a long line for everything it does. Pipe a command into short to keep the lines of the pipeline, each task's
# start and end, the run's end, the alert and the last line of every error.
short() {
  sed -nE \
    -e 's/.*\] (.*) \[(pipeline\.[a-z]+)\].*/\2: \1/p' \
    -e 's/.*running task <TaskInstance: ([a-z_.]+) .*/running \1/p' \
    -e 's/.*new_state=([a-z_]+).*/   task state: \1/p' \
    -e 's/.*DagRun Finished.* state=([a-z]+),.*/run state: \1/p' \
    -e '/^ALERT/p' \
    -e '/^[A-Za-z_.]+(Error|Exception):/p' | sed -E 's/ +$//' | cut -c1-150
}
