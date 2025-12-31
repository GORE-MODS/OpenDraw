<div align="center">
<img width="2560" height="1440" alt="GHBanner" src="https://github.com/GORE-MODS/Shit-forgit/blob/main/OpenDraw.png" />
</div>

# OpenDraw

This will now only be able to download/install OpenDraw on snap/deb files. The source code will always be here.
Transparent, always-on-top drawing tool built for streamers, YouTubers, rage artists, and anyone who needs to circle, draw arrows, or scribble random stuff live on stream without green screen hacks.

Think Epic Pen / OBS Draw plugin but **open-source**, free, no ads, no telemetry, no corporate bullshit. Works perfectly with OBS/Streamlabs (Window Capture or Display Capture → add Chroma Key if needed, but transparency usually just works).

**Why this exists:** Because most drawing tools either suck on Linux, steal focus from games, connect lines like idiots, or cost money. We fixed all that.

## Features (the good shit)
- Fully transparent overlay – draw over ANYTHING (games, desktop, browser, whatever)
- Global hotkeys – toggle, clear, color/size switches even when hidden
- Click-through mode – draw then click through to the game underneath
- Undo (Ctrl+Z) / Redo (Ctrl+Y) – full stroke history
- No random connecting lines between strokes (fixed the canvas path bullshit)
- Toolbar for mouse users + color/size presets
- Resize preserves your drawing
- Linux-friendly (NVIDIA/Wayland flags included)
- No focus steal – games/streams stay in control
- Light as fuck for dev, easy to package

## Hotkeys (Global – work system-wide)

| Key Combo          | Action                              |
|--------------------|-------------------------------------|
| Ctrl + Shift + D   | Toggle overlay (show/hide)          |
| Ctrl + Shift + C   | Clear entire canvas                 |
| Ctrl + Shift + R   | Set color to **Red**                |
| Ctrl + Shift + B   | Set color to **Blue**               |
| Ctrl + Shift + W   | Set color to **White**              |
| Ctrl + Shift + G   | Set color to **Green**              |
| Ctrl + Shift + 1   | Thin brush (4px)                    |
| Ctrl + Shift + 2   | Thick brush (16px)                  |
| Ctrl + Shift + T   | Quick toggle click-through          |
| Ctrl + Z           | Undo last stroke or clear           |
| Ctrl + Y           | Redo                                |

Toolbar (top-left when visible) has buttons for the same stuff + extra colors.

## Quick Start (Dev Mode)

1. Clone or download this repo
   ```bash
   git clone https://github.com/GORE-MODS/OpenDraw
   cd OpenDraw
   ```
2. Install dependencies
   ```bash
   npm install
   ```
3. Run it (Linux transparency flags included in package.json)
   ```bash
   npm start
   ```
   App starts hidden by design
   Hit Ctrl + Shift + D to show the overlay
   Draw like a savage
   Ctrl + Shift + C to nuke it
   Ctrl + Z / Y for undo/redo
   
   # Linux Troubleshooting (the real talk)
   Window invisible/black/no transparency? Try these one by one:
     ```bash
     # One-time setup
     npm install --save-dev @electron-forge/cli
     npx electron-forge import

     # Build for your platform
     npm run make
     ```
     NVIDIA cards + Wayland = pain. --disable-gpu usually fixes alpha channel. Add --no-sandbox if Electron gets mad about permissions.

     # Packaging for Release (turn it into a real app)
     ```bash
     # One-time setup
    npm install --save-dev @electron-forge/cli
    npx electron-forge import

    # Build for your platform
    npm run make
    ```
    Outputs land in out/make/:

    Windows → .exe + portable
    Linux → .deb / .rpm / AppImage
    macOS → .dmg

   # Planned / Want to Add? (DM me on discord.)

   System tray icon + menu (quit, settings, etc) (Added in V1.1)
   
   Save/load drawings as transparent PNG (hotkey?)
   
   Arrow tool / straight lines (hold Shift)
   
   Opacity slider
   
   Text tool / meme stamps
   
   Tablet pressure sensitivity
   
   Rust + Tauri port (tiny <10MB binary)

   Fork it, mod it, make it yours. No limits.
   
   # License
   
   Just don't sue me if your Twitch ban comes from drawing "sus things" on stream.
   
   Open Freedom License - You are free to do anything to it.
   
   Made with ❤ by GORE
