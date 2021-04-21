import {
  ILabShell,
  JupyterFrontEnd, 
  JupyterFrontEndPlugin
} from '@jupyterlab/application';

import {
  IStatusBar
} from '@jupyterlab/statusbar';

import {
  DbStatus 
} from "./dbstatus"

import {
  INotebookTracker 
} from '@jupyterlab/notebook';

export const dbStatusItem: JupyterFrontEndPlugin<void> = {
  id: 'statusbar-extension:databrickslabs-jupyterlab#statusbar',
  autoStart: true,
  requires: [IStatusBar, INotebookTracker, ILabShell],
  activate: (
    app: JupyterFrontEnd, 
    statusBar: IStatusBar,
    notebookTracker: INotebookTracker,
    labShell: ILabShell) => {

    let item = new DbStatus(labShell, notebookTracker);

    statusBar.registerStatusItem(
      'statusbar-extension:databrickslabs-jupyterlab#statusbar',
      {
        item,
        align: 'left',
        rank: 2,
        isActive: () => item.model!.statusAvailable,
        activeStateChanged: item.model!.stateChanged
      }
    );
  }
}

const plugins: JupyterFrontEndPlugin<any>[] = [
  dbStatusItem
];

export default plugins;
