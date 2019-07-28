#   Copyright 2019 Bernhard Walter
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
from IPython.display import HTML, display
import os
import pandas as pd
import datetime
import tempfile
import warnings
from functools import reduce
from databricks_jupyterlab.connect import is_remote


class GridSearchCV():

    def __init__(self, estimator, param_grid, *args, spark=None, **kwargs):
        self.estimator = estimator
        self.grid_size = reduce(lambda a, b: a * b,
                                [len(p) for p in param_grid.values()])
        self.results = None

        if is_remote():
            import spark_sklearn  # pylint: disable=import-error
            self.gs = spark_sklearn.GridSearchCV(spark.sparkContext, estimator,
                                                 param_grid, *args, **kwargs)
        else:
            import sklearn.model_selection
            self.gs = sklearn.model_selection.GridSearchCV(
                estimator, param_grid, *args, **kwargs)

    def fit(self, x, y):
        if is_remote():
            print("Remote crossvalidation,", end=" ")
        else:
            print("Local crossvalidation,", end=" ")
        print("paramter grid size: %d\n" % self.grid_size)

        self.results = self.gs.fit(x, y)
        return self.results

    def log_cv(self, experiment, name, tracking_uri=None):
        cv_results = self.results.cv_results_
        best = self.results.best_index_

        timestamp = datetime.datetime.now().isoformat().split(".")[0].replace(
            ":", ".")

        num_runs = len(cv_results["rank_test_score"])
        run_name = "run %d (best run of %d):" % (self.results.best_index_,
                                                 num_runs)

        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)

        mlflow.set_experiment(experiment)

        with mlflow.start_run(run_name=run_name):  #  as run:

            mlflow.log_param("folds", self.results.cv)

            print("Logging parameters")
            params = list(self.results.param_grid.keys())
            for param in params:
                mlflow.log_param(param, cv_results["param_%s" % param][best])

            print("Logging metrics")
            mlflow.log_metric("mean_test_score",
                              cv_results["mean_test_score"][best])
            mlflow.log_metric("std_test_score",
                              cv_results["std_test_score"][best])

            print("Logging model")
            mlflow.sklearn.log_model(self.results.best_estimator_, "model")

            print("Logging CV results matrix")
            tempdir = tempfile.TemporaryDirectory().name
            os.mkdir(tempdir)
            filename = "%s-%s-cv_results.csv" % (name, timestamp)
            csv = os.path.join(tempdir, filename)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pd.DataFrame(cv_results).sort_values(
                    by='rank_test_score').to_csv(csv, index=False)

            mlflow.log_artifact(csv, "cv_results")

        client = MlflowClient()
        experiment_id = client.get_experiment_by_name(experiment).experiment_id

        if is_remote():
            if os.environ.get("DBJL_ORG", None) is None:
                display(
                    HTML('<a href=%s/#mlflow/experiments/%s>Goto experiment</a>'
                         % (os.environ["DBJL_HOST"], experiment_id)))
            else:
                display(
                    HTML(
                        '<a href=%s?o=%s#mlflow/experiments/%s>Goto experiment</a>'
                        % (os.environ["DBJL_HOST"], os.environ["DBJL_ORG"],
                           experiment_id)))
        else:
            display(
                HTML('<a href=%s/#/experiments/%s>Goto experiment</a>' %
                     (tracking_uri, experiment_id)))
