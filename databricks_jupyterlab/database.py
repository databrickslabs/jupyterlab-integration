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

import os
from sidecar import Sidecar
from ipywidgets import Accordion, Select, VBox, Button, Output, Layout
from IPython.display import display, HTML


class Databases(object):

    instance = None

    class __Databases(object):
        def __init__(self, spark):
            self.spark = spark

        def create(self):
            self.sc = Sidecar(title="Databases-%s" % os.environ["DBJL_CLUSTER"].split("-")[-1],
                              layout=Layout(width="300px"))
            self.refresh = Button(description="refresh")
            self.refresh.on_click(self.on_refresh)
            self.output = Output(layout=Layout(height="600px", width="320px", overflow_x="scroll", overflow_y="scroll"))
            self.output.add_class("db-detail")
            self.selects = []
            self.accordion = Accordion(children=[])

            with self.sc:
                display(VBox([self.refresh, self.accordion, self.output]))

            self.update()
            self.set_css()

        def on_refresh(self, b):
            self.selects = []
            self.update()

        def update(self):
            tables = {}
            for obj in self.spark.sql("show tables").rdd.collect():
                db = obj[0]
                table = obj[1]
                temp = obj[2]
                if temp and db == "":
                    db = "temp"
                if tables.get(db, None) is None:
                    tables[db] = []
                if temp:
                    tables[db].append("%s (temp)" % table)
                else:
                    tables[db].append(table)

            for db in sorted(tables.keys()):
                select = Select(options=[""] + sorted(tables[db]), disabled=False)
                select.observe(self.on_click(db, self), names='value')
                self.selects.append(select)
            self.accordion.children = self.selects
            for i, db in enumerate(sorted(tables.keys())):
                self.accordion.set_title(i, db)

        def on_click(self, db, parent):
            def f(change):
                if change["old"] is not None:
                    parent.output.clear_output()
                    with parent.output:
                        if db == "temp":
                            table = change["new"]
                        else:
                            table = "%s.%s" % (db, change["new"])
                        if table.endswith(" (temp)"):
                            table = table[:-7]

                        try:
                            schema = parent.spark.sql("describe extended %s" % table)
                            rows = int(parent.spark.conf.get("spark.sql.repl.eagerEval.maxNumRows"))
                            parent.spark.conf.set("spark.sql.repl.eagerEval.maxNumRows", 1000)
                            display(schema)
                            parent.spark.conf.set("spark.sql.repl.eagerEval.maxNumRows", rows)
                        except:
                            print("schema cannot be accessed, table most probably broken")

            return f

        def close(self):
            self.selects = []
            self.sc.close()

        def set_css(self):
            display(
                HTML("""
            <style>
            .db-detail .p-Widget {
            overflow: visible;
            }
            </style>
            """))

    def __init__(self, spark=None):
        if not Databases.instance:
            Databases.instance = Databases.__Databases(spark)

    def __getattr__(self, name):
        return getattr(self.instance, name)
