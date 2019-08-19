import time
import numpy as np

from bokeh.io import push_notebook, show, output_notebook
from bokeh.layouts import row, column
from bokeh.resources import Resources
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, Range1d, Legend, CrosshairTool, HoverTool, BoxZoomTool, ResetTool, SaveTool

from tensorflow.keras.callbacks import LambdaCallback
from tensorflow.keras.callbacks import TensorBoard


class AccLossPlot(LambdaCallback):
    """Accuracy / Loss plot to dynamically show progress of tensorflow model 
    in the notebook
        
    Args:
        steps (int): number of steps
        epochs (int): number of epochs
        min_acc (float, optional): minmum accuracy shown on y axis. Defaults to 0.94.
        max_loss (int, optional): max loss shown on y axis. Defaults to 20.
        skip (int, optional): Number of steps to skip for plotting. Defaults to 10.
        table (bool, optional): If True show accuracy/loss results per epoch. Defaults to False.
        visual (bool, optional): If True show visual accuracy/loss progess plot. Defaults to False.
        height (int, optional): height of each plot. Defaults to 400.
        width (int, optional): width of each plot. Defaults to 800.

    Attributess:
        steps (int): number of steps
        epochs (int): number of epochs
        min_acc (float, optional): minmum accuracy shown on y axis. Defaults to 0.94.
        max_loss (int, optional): max loss shown on y axis. Defaults to 20.
        skip (int, optional): Number of steps to skip for plotting. Defaults to 10.
        table (bool, optional): If True show accuracy/loss results per epoch. Defaults to False.
        visual (bool, optional): If True show visual accuracy/loss progess plot. Defaults to False.
        height (int, optional): height of each plot. Defaults to 400.
        width (int, optional): width of each plot. Defaults to 800.
        max_x (nt): maximum value on x axis (epochs*steps)
        handle (str): bokeh graph handle for later updates
        sources (ColumnDataSource): Bokeh ColumnDataSource of accuracy and loss values
    """
    def __init__(self,
                 steps,
                 epochs,
                 min_acc=0.94,
                 max_loss=20,
                 skip=10,
                 table=False,
                 visual=False,
                 height=400,
                 width=800):
        self.steps = steps
        self.epoch = 0
        self.min_acc = min_acc
        self.max_loss = max_loss
        self.skip = skip
        self.height = height
        self.width = width
        self.table = table
        self.visual = visual
        self.time = 0

        self.max_x = epochs * steps
        self.handle = None
        self.sources = {"Accuracy": {}, "Loss": {}}

    def _line(self, plot, x, y, source, color, legend=None):
        """Plot a line
        
        Args:
            plot (object): plot object
            x (list): x values
            y (list): y values
            source (ColumnDataSource): bokeh ColumnDataSource
            color (str): color of line
            legend (str, optional): legend string. Defaults to None.
        """
        plot.line(x, y, source=source, line_color=color, legend=legend)

    def _cline(self, plot, x, y, source, color, legend=None):
        """Plot a line with circles
        
        Args:
            plot (object): plot object
            x (list): x values
            y (list): y values
            source (ColumnDataSource): bokeh ColumnDataSource
            color (str): color of line
            legend (str, optional): legend string. Defaults to None.
        """
        plot.line(x, y, source=source, line_color=color, legend=legend)
        p = plot.circle(x, y, source=source, line_color=color, fill_color=color, legend=legend)
        # plot.add_tools(HoverTool(renderers=[p], tooltips=[("Epoch", "@Epoch"), (y, "@%s" % y)]))
        plot.add_tools(HoverTool(renderers=[p], tooltips=[("Epoch", "@Epoch"), ("Train", "@Train"), ("Val", "@Val")]))

    def _plot(self, kind, range_x, range_y):
        """Create the actual plot
        
        Args:
            kind (str): "Accuracy" or "Loss"
            range_x (tuple): x axis range
            range_y (tuple): y axis range
        
        Returns:
            [type]: [description]
        """
        self.sources[kind]["batch"] = ColumnDataSource({"Step": [], "Train": []})
        self.sources[kind]["epoch"] = ColumnDataSource({"Step": [], "Epoch": [], "Train": [], "Val": []})

        tools = [CrosshairTool(), BoxZoomTool(), ResetTool(), SaveTool()]

        plot = figure(plot_width=self.width, plot_height=self.height, title=kind, tools=tools)
        plot.x_range = Range1d(range_x[0], range_x[1])
        plot.y_range = Range1d(range_y[0], range_y[1])

        self._line(plot, "Step", "Train", source=self.sources[kind]["batch"], color='#dddddd')
        self._cline(plot, "Step", "Train", source=self.sources[kind]["epoch"], color='#ff7f0e', legend="train")
        self._cline(plot, "Step", "Val", source=self.sources[kind]["epoch"], color='#1f77b4', legend="validation")

        plot.legend.click_policy = "hide"

        return plot

    def on_train_begin(self, logs=None):
        """Tensorflow handler for begin training event
        This will create the initial plots
        """
        if self.visual:
            output_notebook()

            train_acc_plot = self._plot("Accuracy", (0, self.max_x), (self.min_acc, 1))
            train_loss_plot = self._plot("Loss", (0, self.max_x), (0, self.max_loss))
            train_acc_plot.legend.location = "bottom_right"

            self.handle = show(column(train_acc_plot, train_loss_plot), notebook_handle=True)

        if self.table:
            print("Epoch \t train-acc \t train-loss \t val-acc \t val-loss ")

    def on_batch_end(self, batch, logs=None):
        """Tensorflow handler for batch end event
        This will plot the line for this batch if not skipped
        
        Args:
            logs (dict, optional): include loss, and optionally acc. Defaults to None.
        """
        if self.visual:
            if batch % self.skip == 0:
                step = self.steps * self.epoch + batch
                self.sources["Accuracy"]["batch"].stream({'Step': [step], 'Train': [logs["acc"]]})
                self.sources["Loss"]["batch"].stream({'Step': [step], 'Train': [logs["loss"]]})
                push_notebook(handle=self.handle)

    def on_epoch_begin(self, epoch, logs=None):
        """Tensorflow handler for epoch begin event
        This will start taking time.
        
        Args:
            logs (dict, optional): include acc and loss. Defaults to None.
        """
        self.time = time.time()

    def on_epoch_end(self, epoch, logs=None):
        """Tensorflow handler for epoch begin event
        This will stop taking time and plot epoch results
        Optionally writes accuracy/loss table
        
        Args:
            logs (dict, optional): include acc and loss. Defaults to None.
        """
        if self.table:
            print("% 5d\t" % epoch, end="")
            for k in ["acc", "loss", "val_acc", "val_loss"]:
                print(" %2.8f  " % logs[k], end="\t")
            print("(%3.1f s)" % (time.time() - self.time))

        self.epoch += 1
        step = self.steps * self.epoch

        if self.visual:
            self.sources["Accuracy"]["epoch"].stream({
                'Step': [step],
                'Epoch': [epoch],
                'Train': [logs["acc"]],
                'Val': [logs["val_acc"]]
            })
            self.sources["Loss"]["epoch"].stream({
                'Step': [step],
                'Epoch': [epoch],
                'Train': [logs["loss"]],
                'Val': [logs["val_loss"]]
            })
            push_notebook(handle=self.handle)


class VisualModel(object):
    """Class for starting tensorflow in visual mode
        
    Args:
        data ([type]): [description]
        batch_size (int): batch size
        epochs (int): number of epochs
    """
    def __init__(self, data, batch_size, epochs):
        self.data = data
        self.batch_size = batch_size
        self.epochs = epochs
        self.t_shape = self.data.target_shape()
        self.i_shape = self.data.shape
        self.format = self.data.data_format
        self.classes = self.data.num_classes

    def callback(self, min_acc=0.95, max_loss=5, skip=10, table=False, visual=False):
        """Callback to use Accuracy Loss Plot
        
        Args:
            min_acc (float, optional): minmum accuracy shown on y axis. Defaults to 0.94.
            max_loss (int, optional): max loss shown on y axis. Defaults to 20.
            skip (int, optional): Number of steps to skip for plotting. Defaults to 10.
            table (bool, optional): If True show accuracy/loss results per epoch. Defaults to False.
            visual (bool, optional): If True show visual accuracy/loss progess plot. Defaults to False.

        Returns:
            object: AccLossplot object
        """
        return AccLossPlot(steps=int(self.data.train_images.shape[0] / self.batch_size),
                           epochs=self.epochs,
                           min_acc=min_acc,
                           max_loss=max_loss,
                           skip=skip,
                           table=table,
                           visual=visual)

    def tbCallback(self):
        """TensorBoard callback"""
        return TensorBoard(log_dir='./Graph',
                           histogram_freq=0,
                           write_grads=False,
                           write_graph=False,
                           write_images=False)

    def create_model(self):
        raise NotImplementedError("model not implemented")

    def fit(self, callbacks=None, verbose=0):
        raise NotImplementedError("model not implemented")
