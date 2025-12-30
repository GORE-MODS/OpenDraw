const { app, BrowserWindow, globalShortcut, ipcMain, Tray, Menu, nativeImage, dialog } = require('electron');

console.log('[OpenDraw] Starting up...');

let mainWindow = null;
let tray = null;

// Fixed hotkeys (no remap for now)
const hotkeys = {
  toggle: 'Control+Shift+D',
  clear: 'Control+Shift+C',
  red: 'Control+Shift+R',
  blue: 'Control+Shift+B',
  white: 'Control+Shift+W',
  green: 'Control+Shift+G',
  thin: 'Control+Shift+1',
  thick: 'Control+Shift+2',
  clickthrough: 'Control+Shift+T',
  undo: 'Control+Z',
  redo: 'Control+Y'
};

const hotkeyDescriptions = {
  toggle: 'Toggle Overlay (show/hide)',
  clear: 'Clear Canvas',
  red: 'Set color to Red',
  blue: 'Set color to Blue',
  white: 'Set color to White',
  green: 'Set color to Green',
  thin: 'Set brush to Thin (4px)',
  thick: 'Set brush to Thick (16px)',
  clickthrough: 'Toggle Click-Through',
  undo: 'Undo last action',
  redo: 'Redo last action'
};

function createWindow() {
  console.log('[OpenDraw] Creating main window...');
  mainWindow = new BrowserWindow({
    width: 3840,
    height: 2160,
    x: 0,
    y: 0,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    focusable: false,
    resizable: false,
    hasShadow: false,
    show: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  mainWindow.loadFile('index.html')
    .then(() => console.log('[OpenDraw] index.html loaded'))
    .catch(err => console.error('[OpenDraw] Load failed:', err));

  mainWindow.setFocusable(false);
  mainWindow.blur();
}

function createTray() {
  console.log('[OpenDraw] Creating tray icon...');
  try {
    // Tiny red fallback icon (1x1 PNG buffer)
    const fallbackBuffer = Buffer.from([
      0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d,
      0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
      0x08, 0x06, 0x00, 0x00, 0x00, 0x1f, 0x15, 0xc4, 0x89, 0x00, 0x00, 0x00,
      0x0a, 0x49, 0x44, 0x41, 0x54, 0x78, 0x9c, 0x63, 0xfc, 0xcf, 0x30, 0x00,
      0x00, 0x03, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4e, 0x44,
      0xae, 0x42, 0x60, 0x82
    ]);

    const icon = nativeImage.createFromBuffer(fallbackBuffer);

    tray = new Tray(icon);

    const contextMenu = Menu.buildFromTemplate([
      { label: 'Toggle Overlay', click: () => mainWindow?.isVisible() ? mainWindow.hide() : mainWindow.showInactive() },
      { label: 'Clear Canvas', click: () => mainWindow?.webContents.send('clear-canvas') },
      { type: 'separator' },
      {
        label: 'Supported Hotkeys (list)',
        click: () => {
          const list = Object.keys(hotkeys).map(key => 
            `${hotkeys[key]} → ${hotkeyDescriptions[key]}`
          ).join('\n');

          dialog.showMessageBox(mainWindow, {
            type: 'info',
            title: 'Supported Hotkeys',
            message: 'Current hotkeys in OpenDraw:',
            detail: list,
            buttons: ['OK']
          });
        }
      },
      { type: 'separator' },
      { label: 'Quit OpenDraw', click: () => app.quit() }
    ]);

    tray.setToolTip('OpenDraw');
    tray.setContextMenu(contextMenu);

    tray.on('click', () => {
      mainWindow?.isVisible() ? mainWindow.hide() : mainWindow.showInactive();
    });

    console.log('[OpenDraw] Tray created successfully');
  } catch (err) {
    console.error('[OpenDraw] Tray creation failed:', err.message);
  }
}

function registerAllHotkeys() {
  globalShortcut.unregisterAll();

  globalShortcut.register(hotkeys.toggle, () => {
    if (mainWindow) {
      mainWindow.isVisible() ? mainWindow.hide() : mainWindow.showInactive();
    }
  });

  globalShortcut.register(hotkeys.clear, () => mainWindow?.webContents.send('clear-canvas'));
  globalShortcut.register(hotkeys.red, () => mainWindow?.webContents.send('set-color', '#ff0000'));
  globalShortcut.register(hotkeys.blue, () => mainWindow?.webContents.send('set-color', '#0000ff'));
  globalShortcut.register(hotkeys.white, () => mainWindow?.webContents.send('set-color', '#ffffff'));
  globalShortcut.register(hotkeys.green, () => mainWindow?.webContents.send('set-color', '#00ff00'));
  globalShortcut.register(hotkeys.thin, () => mainWindow?.webContents.send('set-size', 4));
  globalShortcut.register(hotkeys.thick, () => mainWindow?.webContents.send('set-size', 16));
  globalShortcut.register(hotkeys.clickthrough, () => mainWindow?.webContents.send('toggle-clickthrough'));
  globalShortcut.register(hotkeys.undo, () => mainWindow?.webContents.send('undo'));
  globalShortcut.register(hotkeys.redo, () => mainWindow?.webContents.send('redo'));
}

app.whenReady().then(() => {
  console.log('[OpenDraw] App ready');
  createWindow();
  createTray();
  registerAllHotkeys();
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
  console.log('[OpenDraw] Shutting down');
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});