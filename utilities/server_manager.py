# OpenModuli - Open Source, Self-Hosted Form Builder and Management System.
# Copyright (C) 2025 Samuele Gallicani
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import os
import signal
import sys
import threading

from time import sleep
from rich.console import Console

console = Console()


def _run_in_background(action, delay: float = 0.3):
    """Run a process-control action after a short delay in a daemon thread.

    The delay gives Flask enough time to send the HTTP response before
    stopping/replacing the current process.
    """

    def _runner():
        if delay > 0:
            sleep(delay)
        action()

    worker = threading.Thread(target=_runner, daemon=True)
    worker.start()


def exit_open_moduli():
    os._exit(0)
    
def terminate_open_moduli():
    console.print("[yellow]Chiusura in corso...[/yellow]")
    try:
        os.kill(os.getpid(), signal.SIGTERM)
    except Exception:
        # Fallback for environments where SIGTERM is unavailable.
        os._exit(0)
    
def reboot_system():
    console.print("[yellow]Riavvio in corso...[/yellow]")

    def _restart_process():
        python_exec = sys.executable
        argv = [python_exec, *sys.argv]
        os.execv(python_exec, argv)

    _run_in_background(_restart_process)
    
def shutdown_system():
    console.print("[yellow]Spegnimento in corso...[/yellow]")
    _run_in_background(terminate_open_moduli)