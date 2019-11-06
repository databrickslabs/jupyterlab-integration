import threading
import time
import uuid

from IPython.display import HTML, display
from IPython import get_ipython

try:
    from ipywidgets import FloatProgress, Label, HBox, VBox, Layout, Button
    has_ipywidgets = True
except:
    has_ipywidgets = False


class Progress(object):
    def __init__(self, sc, job_info):
        self.sc = sc
        self.job_info = job_info
        self.tracker = sc.statusTracker()
        self.progressbar_showing = False

    def worker(self):
        def cancel(b):
            self.sc.cancelJobGroup(self.job_info.group_id)

        def toggle(widget):
            def f(b):
                for w in widget.children:
                    h = w.layout.height
                    if h is None or h == "16px":
                        w.layout.height = "0px"
                        b.icon = 'arrow-circle-down'
                    else:
                        w.layout.height = "16px"
                        b.icon = 'arrow-circle-right'

            return f

        style = {'description_width': 'initial'}
        bars = {}
        labels = {}
        lastJob = None

        progressbars = VBox([])

        cancel_button = Button(button_style='', tooltip='Cancel Spark Job', icon='window-close')
        cancel_button.add_class("db-button")
        cancel_button.on_click(cancel)

        toggle_button = Button(button_style='', tooltip='Toggle progress bar', icon='arrow-circle-right')
        toggle_button.add_class("db-button")
        toggle_button.on_click(toggle(progressbars))

        indicator = HBox([toggle_button, progressbars])

        while (self.running == 1):
            time.sleep(0.2)
            jobs = [(jobid, self.tracker.getJobInfo(jobid))
                    for jobid in self.tracker.getJobIdsForGroup(self.job_info.group_id)
                    if self.tracker.getJobInfo(jobid).status == "RUNNING"]

            for j, job in jobs:
                if bars.get(j, None) is None:
                    if lastJob is not None:
                        bars[lastJob].value = 100.0
                    bars[j] = FloatProgress(value=0.0,
                                            min=0.0,
                                            max=100.0,
                                            description='Job: %04d Stage: %04d' % (j, 0),
                                            bar_style='info',
                                            orientation='horizontal',
                                            style=style)
                    bars[j].add_class("db-bar")
                    labels[j] = Label(value='',
                                      description='Code:',
                                      disabled=False,
                                      layout=Layout(width="800px", height="100%", margin="0 0 0 5px"))
                    labels[j].add_class("db-label")

                    progressbar = HBox([bars[j], labels[j]])
                    progressbars.children = progressbars.children + (progressbar, )
                    if not self.progressbar_showing:
                        self.progressbar_showing = True
                        display(indicator)

                lastJob = j
                stageIds = sorted(job.stageIds)
                for s in stageIds:
                    stageInfo = self.tracker.getStageInfo(s)
                    bars[j].description = 'Job: %04d Stage: %04d' % (j, s)
                    labels[j].value = "code: '%s' / stages: %s" % (stageInfo.name, str(stageIds)[1:-1])
                    if stageInfo.numActiveTasks > 0:
                        progress = int(100 * stageInfo.numCompletedTasks / stageInfo.numTasks)
                        bars[j].value = progress

        if lastJob is not None and self.running == 0:
            bars[lastJob].value = 100.0

    def start_progressbar(self, info):
        self.sc.setLocalProperty("spark.scheduler.pool", self.job_info.pool_id)
        self.job_info.group_id = self.job_info.pool_id + "_" + uuid.uuid4().hex
        self.sc.setJobGroup(self.job_info.group_id, "jupyterlab job group", True)

        self.running = 1
        self.progressbar_showing = False
        self.t = threading.Thread(target=self.worker)
        self.t.start()

    def stop_progressbar(self, result):
        # print("stop_progressbar")
        def is_running():
            job_status = [
                self.tracker.getJobInfo(jobid).status
                for jobid in self.tracker.getJobIdsForGroup(self.job_info.group_id)
            ]
            return any(status == "RUNNING" for status in job_status)

        if is_running():
            print("Killing spark job ", end="")
            while is_running():
                self.sc.cancelJobGroup(self.job_info.group_id)
                print(".", end="")
                time.sleep(1)
            print(". Spark job killed")
            self.running = -1
        else:
            # print("done")
            self.running = 0


def load_css():
    if has_ipywidgets:
        display(
            HTML("""
        <style>
        .db-bar {
            height: 12px;
            overflow: hidden;
        }

        .db-label {
            height: 14px;
            line-height: 11px !important;
            font-size: 11px;
            color: #999 !important;
        }
        div.db-bar label {
            font-size: 11px;
            color: #999 !important;
        }
        .db-button {
            width: 13px;
            height: 12px;
            padding: 0px;
        }
        .db-button .fa {
            display: block;
        }
        </style>
        """))


def load_progressbar(ip, sc, job_info):
    if has_ipywidgets:
        progress = Progress(sc, job_info)
        for event, name, func in (('pre_run_cell', "start_progressbar", progress.start_progressbar),
                                  ('post_run_cell', "stop_progressbar", progress.stop_progressbar)):
            register = True
            for m in ip.events.callbacks["pre_run_cell"]:
                if m.__name__ == name:
                    register = False
            if register:
                ip.events.register(event, func)
