#! /usr/bin/env nix-shell
#! nix-shell -i python3.10 -p python310.withPackages(ps:\ [ps.ewmh\ ps.loguru])

# The nix-shell shebang above makes this script executable
# in an environment with nix-shell installed (e.g. NixOS)
# with the packages listed above installed.

import asyncio
import atexit
import os
import textwrap
from dataclasses import dataclass
from pathlib import Path

import ewmh
from Xlib.xobject.drawable import Window
from loguru import logger


@dataclass
class ScratchpadApp:
    window_class: tuple[str, str]
    app_cmd: str | None = None

    @property
    def windows(self) -> list[Window]:
        return [win for win in ew.getClientList() if win.get_wm_class() == self.window_class]

    async def toggle_visible(self):
        wins = self.windows
        just_spawned = False

        # If there are no windows, spawn the app
        if len(wins) == 0:
            logger.info(f"Spawning {self.app_cmd}")
            await asyncio.create_subprocess_exec(
                self.app_cmd,
                start_new_session=True,
                close_fds=True,
            )

            for _ in range(int(win_wait_timeout / win_wait_interval)):
                wins = self.windows
                if len(wins) > 0:
                    just_spawned = True
                    break
                await asyncio.sleep(win_wait_interval)
            else:
                logger.error(f"Failed to find window for {self.window_class}")
                return

        # Toggle visibility of the windows
        for win in wins:
            is_not_active = (
                ew.getWmDesktop(win) != ew.getWmDesktop(ew.getActiveWindow())
                and ew.getWmDesktop(win) != 4294967295
            )  # 0xFFFFFFFF - WM uses this to indicate sticky (should appear in all desktops)

            if just_spawned or is_not_active:
                logger.info(f"Showing {self.window_class}")
                ew.setWmState(win, 1, "_NET_WM_STATE_STICKY")
                ew.setWmState(win, 1, "_NET_WM_STATE_ABOVE")
                ew.setWmState(win, 1, "_NET_WM_TYPE_DOCK")
            else:
                logger.info(f"Hiding {self.window_class}")
                ew.setWmDesktop(win, inactive_desktop)
                ew.setWmState(win, 0, "_NET_WM_STATE_STICKY")
                ew.setWmState(win, 0, "_NET_WM_STATE_ABOVE")
                ew.setWmState(win, 0, "_NET_WM_TYPE_DOCK")


class ScratchpadReaderProtocol(asyncio.Protocol):
    """The protocol that handles data being written to the scratchpad fifo.

    The data is the name of the app to toggle. If the app is not running,
    it will be spawned. If it is running and active, it will be hidden away
    in the last desktop. If it is running but not active, it will be shown.

    We monitor the file located at `scratchpad_fifo_path`, i.e.
    /run/user/1000/scratchpad.fifo, to receive commands. This is faster
    than incurring the overhead of spawning a shell to run the command,
    especially with the `nix-shell` shebang. By just writing the app name
    to the fifo, we can toggle the app instantly without spawning a shell.

    This is done by, e.g.:

        echo spotify > /run/user/1000/scratchpad.fifo

    You can then bind this to a key in your window manager, e.g.:

        bindsym $mod+Shift+s exec echo spotify > /run/user/1000/scratchpad.fifo
    """

    def data_received(self, data: bytes) -> None:
        app_name = data.decode().strip()
        logger.info(f"Handling scratchpad command: {app_name!r}")
        if app_name in scratchpad_apps:
            asyncio.create_task(scratchpad_apps[app_name].toggle_visible())
        else:
            logger.error(f"Unknown app {app_name}")


async def main() -> None:

    logger.info(f"Starting scratchpad daemon [pid: {os.getpid()}]")
    logger.info(f"Known apps: {', '.join(scratchpad_apps.keys())}")

    script = run_dir / "scratchpad.sh"
    if not script.exists():
        script_contents = f"""\
            #!/usr/bin/env sh
            echo "$1" > {fifo_file}
            """
        script.write_text(textwrap.dedent(script_contents))
        script.chmod(0o755)
        logger.info(f"Created {script}")

    if os.path.exists(pid_file):
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())
        try:
            logger.warning(
                f"PID file is present, it seems an instance of the "
                f"program is already running (PID {pid}). Getting (politely) murderous..."
            )
            os.kill(pid, 15)
        except ProcessLookupError:
            logger.warning("Process not found. Huh. Must've been my imagination.")
        else:
            logger.warning("Done, probably.")

    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

    try:
        os.unlink(fifo_file)
    except FileNotFoundError:
        pass
    os.mkfifo(fifo_file, os.O_CREAT | 0o600)

    atexit.register(os.unlink, pid_file)
    atexit.register(os.unlink, fifo_file)

    file_io = os.fdopen(os.open(fifo_file, os.O_RDWR))
    loop = asyncio.get_running_loop()
    await loop.connect_read_pipe(ScratchpadReaderProtocol, file_io)

    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":

    logger.info(f"Running {__file__}")

    run_dir = Path(f"/run/user/{os.getuid()}/scratchpad")
    run_dir.mkdir(parents=True, exist_ok=True)
    pid_file = run_dir / "scratchpad.pid"
    fifo_file = run_dir / "scratchpad.fifo"

    ew = ewmh.EWMH()

    inactive_desktop = ew.getNumberOfDesktops() - 1
    win_wait_timeout = 3
    win_wait_interval = 0.1

    scratchpad_apps = {
        "spotify": ScratchpadApp(
            window_class=("spotify", "Spotify"),
            app_cmd="/home/pedro/.nix-profile/bin/spotify",
        ),
        "obsidian": ScratchpadApp(
            window_class=("obsidian", "obsidian"),
            app_cmd="/home/pedro/.nix-profile/bin/obsidian",
        ),
    }

    asyncio.run(main())
