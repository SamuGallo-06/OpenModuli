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