from datetime import datetime
import os
from IPython.display import HTML
import pandas as pd
from mlflow.tracking import MlflowClient


class MLflowBrowser:
    def __init__(self, experiment_name):
        self.client = MlflowClient()
        self.experiment = self.client.get_experiment_by_name(experiment_name)
        self.experiment_id = self.experiment.experiment_id
        self.url = "{host}/_mlflow/#/experiments/{experiment_id}/runs/".format(
            host=os.environ["DBJL_HOST"].strip("/"), experiment_id=self.experiment_id
        )
        self.runs = []
        self.table = None

    def _make_clickable(self, run_id, shorten=True):
        if shorten and run_id != "-":
            view_run_id = "%s..." % run_id[:8]
        else:
            view_run_id = run_id
        return '<a target="_blank" href="{}">{}</a>'.format(self.url + run_id, view_run_id)

    def _make_status(self, status):
        if status == "FINISHED":
            return u"\N{white heavy check mark}"
        elif status == "FAILED":
            return u"\N{cross mark}"
        elif status == "RUNNING":
            return u"\N{cyclone}"
        return status

    def summarize_run(self, run):
        result = dict(
            status=run.info.status,
            date=datetime.utcfromtimestamp(run.info.start_time / 1000).isoformat(
                sep=" ", timespec="seconds"
            ),
            run_id=run.info.run_id,
            parent_run_id=run.data.tags.get("mlflow.parentRunId", "-"),
            run_name=run.data.tags.get("mlflow.runName", "-"),
            user=run.data.tags.get("mlflow.user", "-"),
        )
        for k, v in run.data.params.items():
            try:
                val = float(v)
            except ValueError:
                val = v
            result["P.%s" % k] = val

        for k, v in run.data.metrics.items():
            try:
                val = float(v)
            except ValueError:
                val = v
            result["M.%s" % k] = val

        return result

    def get_runs(self, run_id=None):
        self.runs = self.client.search_runs(self.experiment_id)
        df = pd.DataFrame([self.summarize_run(run) for run in self.runs]).sort_values(
            ["date"], ascending=False
        )
        params = sorted([c for c in df.columns if c.startswith("P.")])
        metrics = sorted([c for c in df.columns if c.startswith("M.")])
        self.table = df[
            ["status", "date", "run_id", "parent_run_id", "run_name"] + params + metrics + ["user"]
        ]
        if run_id is None:
            return self.table
        else:
            return self.table[(self.table["run_id"] == run_id) | (self.table["parent_run_id"] == run_id)]

    def display(self, runs):
        print("=> Click on a run_id to open the run on the managed MLflow Tracking Server\n")

        return runs.fillna("-").style.format(
            {
                "run_id": self._make_clickable,
                "status": self._make_status,
                "parent_run_id": self._make_clickable,
            }
        )

    def compare(self, runs):
        run_ids = ",".join(["%%22%s%%22" % run for run in runs["run_id"]])
        url = "{host}/_mlflow/#/compare-runs?runs=[{run_ids}]&experiment={experiment_id}".format(
            host=os.environ["DBJL_HOST"].strip("/"),
            experiment_id=self.experiment_id,
            run_ids=run_ids,
        )
        return HTML(
            "<a href='{}'>Click to open comparision in Managed Tracking Server</a>".format(url)
        )
