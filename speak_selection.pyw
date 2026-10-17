"""
speak_selection.pyw — Reads the selected text aloud using online neural voices (via edge-tts).

Usage:   select text in any app and press the hotkey (see HOTKEY below). Press it again to stop.
Install: pip install edge-tts keyboard pyperclip pystray pillow
Run:     double-click (runs with pythonw, no console window). An icon stays in the system tray
         (grey when idle, green while speaking); right-click > Quit to close it.
Start with Windows: add a shortcut to this file in  shell:startup
"""
import asyncio
import atexit
import ctypes
import os
import queue
import re
import shutil
import tempfile
import threading
import time
import winsound

import edge_tts
import keyboard
import pyperclip
import pystray
from PIL import Image, ImageDraw

# ── Settings ──────────────────────────────────────────────────────────────────
HOTKEY = "ctrl+alt+l"
VOICE = "es-ES-AlvaroNeural"   # others: es-ES-ElviraNeural. List them all: edge-tts --list-voices
CODE_BLOCK_TEXT = "Bloque de código omitido."   # spoken instead of code blocks: keep it in VOICE's language
LINK_TEXT = "enlace"                          # spoken instead of bare URLs: keep it in VOICE's language
RATE = "+0%"                   # speed: "+20%", "-10%"...
FIRST_CHUNK = 150              # characters in the first chunk (the smaller, the sooner it starts speaking)
MAX_CHUNK = 600                # characters in the remaining chunks

# ── State ─────────────────────────────────────────────────────────────────────
user32 = ctypes.windll.user32
winmm = ctypes.windll.winmm
TMP = tempfile.mkdtemp(prefix="speak_selection_")
atexit.register(shutil.rmtree, TMP, ignore_errors=True)
stop_event = threading.Event()
worker = None
producer = None
lock = threading.Lock()


def mci(command):
    buf = ctypes.create_unicode_buffer(256)
    winmm.mciSendStringW(command, buf, 255, 0)
    return buf.value


# ── Selection capture ─────────────────────────────────────────────────────────
def copy_selection():
    """Copy the selection with Ctrl+C, then restore the previous clipboard contents."""
    keys = HOTKEY.split("+")
    while any(keyboard.is_pressed(k) for k in keys):   # wait for the hotkey to be released
        time.sleep(0.02)
    try:
        previous = pyperclip.paste()
    except pyperclip.PyperclipException:
        previous = None
    seq = user32.GetClipboardSequenceNumber()
    keyboard.send("ctrl+c")
    for _ in range(60):
        time.sleep(0.01)
        if user32.GetClipboardSequenceNumber() != seq:
            break
    else:
        return ""                                       # nothing was selected
    time.sleep(0.05)
    text = pyperclip.paste()
    if previous is not None:
        pyperclip.copy(previous)
    return text


# ── Text cleanup (Markdown, emojis, links) ────────────────────────────────────
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D\u20E3]")


def clean(text):
    text = re.sub(r"```.*?```", lambda m: f"\n{CODE_BLOCK_TEXT}\n", text, flags=re.S)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)          # [text](url) -> text
    text = re.sub(r"https?://\S+", lambda m: LINK_TEXT, text)
    text = EMOJI.sub("", text)
    text = re.sub(r"^\s*(?:[-*•]|\d+\.)\s+", "", text, flags=re.M)  # bullets and numbering
    text = re.sub(r"[`*#>|]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"([^\s.!?:;,])[ \t]*\n", r"\1.\n", text)       # pause at the end of each line
    return text.strip()


def split_chunks(text):
    parts, current = [], ""
    for sentence in re.split(r"(?<=[.!?:;])\s+|\n+", text):
        sentence = sentence.strip()
        if not sentence:
            continue
        limit = FIRST_CHUNK if not parts else MAX_CHUNK
        if current and len(current) + len(sentence) > limit:
            parts.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        parts.append(current)
    return parts


# ── Synthesis and playback (synthesizes the next chunk while the current one plays) ──
def produce(parts, q, stop):
    loop = asyncio.new_event_loop()
    try:
        for i, part in enumerate(parts):
            if stop.is_set():
                break
            path = os.path.join(TMP, f"{time.time_ns()}_{i}.mp3")
            loop.run_until_complete(edge_tts.Communicate(part, VOICE, rate=RATE).save(path))
            if stop.is_set():                           # stopped during synthesis: nobody will play it
                os.remove(path)
                break
            q.put(path)
    except Exception as exc:                            # no internet, invalid voice...
        q.put(exc)
    finally:
        q.put(None)
        loop.close()


def play(path, stop):
    mci(f'open "{path}" type mpegvideo alias speech')
    mci("play speech")
    time.sleep(0.05)
    while not stop.is_set() and mci("status speech mode") == "playing":
        time.sleep(0.05)
    mci("stop speech")
    mci("close speech")
    try:
        os.remove(path)
    except OSError:
        pass


def run(stop):
    global producer
    text = clean(copy_selection())
    if not text:
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
        return
    set_speaking(True)
    try:
        q = queue.Queue()
        producer = threading.Thread(target=produce, args=(split_chunks(text), q, stop), daemon=True)
        producer.start()
        while not stop.is_set():
            try:
                item = q.get(timeout=0.1)               # timeout: stop without waiting for the ongoing synthesis
            except queue.Empty:
                continue
            if item is None:
                break
            if isinstance(item, Exception):
                winsound.MessageBeep(winsound.MB_ICONHAND)
                break
            play(item, stop)
    finally:
        set_speaking(False)


def on_hotkey():
    global worker, stop_event
    with lock:
        if worker and worker.is_alive():
            stop_event.set()                            # second press: stop
            return
        stop_event = threading.Event()                  # one per reading: stopping one never revives another's threads
        worker = threading.Thread(target=run, args=(stop_event,), daemon=True)
        worker.start()


# ── System tray icon ──────────────────────────────────────────────────────────
def make_icon(color):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, 60, 60), fill=color)
    d.polygon([(18, 26), (28, 26), (40, 14), (40, 50), (28, 38), (18, 38)], fill="white")  # speaker
    return img


ICON_IDLE = make_icon((120, 120, 130))
ICON_SPEAKING = make_icon((40, 170, 90))
tray = None
speaking = False


def set_speaking(value):
    global speaking
    speaking = value
    if tray:
        tray.icon = ICON_SPEAKING if value else ICON_IDLE
        tray.title = f"Speak Selection — {'speaking…' if value else HOTKEY.upper()}"
        tray.update_menu()                              # on Windows the menu does not re-evaluate "enabled" by itself


def stop_reading(icon=None, item=None):
    stop_event.set()


def quit_app(icon, item):
    stop_event.set()
    keyboard.unhook_all()
    for t in (worker, producer):                        # leave no files open when TMP is deleted
        if t:
            t.join(timeout=3)
    icon.stop()


if __name__ == "__main__":
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    mutex = kernel32.CreateMutexW(None, False, "Local\\speak_selection")   # lives until the process exits
    if ctypes.get_last_error() == 183:                  # ERROR_ALREADY_EXISTS: another instance is running
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
        raise SystemExit
    keyboard.add_hotkey(HOTKEY, on_hotkey)
    tray = pystray.Icon(
        "speak_selection",
        ICON_IDLE,
        f"Speak Selection — {HOTKEY.upper()}",
        menu=pystray.Menu(
            pystray.MenuItem("Stop reading", stop_reading, default=True, enabled=lambda item: speaking),
            pystray.MenuItem("Quit", quit_app),
        ),
    )
    tray.run()   # blocks until "Quit"
