"""Mac system controls: volume, app control, Apple Music, text input, window management."""

import asyncio
import logging

log = logging.getLogger("jarvis.mac")


async def _run_script(script: str, timeout: float = 10.0) -> tuple[bool, str]:
    """Run an AppleScript and return (success, output)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode == 0:
            return True, stdout.decode().strip()
        log.warning(f"Script failed: {stderr.decode().strip()}")
        return False, stderr.decode().strip()
    except asyncio.TimeoutError:
        log.warning("AppleScript timed out")
        return False, "timeout"
    except Exception as e:
        log.error(f"Script error: {e}")
        return False, str(e)


# ---------------------------------------------------------------------------
# Volume Control
# ---------------------------------------------------------------------------

async def set_volume(level: int) -> dict:
    """Set Mac output volume 0-100."""
    level = max(0, min(100, level))
    ok, _ = await _run_script(f"set volume output volume {level}")
    return {
        "success": ok,
        "confirmation": f"Volume set to {level}%, sir." if ok else "Couldn't adjust the volume, sir.",
    }


async def get_volume() -> int:
    """Return current output volume level (0-100), or -1 on error."""
    ok, out = await _run_script("output volume of (get volume settings)")
    try:
        return int(out) if ok else -1
    except ValueError:
        return -1


async def mute_volume() -> dict:
    ok, _ = await _run_script("set volume with output muted")
    return {"success": ok, "confirmation": "Muted, sir." if ok else "Couldn't mute, sir."}


async def unmute_volume() -> dict:
    ok, _ = await _run_script("set volume without output muted")
    return {"success": ok, "confirmation": "Unmuted, sir." if ok else "Couldn't unmute, sir."}


# ---------------------------------------------------------------------------
# App Control
# ---------------------------------------------------------------------------

async def open_app(app_name: str) -> dict:
    """Open any Mac application by name."""
    script = f'tell application "{app_name}" to activate'
    ok, _ = await _run_script(script)
    if not ok:
        ok2, _ = await _run_script(f'launch application "{app_name}"')
        if ok2:
            return {"success": True, "confirmation": f"Opening {app_name}, sir."}
        return {"success": False, "confirmation": f"Couldn't find {app_name}, sir."}
    return {"success": True, "confirmation": f"Opening {app_name}, sir."}


async def quit_app(app_name: str) -> dict:
    """Quit a Mac application."""
    ok, _ = await _run_script(f'tell application "{app_name}" to quit')
    return {
        "success": ok,
        "confirmation": f"Closed {app_name}, sir." if ok else f"Couldn't close {app_name}, sir.",
    }


# ---------------------------------------------------------------------------
# Apple Music Control
# ---------------------------------------------------------------------------

async def music_play(query: str = "") -> dict:
    """Play music in Apple Music. Optionally search library for query."""
    if query:
        escaped = query.replace('"', '\\"')
        script = f'''
tell application "Music"
    activate
    set sr to search playlist "Library" for "{escaped}"
    if (count of sr) > 0 then
        play item 1 of sr
        return "playing"
    else
        return "not found"
    end if
end tell
'''
        ok, out = await _run_script(script, timeout=15)
        if not ok or out == "not found":
            return {"success": False, "confirmation": f"Couldn't find {query!r} in your library, sir."}
        return {"success": True, "confirmation": f"Playing {query}, sir."}
    else:
        ok, _ = await _run_script('tell application "Music" to play')
        return {"success": ok, "confirmation": "Playing, sir." if ok else "Nothing to play, sir."}


async def music_pause() -> dict:
    ok, _ = await _run_script('tell application "Music" to pause')
    return {"success": ok, "confirmation": "Paused, sir." if ok else "Music isn't playing, sir."}


async def music_next() -> dict:
    ok, _ = await _run_script('tell application "Music" to next track')
    return {"success": ok, "confirmation": "Skipped, sir." if ok else "Couldn't skip, sir."}


async def music_previous() -> dict:
    ok, _ = await _run_script('tell application "Music" to previous track')
    return {"success": ok, "confirmation": "Going back, sir." if ok else "Couldn't go back, sir."}


async def music_get_current() -> dict:
    """Return info about the currently playing track."""
    script = '''
tell application "Music"
    if player state is playing then
        return (name of current track) & " ||| " & (artist of current track)
    else
        return "not playing"
    end if
end tell
'''
    ok, out = await _run_script(script)
    if not ok or out == "not playing":
        return {"playing": False, "track": None, "artist": None}
    parts = out.split("|||")
    return {
        "playing": True,
        "track": parts[0].strip() if len(parts) > 0 else "",
        "artist": parts[1].strip() if len(parts) > 1 else "",
    }


async def music_set_volume(level: int) -> dict:
    level = max(0, min(100, level))
    ok, _ = await _run_script(f'tell application "Music" to set sound volume to {level}')
    return {"success": ok, "confirmation": f"Music volume at {level}%, sir." if ok else "Couldn't adjust, sir."}


# ---------------------------------------------------------------------------
# Text Input
# ---------------------------------------------------------------------------

async def type_text(text: str) -> dict:
    """Type text into the currently focused application."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    script = f'''
tell application "System Events"
    keystroke "{escaped}"
end tell
'''
    ok, _ = await _run_script(script)
    return {
        "success": ok,
        "confirmation": "Done, sir." if ok else "Couldn't type — Accessibility permissions may be needed.",
    }


# ---------------------------------------------------------------------------
# Window Management
# ---------------------------------------------------------------------------

async def move_window(app_name: str, x: int, y: int, width: int, height: int) -> dict:
    """Move and resize the front window of an app."""
    script = f'''
tell application "System Events"
    tell process "{app_name}"
        set position of window 1 to {{{x}, {y}}}
        set size of window 1 to {{{width}, {height}}}
    end tell
end tell
'''
    ok, _ = await _run_script(script)
    return {
        "success": ok,
        "confirmation": f"Moved {app_name} window, sir." if ok else f"Couldn't move {app_name} window, sir.",
    }


async def maximize_window(app_name: str) -> dict:
    """Zoom/maximize the front window of an app."""
    script = f'''
tell application "System Events"
    tell process "{app_name}"
        click button 1 of window 1
    end tell
end tell
'''
    ok, _ = await _run_script(script)
    return {"success": ok, "confirmation": f"Maximized {app_name}, sir." if ok else "Couldn't maximize, sir."}
