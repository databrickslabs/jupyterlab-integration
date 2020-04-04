from ipywidgets import Select, HBox, VBox, Button, Output
from IPython.display import display, HTML
import pandas as pd


def _px(val):
    return "%dpx" % val


class DBList:
    def __init__(self, spark, console):
        self.spark = spark
        self.console = console
        self.height = 200
        self.db = None
        self.tbl = None
        self.list = None
        self.refresh = None

    def _set_status(self, status):
        with self.console:
            print(status, "...")

    def _clear_status(self):
        self.console.clear_output()

    def create(self, width=120, height=200):
        self.height = height
        self.refresh = Button(icon="refresh", layout={"width": "40px"})
        self.refresh.on_click(self.on_refresh)
        self.list = Select(
            options=[], disabled=False, layout={"width": _px(width), "height": _px(height)}
        )
        self.list.observe(self.on_click, names="value")
        self.update()

    def on_refresh(self, _):
        self.update()

    def on_click(self, change):
        self.console.clear_output()
        if change["old"] is not None:
            selected = change["new"]
            self.update(selected)

    def update(self, selected=None):
        pass


class DatabaseList(DBList):
    def __init__(self, spark, console, tbl):
        super().__init__(spark, console)
        self.tbl = tbl

    def update(self, selected=None):
        if selected is None:
            self._set_status("loading databases")
            result = [db.name for db in self.spark.catalog.listDatabases()]
            self.list.options = [""] + result
            self._clear_status()
        else:
            db = selected
            self.tbl.set_db(db)


class TableList(DBList):
    def __init__(self, spark, console, schema, data, sample_size=20):
        super().__init__(spark, console)
        self.schema = schema
        self.data = data
        self.sample_size = sample_size

    def _display_schema(self, schema, sep=False):
        if not sep:
            self.schema.clear_output()
        with self.schema:
            if sep:
                display(HTML("<hr>"))
            display(schema)

    def _display_data(self, data):
        self.data.clear_output()
        with self.data:
            display(data)

    def set_db(self, db):
        self.db = db
        self.update()

    def to_dict(self, c):
        return {
            "name": c.name,
            "data_type": c.dataType,
            "description": c.description,
            "nullable": c.nullable,
            "is_partition": c.isPartition,
            "is_bucket": c.isBucket,
        }

    def update(self, selected=None):
        tbl = selected
        if self.db is None:
            result = []
        elif tbl is None:
            self._set_status("loading tables")
            result = [tbl.name for tbl in self.spark.catalog.listTables(self.db)]
            self.list.options = [""] + result
            self._clear_status()
        else:
            # show schema
            self.schema.clear_output()
            self.data.clear_output()
            df = None
            try:
                df = pd.DataFrame(
                    [self.to_dict(col) for col in self.spark.catalog.listColumns(tbl, self.db)]
                )
            except:  # pylint: disable=bare-except
                self._display_schema("Cannot load schema")

            if df is None or df.empty:
                self._display_schema("Cannot load schema")
            else:
                df = df[
                    ["name", "data_type", "description", "nullable", "is_partition", "is_bucket"]
                ]
                self._display_schema(df)

                # show extended information
                pdf = self.spark.sql("describe extended %s.%s" % (self.db, tbl)).toPandas()
                pdf = pdf[pdf.index > len(df) + 1][["col_name", "data_type"]]
                pdf.columns = ["Key", "Value"]
                self._display_schema(pdf.style.hide_index(), sep=True)

                # show sample data
                self._set_status("loading data")
                try:
                    result = self.spark.sql(
                        "select * from %s.%s limit %d" % (self.db, tbl, self.sample_size)
                    ).toPandas()
                    self._display_data(result)
                except:  # pylint: disable=bare-except
                    self._display_data("Cannot load data")
                self._clear_status()


class Databases:
    """Database browser implementation

    Args:
        spark (SparkSession): Spark Session object
    """

    def __init__(self, spark):
        self.spark = spark

    def create(self, height=300, db_width=150, tbl_width=200, schema_width=700):
        console = Output(layout={"height": "28px"})
        schema = Output(
            layout={
                "height": _px(height),
                "width": _px(schema_width),
                "border": "1px solid grey",
                "overflow": "scroll",
            }
        )
        data = Output()

        tbl = TableList(self.spark, console, schema, data)
        tbl.create(width=tbl_width, height=height)

        db = DatabaseList(self.spark, console, tbl)
        db.create(width=db_width, height=height)

        display(
            VBox(
                [
                    HBox(
                        [
                            VBox([db.refresh, db.list]),
                            VBox([tbl.refresh, tbl.list]),
                            VBox([console, schema]),
                        ]
                    ),
                    data,
                ]
            )
        )
