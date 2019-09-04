// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

import React from 'react';

import { VDomRenderer, VDomModel } from '@jupyterlab/apputils';

import { URLExt, Poll } from '@jupyterlab/coreutils';

import { interactiveItem, TextItem } from '@jupyterlab/statusbar';

import { ServerConnection } from '@jupyterlab/services';

import { ILabShell } from '@jupyterlab/application';

import { INotebookTracker } from '@jupyterlab/notebook';

import { Dialog, showDialog } from '@jupyterlab/apputils';


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
          break; } 
        case 2: { 
          this._delay = 5; 
          this._limit = 24; // 120 seconds every 5 seconds
          break; }
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
    super();
    this.model = new DbStatus.Model({
      refreshRate: 1000,
      labShell: labShell,
      notebookTracker: notebookTracker
    });
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
    } else if (text === "CONNECT FAILED") { 
      text = "[ " + text + " ] (retrying)";
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

      options.labShell.restored.then((layout) => { 
        var session = options.notebookTracker.currentWidget.session;
        console.debug("Databrickslabs-jupyterlab: session", session)
        session.kernelChanged.connect((change) => {
          console.debug("Databrickslabs-jupyterlab: Kernel changed", change)
          this.check_status(session.kernelDisplayName, session.kernel.id)
        })
        session.ready.then(() => {
          console.debug("Databrickslabs-jupyterlab: Session ready", session)
          this.check_status(session.kernelDisplayName, session.kernel.id)
        })
      })

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

      options.labShell.currentChanged.connect((_, change) => {
        console.debug("Databrickslabs-jupyterlab: shell changed")
      })
    }

    private async check_status(name:string, id: string) {
      const response = await Private.request("databrickslabs-jupyterlab-status", name, id);
      if (response.ok) {
        var result = await response.json();
        if (result.status === "UNREACHABLE") {
          this._updateStatusValues(result)
        }
      } else {
        console.error("check_status response: unknown", response)
      }
    }
    
    private _restart_dialog(status:string) {
      if (! this._dialog_shown) {
        this._dialog_shown = true;
        var title, body, label;
        if (status === "UNREACHABLE") {
          title = "Kernel not reachable";
          body = "Kernel cannot be reached. Check your network (e.g. VPN) and then press 'Restart' to restart the kernel or cluster";
          label = "Restart";
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
            let session = this._notebookTracker.currentWidget!.session;
            let id = session.kernel.id;
            let name = session.kernelDisplayName;
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
      if (this._currentStatus == "UNREACHABLE") {
          this._restart_dialog(this.currentStatus)
      }
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
    var regex = new RegExp("^SSH (.+) ([^:]+):(.*)");
    var parts = regex.exec(name);
    var cluster_id = parts[1];
    var profile = parts[2];
    
    var url = URLExt.join(SERVER_CONNECTION_SETTINGS.baseUrl, command);
    url = url + "?profile=" + profile + "&cluster_id=" + cluster_id + "&id=" + id;

    return ServerConnection.makeRequest(url, {}, SERVER_CONNECTION_SETTINGS);
  }
  
  export async function factory(parent: DbStatus.Model, notebookTracker: INotebookTracker): Promise<IDbStatusRequestResult | null> {
    
    let name = notebookTracker.currentWidget!.session.kernelDisplayName;
    var tab_switch = old_name !== name;
    old_name = name;
    let id = notebookTracker.currentWidget!.session.kernel.id;
    var is_starting = parent.currentStatus !== "Connected";
    var do_status_check = parent.counter.next()

    if (do_status_check || is_starting || tab_switch) {
      
      const response = await request("databrickslabs-jupyterlab-status", name, id);

      if (response.ok) {
        try {
          var result = await response.json();
          return result
        } catch (error) {
          throw error;
        }
      } 
    } else {
      return {"status": parent.currentStatus}
    }
    return null;
  }
}