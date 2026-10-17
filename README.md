# speak-selection

[![Release](https://img.shields.io/github/v/release/AlexisDx13/speak-selection)](https://github.com/AlexisDx13/speak-selection/releases/latest)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows-0078D6)](#requirements)
[![License: MIT](https://img.shields.io/github/license/AlexisDx13/speak-selection)](LICENSE)

Read the selected text aloud on Windows with a global hotkey, using online neural voices.

Select text in any application, press `Ctrl+Alt+L` and it is read aloud. Press it again to stop.

> [!NOTE]
> This project is not affiliated with, endorsed by or connected to Microsoft. It relies on [edge-tts](https://github.com/rany2/edge-tts), which uses an unofficial, undocumented online text-to-speech service. That service may change or stop working at any time without notice.

## Features

- **Global hotkey**: works in any application; the selection is copied and your clipboard is restored afterwards.
- **Text cleanup**: strips Markdown formatting, emojis and list markers; reads Markdown links by their text only; replaces bare URLs and fenced code blocks with a short spoken placeholder.
- **Fast start**: the text is synthesized in chunks, so playback starts after the first chunk while the rest is synthesized in the background.
- **System tray icon**: grey when idle, green while speaking; right-click to stop reading or quit.
- **Lightweight**: a single script, no console window, only one instance runs at a time.

## Requirements

- Windows.
- Python 3.10 or later.
- An internet connection (speech is synthesized online).

## Installation

Download [`speak_selection.pyw`](speak_selection.pyw) and [`requirements.txt`](requirements.txt) (or clone the repository), then install the dependencies:

```bash
pip install -r requirements.txt
```

## Usage

1. Double-click `speak_selection.pyw`. It runs with `pythonw`, without a console window, and an icon appears in the system tray.
2. Select text in any application and press `Ctrl+Alt+L`.
3. Press `Ctrl+Alt+L` again, or use **Stop reading** in the tray menu, to stop.
4. Right-click the tray icon and choose **Quit** to close it.

If nothing is selected, or if it is already running when you start it again, you hear a short beep; if synthesis fails (for example, without an internet connection) you hear an error sound.

To start it with Windows, press `Win+R`, type `shell:startup` and add a shortcut to `speak_selection.pyw` in the folder that opens.

## Configuration

Edit the constants in the `Settings` block at the top of `speak_selection.pyw` and restart it:

| Setting | Default | Description |
|---|---|---|
| `HOTKEY` | `"ctrl+alt+l"` | Global hotkey, in [keyboard](https://github.com/boppreh/keyboard) syntax. |
| `VOICE` | `"es-ES-AlvaroNeural"` | Voice to use. List all available voices with `edge-tts --list-voices`. |
| `CODE_BLOCK_TEXT` | `"Bloque de código omitido."` | Spoken instead of code blocks. Keep it in the voice's language. |
| `LINK_TEXT` | `"enlace"` | Spoken instead of bare URLs. Keep it in the voice's language. |
| `RATE` | `"+0%"` | Speaking rate, e.g. `"+20%"` or `"-10%"`. |
| `FIRST_CHUNK` | `150` | Characters in the first chunk; smaller starts speaking sooner. |
| `MAX_CHUNK` | `600` | Characters in the remaining chunks. |

The default voice is Spanish. To use another language, change `VOICE` and translate `CODE_BLOCK_TEXT` and `LINK_TEXT` accordingly.

## Known limitations

- **The hotkey is not exclusive**: the active application also receives the key combination. If an application already uses `Ctrl+Alt+L`, both actions are triggered; change `HOTKEY` to avoid the conflict.
- **Copying the selection simulates `Ctrl+C`**: text cannot be read in applications where `Ctrl+C` does not copy the selection.
- **Windows only**: playback and single-instance detection use Windows APIs.

## License

[MIT](LICENSE)
