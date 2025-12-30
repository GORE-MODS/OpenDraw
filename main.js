const { app, BrowserWindow, globalShortcut, ipcMain } = require('electron');
const Store = require('electron-store');
const store = new Store();

let mainWindow = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 3840,                  // Oversized to cover most screens
    height: 2160,
    x: 0,
    y: 0,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,            // No taskbar icon
    focusable: false,             // Doesn't steal focus from games/streams
    resizable: false,
    hasShadow: false,
    show: false,                  // Start hidden
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  });

  mainWindow.loadFile('index.html');

  // Show the window only when content is ready (fixes Linux transparency glitches)
  mainWindow.once('ready-to-show', () => {
    mainWindow.showInactive();  // Show without stealing focus
  });

  // IPC handlers
  ipcMain.on('set-clickthrough', (event, ignore) => {
    if (mainWindow) {
      mainWindow.setIgnoreMouseEvents(ignore, { forward: true });
    }
  });

  ipcMain.on('clear-canvas', () => {
    if (mainWindow) {
      mainWindow.webContents.send('clear-canvas');
    }
  });
}

app.whenReady().then(() => {
  createWindow();

  // Global hotkeys (work even when hidden)
  globalShortcut.register('Control+Shift+D', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.showInactive();
      }
    }
  });

  globalShortcut.register('Control+Shift+C', () => {
    if (mainWindow) {
      mainWindow.webContents.send('clear-canvas');
    }
  });

  globalShortcut.register('Control+Shift+R', () => {
    mainWindow.webContents.send('set-color', '#ff0000');
  });

  globalShortcut.register('Control+Shift+B', () => {
    mainWindow.webContents.send('set-color', '#0000ff');
  });

  globalShortcut.register('Control+Shift+W', () => {
    mainWindow.webContents.send('set-color', '#ffffff');
  });

  globalShortcut.register('Control+Shift+G', () => {
    mainWindow.webContents.send('set-color', '#00ff00');
  });

  globalShortcut.register('Control+Shift+1', () => {
    mainWindow.webContents.send('set-size', 4);
  });

  globalShortcut.register('Control+Shift+2', () => {
    mainWindow.webContents.send('set-size', 16);
  });

  globalShortcut.register('Control+Shift+T', () => {
    mainWindow.webContents.send('toggle-clickthrough');
  });

  // Undo / Redo global hotkeys
  globalShortcut.register('Control+Z', () => {
    if (mainWindow) {
      mainWindow.webContents.send('undo');
    }
  });

  globalShortcut.register('Control+Y', () => {
    if (mainWindow) {
      mainWindow.webContents.send('redo');
    }
  });
});

app.on('will-quit', () => {
  // Clean up hotkeys
  globalShortcut.unregisterAll();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});