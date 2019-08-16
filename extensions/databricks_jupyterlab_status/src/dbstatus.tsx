// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

import React from 'react';

import { VDomRenderer, VDomModel, IClientSession } from '@jupyterlab/apputils';

import { URLExt, Poll } from '@jupyterlab/coreutils';

import { interactiveItem, TextItem } from '@jupyterlab/statusbar';

import { ServerConnection } from '@jupyterlab/services';

import { ILabShell } from '@jupyterlab/application';

import { INotebookTracker } from '@jupyterlab/notebook';

import { Dialog, showDialog } from '@jupyterlab/apputils';


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
    if (text === "TERMINATED") {
      text = "[ " + text + " ] (click here to start cluster)";
    } else if (text === "UNREACHABLE") { 
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

      this._poll = new Poll<Private.IDbStatusRequestResult | null>({
        factory: () => Private.factory(this, options.notebookTracker),
        frequency: {
          interval: options.refreshRate,
          backoff: true
        },
        name: 'statusbar-extension:databricks-jupyterlab#status'
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

      const onStatusChanged = (session: IClientSession) => {
        if (session.status === "restarting") {
          this.restarting = true;
          this.restarting_count = 0;
        }
      };

      options.labShell.currentChanged.connect((_, change) => {
        if (this._oldSession) {
          this._oldSession.statusChanged.disconnect(onStatusChanged);
        }
        this._session = options.notebookTracker.currentWidget.session
        this._session.statusChanged.connect(onStatusChanged);
        this._oldSession = this._session;
      })
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
        if (this.restarting) {
          status = "Restarting"
        }
        this._statusAvailable = true;
        this._currentStatus = status;
      }

      if ((this._currentStatus === "TERMINATED") || (this._currentStatus === "UNREACHABLE")) {
        if (this._currentStatus !== oldCurrentStatus) {
          this._terminate_count = 0;
        } else {
          this._terminate_count += 1;
        }
        if (this._terminate_count === 2) {
          showDialog({
            title: this._currentStatus,
            body: "Note: The cluster is " + this._currentStatus.toLowerCase(),
            buttons: [
              Dialog.warnButton({ label: 'OK' })
            ]
          })
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
      var title = "";
      var body = "";
      var label = "";

      if (this.currentStatus == "TERMINATED") {
        title = "Cluster terminated";
        body = "Start remote cluster?";
        label = "Start Cluster";
      } else if (this.currentStatus === "UNREACHABLE") {
        title = "Cluster not reachable?";
        body = "Check e.g. VPN and then reconfigure kernel?";
        label = "Reconfigure cluster";
      }
      if ((this.currentStatus == "TERMINATED") || 
          (this.currentStatus === "UNREACHABLE")) {
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
            Private.request("/databricks-jupyterlab-start", name, id)
          }
        })
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
    private _oldSession: IClientSession;
    private _session: IClientSession;
    private _restarting = false;
    private _restarting_count = 0;
    private _terminate_count = 0;
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
  var counter = 0;
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

    counter += 1
    if (counter === 10 || is_starting || tab_switch || parent.restarting) {
      counter = 0;
      
      const response = await request("databricks-jupyterlab-status", name, id);

      if (response.ok) {
        try {
          var result = await response.json();
          // Keep restarting for 3 seconds
          if (parent.restarting_count > 3) {
            parent.restarting = false
          } else {
            parent.restarting_count += 1;
          }
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