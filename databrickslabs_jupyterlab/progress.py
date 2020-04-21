import os
import threading
import time

from IPython.display import display
from IPython import get_ipython

try:
    from ipywidgets import FloatProgress, Label, HBox, VBox, Layout, Button

    has_ipywidgets = True
except ImportError:
    has_ipywidgets = False


def debug():
    return os.environ.get("PROGRESS_DEBUG", None) == "TRUE"


class ProgressBars:
    def __init__(self):
        self.style = {"description_width": "initial"}
        self.bars = {}
        self.labels = {}
        self.last_job = None

        self.progressbars = VBox([])

        cancel_button = Button(button_style="", tooltip="Cancel Spark Job", icon="window-close")
        cancel_button.add_class("db-button")

        toggle_button = Button(
            button_style="", tooltip="Toggle progress bar", icon="arrow-circle-right"
        )
        toggle_button.add_class("db-button")
        toggle_button.on_click(self._toggle(self.progressbars))

        self.indicator = HBox([toggle_button, self.progressbars])
        self.progressbar_showing = False

    def _toggle(self, widget):
        def f(b):
            for w in widget.children:
                h = w.layout.height
                if h is None or h == "16px":
                    w.layout.height = "0px"
                    b.icon = "arrow-circle-down"
                else:
                    w.layout.height = "16px"
                    b.icon = "arrow-circle-right"

        return f

    def bar_needed(self, job):
        return self.bars.get(job, None) is None

    def add_bar(self, job):
        self.bars[job] = FloatProgress(
            value=0.0,
            min=0.0,
            max=100.0,
            description="Job: %04d Stage: %04d" % (job, 0),
            bar_style="info",
            orientation="horizontal",
            style=self.style,
        )
        self.bars[job].add_class("db-bar")
        self.labels[job] = Label(
            value="",
            description="Code:",
            disabled=False,
            layout=Layout(width="800px", height="100%", margin="0 0 0 5px"),
        )
        self.labels[job].add_class("db-label")

        progressbar = HBox([self.bars[job], self.labels[job]])
        self.progressbars.children = self.progressbars.children + (progressbar,)
        if not self.progressbar_showing:
            self.progressbar_showing = True
            display(self.indicator)

    def set_last_job(self, job):
        self.last_job = job

    def finish_last_job(self):
        if self.last_job is not None:
            self.bars[self.last_job].value = 100.0

    def update_bar(self, job, description, label):
        self.bars[job].description = description
        self.labels[job].value = label

    def update_progress(self, job, value):
        self.bars[job].value = value


class Progress:
    def __init__(self, sc, job_info):
        self.sc = sc
        self.job_info = job_info
        self.thread = None
        self.tracker = sc.statusTracker()
        self.progressbars = ProgressBars()

    def start(self):
        self.job_info.dump("START")
        self.thread = threading.Thread(target=self.worker, args=(self.progressbars,), daemon=True)
        self.job_info.current_thread = self.thread
        self.thread.start()

        # Re-attach to ensure main thread has group_id
        # Sometimes this was reset to last group_id, reason unclear
        self.job_info.attach()
        self.job_info.dump("POST START")

    def worker(self, progressbars):
        self.job_info.attach()
        self.job_info.is_running[self.job_info.group_id] = True
        self.job_info.dump("RUNNING")

        while self.job_info.is_running[self.job_info.group_id]:
            jobs = [
                (jobid, self.tracker.getJobInfo(jobid))
                for jobid in self.tracker.getJobIdsForGroup(self.job_info.group_id)
                if self.tracker.getJobInfo(jobid).status == "RUNNING"
            ]
            if debug():
                print("==> jobs", jobs, self.job_info.group_id)
            for j, job in jobs:
                if progressbars.bar_needed(j):
                    progressbars.finish_last_job()
                    progressbars.add_bar(j)
                    progressbars.set_last_job(j)

                stageIds = sorted(job.stageIds)
                for s in stageIds:
                    stageInfo = self.tracker.getStageInfo(s)
                    description = "Job: %04d Stage: %04d" % (j, s)
                    label = "code: '%s' / stages: %s" % (stageInfo.name, str(stageIds)[1:-1])
                    progressbars.update_bar(j, description, label)
                    if stageInfo.numActiveTasks > 0:
                        progress = int(100 * stageInfo.numCompletedTasks / stageInfo.numTasks)
                        progressbars.update_progress(j, progress)
            time.sleep(0.2)

        progressbars.finish_last_job()

        self.job_info.dump("LEFT LOOP")


def is_running(tracker, group_id):
    job_status = [tracker.getJobInfo(jobid).status for jobid in tracker.getJobIdsForGroup(group_id)]
    return any(status == "RUNNING" for status in job_status)


def start_wrapper(sc, job_info):
    def start_progressbar(_):
        job_info.new_group_id()
        job_info.dump("INIT")
        prog_bar = Progress(sc, job_info)
        prog_bar.start()

    return start_progressbar


def stop_wrapper(sc, job_info):
    def stop_progressbar(_):
        job_info.is_running[job_info.group_id] = False

        # job_info.attach()
        job_info.dump("STOPPED")

        tracker = sc.statusTracker()

        if is_running(tracker, job_info.group_id):
            print("Killing spark job ", end="")
            while is_running(tracker, job_info.group_id):
                sc.cancelJobGroup(job_info.group_id)
                print(".", end="")
                time.sleep(1)
            print(". Spark job killed")

        job_info.stop_all()
        if job_info.current_thread is not None:
            if debug():
                print("\nWAITING for thread to stop")
            job_info.current_thread.join()
            if debug():
                print("\nTHREAD STOPPED")

    return stop_progressbar


def load_progressbar(sc, job_info):
    def unregister(ip, event, func_name):
        f = [f for f in ip.events.callbacks[event] if f.__name__ == func_name]
        if len(f) > 0:
            ip.events.unregister(event, f[0])

    if has_ipywidgets:
        ip = get_ipython()
        for event, name, func in (
            ("pre_run_cell", "start_progressbar", start_wrapper(sc, job_info)),
            ("post_run_cell", "stop_progressbar", stop_wrapper(sc, job_info)),
        ):
            unregister(ip, event, name)
            ip.events.register(event, func)
