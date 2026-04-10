"""Apple Reminders integration via AppleScript."""

import asyncio
import logging

log = logging.getLogger("jarvis.reminders")


async def _run_script(script: str, timeout: float = 10.0) -> tuple[bool, str]:
    try:
        proc = await asyncio.create_subprocess_exec(
            "osascript", "-e", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode == 0:
            return True, stdout.decode().strip()
        log.warning(f"Reminders script failed: {stderr.decode().strip()}")
        return False, stderr.decode().strip()
    except asyncio.TimeoutError:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


async def create_reminder(title: str, notes: str = "", list_name: str = "Reminders") -> dict:
    """Create a reminder in the specified list."""
    t = title.replace('"', '\\"')
    n = notes.replace('"', '\\"')
    script = f'''
tell application "Reminders"
    if not (exists list "{list_name}") then
        make new list with properties {{name:"{list_name}"}}
    end if
    tell list "{list_name}"
        make new reminder with properties {{name:"{t}", body:"{n}"}}
    end tell
end tell
'''
    ok, _ = await _run_script(script)
    return {
        "success": ok,
        "confirmation": f"Reminder set: {title}, sir." if ok else "Couldn't create the reminder, sir.",
    }


async def add_to_shopping_list(item: str) -> dict:
    """Add an item to the Shopping List in Reminders."""
    escaped = item.replace('"', '\\"')
    script = f'''
tell application "Reminders"
    if not (exists list "Shopping List") then
        make new list with properties {{name:"Shopping List"}}
    end if
    tell list "Shopping List"
        make new reminder with properties {{name:"{escaped}"}}
    end tell
end tell
'''
    ok, _ = await _run_script(script)
    return {
        "success": ok,
        "confirmation": f"Added {item} to your shopping list, sir." if ok else "Couldn't add to shopping list, sir.",
    }


async def get_reminders(list_name: str = "") -> list[dict]:
    """Get incomplete reminders, optionally from a specific list."""
    if list_name:
        escaped = list_name.replace('"', '\\"')
        script = f'''
tell application "Reminders"
    set output to ""
    tell list "{escaped}"
        set rems to reminders whose completed is false
        repeat with r in rems
            set output to output & (name of r) & "\n"
        end repeat
    end tell
    return output
end tell
'''
    else:
        script = '''
tell application "Reminders"
    set output to ""
    set rems to reminders whose completed is false
    repeat with r in rems
        set output to output & (name of r) & "\n"
    end repeat
    return output
end tell
'''
    ok, out = await _run_script(script)
    if not ok or not out.strip():
        return []
    return [{"title": line.strip()} for line in out.strip().split("\n") if line.strip()]


async def complete_reminder(title_match: str) -> dict:
    """Mark the first incomplete reminder matching title_match as complete."""
    escaped = title_match.replace('"', '\\"')
    script = f'''
tell application "Reminders"
    set rems to reminders whose name contains "{escaped}" and completed is false
    if (count of rems) > 0 then
        set completed of item 1 of rems to true
        return "done"
    else
        return "not found"
    end if
end tell
'''
    ok, out = await _run_script(script)
    if not ok or out == "not found":
        return {"success": False, "confirmation": f"Couldn't find a reminder matching '{title_match}', sir."}
    return {"success": True, "confirmation": "Marked as done, sir."}


def format_reminders_for_voice(reminders: list[dict]) -> str:
    """Format reminder list for voice output."""
    if not reminders:
        return "No pending reminders."
    items = [r["title"] for r in reminders[:5]]
    return "Your reminders: " + ", ".join(items) + "."
