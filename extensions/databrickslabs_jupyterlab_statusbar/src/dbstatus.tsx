import React from 'react';
import { VDomRenderer, VDomModel, ISessionContext } from '@jupyterlab/apputils';
import { URLExt } from '@jupyterlab/coreutils';
import { interactiveItem, TextItem } from '@jupyterlab/statusbar';
import { ServerConnection } from '@jupyterlab/services';
import { ILabShell } from '@jupyterlab/application';
import { INotebookTracker } from '@jupyterlab/notebook';
import { Dialog, showDialog } from '@jupyterlab/apputils';
import { Poll } from '@lumino/polling';
import { NotebookPanel } from '@jupyterlab/notebook';


class Counter {
  private _count = 0;
  private _limit = 0;
  private _delay = 0;

  constructor() {
    this.reset()
  }
  next() {
    this._count += 1;
    var result = (this._count % this._delay == 0)
    if ((this._limit != -1) && (this._count > this._limit)) {
      switch (this._delay) {
        case 1: {
          this._delay = 2;
          this._limit = 30; // 60 seconds every 2 seconds
          break;
        }
        case 2: {
          this._delay = 5;
          this._limit = 24; // 120 seconds every 5 seconds
          break;
        }
        case 5: {
          this._delay = 10;  // every 10 seconds until reset
          this._limit = -1;
          break;
        }
        default: {
          this._delay = 10;  // every 10 seconds until reset
          this._limit = -1;
          break;
        }
      }

      this._count = 1;
      console.debug("Databrickslabs-jupyterlab: monitoring every", this._delay, "seconds")
    }
    return result
  }
  reset() {
    this._count = 0
    this._limit = 60  // 60 seconds every seconds
    this._delay = 1
  }
}
/**
 * A VDomRenderer for showing memory usage by a kernel.
 */
export class DbStatus extends VDomRenderer<DbStatus.Model> {
  /**
   * Construct a new databricks status item.
   */
  constructor(labShell: ILabShell, notebookTracker: INotebookTracker) {
    super(new DbStatus.Model({
      refreshRate: 1000,
      labShell: labShell,
      notebookTracker: notebookTracker
    }));
    this.addClass(interactiveItem);
  }

  /**
   * Render the databricks status item.
   */
  render() {
    if (!this.model) {
      return null;
    }
    let text: string = this.model.currentStatus;
    if (text === "UNREACHABLE") {
      text = "[ " + text + " ] (click here to restart)";
      // } else if (text === "CONNECT FAILED") {
      //   text = "[ " + text + " ] (retrying)";
    } else if (text === "STARTING") {
      text = "[ " + text + " ] (click here to reconfigure)";
    } else {
      text = "[ " + text + " ]";
    }
    return <TextItem onClick={() => this.model.handleClick()} title="Current databricks status" source={text} />;
  }
}

/**
 * A namespace for DbStatus statics.
 */
export namespace DbStatus {
  /**
   * A VDomModel for the databricks status item.
   */
  export class Model extends VDomModel {
    /**
     * Construct a new databricks model.
     *
     * @param options: the options for creating the model.
     */
    constructor(options: Model.IOptions) {
      super();
      this._notebookTracker = options.notebookTracker;

      options.labShell.restored.then(
        (layout) => {
          // notebookTracker.currentWidget might be wrong after new start or browser refresh with more 
          // than 1 open tab. Hence loop through all open tabs to find the visble one
          this._notebookTracker.forEach((notebookPanel: NotebookPanel) => {
            if (notebookPanel.isVisible) {
              console.debug("Databrickslabs-jupyterlab: select open notebook")
              this.check_status(notebookPanel.sessionContext)
            }
          })

          // When a new tab gets selected, update the kernel id
          this._notebookTracker.currentChanged.connect((sender: INotebookTracker, notebookPanel: NotebookPanel) => {
            console.debug("Databrickslabs-jupyterlab: selected notebook changed")
            this.check_status()
          })

          // When a kernel gets strted, restarted or stopped, update the kernel id
          options.labShell.currentChanged.connect((_, change) => {
            const { oldValue, newValue } = change;
            if (oldValue) {
              var context = (oldValue as NotebookPanel).sessionContext
              context.connectionStatusChanged.disconnect(this.onConnectionStatusChange, this)
            }
            if (newValue) {
              var context = (newValue as NotebookPanel).sessionContext
              context.connectionStatusChanged.connect(this.onConnectionStatusChange, this)
            }
          })
        }
      )

      this._poll = new Poll<Private.IDbStatusRequestResult | null>({
        factory: () => Private.factory(this, options.notebookTracker),
        frequency: {
          interval: options.refreshRate,
          backoff: true
        },
        name: 'statusbar-extension:databrickslabs-jupyterlab#status'
      });

      this._poll.ticked.connect(poll => {
        const { payload, phase } = poll.state;

        if (phase === 'resolved') {
          this._updateStatusValues(payload);
          return;
        }
        if (phase === 'rejected') {
          const oldStatusAvailable = this._statusAvailable;
          this._statusAvailable = false;
          this._currentStatus = "";

          if (oldStatusAvailable) {
            this.stateChanged.emit();
          }
          return;
        }
      });
    }


    cleanup() {
      console.info("Databrickslabs-jupyterlab: cleanup")
      this._updateStatusValues(null)
    }

    private onConnectionStatusChange(context: ISessionContext, change: any) {
      console.debug("Databrickslabs-jupyterlab: kernel state changed: " + change)
      if (change == "disconnected") {
        this.cleanup()
      } else if (change == "connected") {
        this.check_status()
      }
    }

    private async check_status(context: ISessionContext = null) {
      if (!context) {
        var context = this._notebookTracker.currentWidget.sessionContext;
        // console.debug("Databrickslabs-jupyterlab: check status, set: ", context)
      }
      // console.debug("Databrickslabs-jupyterlab: check status: ", context)
      context.ready.then(async () => {
        var name = context.kernelDisplayName
        var id = context.session.kernel.id

        const response = await Private.request("databrickslabs-jupyterlab-status", name, id);
        // console.debug("Databrickslabs-jupyterlab: check status, response: ", response)

        if (response && response.ok) {
          var result = await response.json();
          console.debug("Databrickslabs-jupyterlab: check status, result: ", result)
          if (result.status === "UNREACHABLE") {
            this._updateStatusValues(result)
          }
        } else {
          if (response) {
            console.error("check_status response: unknown", response)
          }
        }
      })
    }

    private _restart_dialog(status: string) {
      if (!this._dialog_shown) {
        this._dialog_shown = true;
        var title, body, label;
        if (status === "UNREACHABLE") {
          title = "Cluster not reachable";
          body = "Cluster cannot be reached. Check cluster or your network (e.g. VPN) and then press 'Restart' to restart the kernel or cluster";
          label = "Restart";
        } else {
          title = "Reconfigure cluster";
          body = "Reconfigure the cluster, i.e. fix ssh config, install libs, and create Spark Context";
          label = "Reconfigure";
        }
        showDialog({
          title: title,
          body: body,
          buttons: [
            Dialog.cancelButton(),
            Dialog.warnButton({ label: label })
          ]
        }).then(result => {
          if (result.button.accept) {
            let context = this._notebookTracker.currentWidget.sessionContext;
            this._notebookTracker.currentWidget.sessionContext.kernelDisplayName
            let id = context.session.kernel.id;
            let name = context.kernelDisplayName;
            Private.request("/databrickslabs-jupyterlab-start", name, id)
            this.counter.reset();
          }
        })
        this._dialog_shown = false;
      }
    }
    /**
     * Given the results of the status request, update model values.
     */
    private _updateStatusValues(value: Private.IDbStatusRequestResult | null): void {
      const oldStatusAvailable = this._statusAvailable;
      const oldCurrentStatus = this._currentStatus;
      console.debug("Databrickslabs-jupyterlab: (old status avail, old current status, value)",
        oldStatusAvailable, oldCurrentStatus, value
      )
      if (value === null) {
        this._statusAvailable = false;
        this._currentStatus = "";
      } else {
        var status = value.status;
        this._statusAvailable = true;
        this._currentStatus = status;
      }

      if (this._currentStatus === "UNREACHABLE") {
        if (this._currentStatus !== oldCurrentStatus) {
          this._restart_dialog(this._currentStatus)
        }
      }

      if (
        this._currentStatus !== oldCurrentStatus ||
        this._statusAvailable !== oldStatusAvailable
      ) {
        this.stateChanged.emit(void 0);
      }
    }

    /**
     * Click handler
     */
    handleClick() {
      this._restart_dialog(this.currentStatus)
    }

    get restarting_count(): number {
      return this._restarting_count;
    }

    set restarting_count(value: number) {
      this._restarting_count = value;
    }

    get restarting(): boolean {
      return this._restarting;
    }

    set restarting(value: boolean) {
      this._restarting = value;
    }
    /**
     * Whether the metrics server extension is available.
     */
    get statusAvailable(): boolean {
      return this._statusAvailable;
    }

    /**
     * The current status
     */
    get currentStatus(): string {
      return this._currentStatus;
    }
    /**
     * Dispose of the memory usage model.
     */
    dispose(): void {
      super.dispose();
    }
    private _currentStatus: string = "";
    private _statusAvailable: boolean = false;
    private _poll: Poll<Private.IDbStatusRequestResult>;
    private _notebookTracker: INotebookTracker;
    private _restarting = false;
    private _restarting_count = 0;
    private _dialog_shown = false;
    public counter = new Counter()
  }

  /**
   * A namespace for Model statics.
   */
  export namespace Model {
    /**
     * Options for creating a MemoryUsage model.
     */
    export interface IOptions {
      /**
       * The refresh rate (in ms) for querying the server.
       */
      refreshRate: number;
      labShell: ILabShell;
      notebookTracker: INotebookTracker;
    }
  }

}


namespace Private {
  const SERVER_CONNECTION_SETTINGS = ServerConnection.makeSettings();
  var old_name = "";

  export interface IDbStatusRequestResult {
    status: string;
  }

  export async function request(command: string, name: string, id: string) {
    if (name && name.slice(0, 4) != "SSH ") {
      return null
    }
    console.debug("Databrickslabs-jupyterlab: request ", command, name, id)
    var regex = new RegExp("^SSH (.+) ([^:]+):(.*)");
    var parts = regex.exec(name);
    var cluster_id = parts[1];
    var profile = parts[2];

    var url = URLExt.join(SERVER_CONNECTION_SETTINGS.baseUrl, command);
    url = url + "?profile=" + profile + "&cluster_id=" + cluster_id + "&id=" + id;
    // console.debug("Databrickslabs-jupyterlab: request url: ", url)

    return ServerConnection.makeRequest(url, {}, SERVER_CONNECTION_SETTINGS);
  }

  export async function factory(parent: DbStatus.Model, notebookTracker: INotebookTracker): Promise<IDbStatusRequestResult | null> {

    let name = notebookTracker.currentWidget.sessionContext.kernelDisplayName;
    var tab_switch = old_name !== name;
    old_name = name;
    let id = notebookTracker.currentWidget.sessionContext.session.kernel.id;
    var is_starting = parent.currentStatus !== "Connected";
    var do_status_check = parent.counter.next()

    if (do_status_check || is_starting || tab_switch) {

      const response = await request("databrickslabs-jupyterlab-status", name, id);
      // console.debug("Databrickslabs-jupyterlab: factory, response: ", response)

      if (response.ok) {
        try {
          var result = await response.json();
          // console.debug("Databrickslabs-jupyterlab: factory, result: ", result)
          return result
        } catch (error) {
          throw error;
        }
      }
    } else {
      return { "status": parent.currentStatus }
    }
    return null;
  }
}