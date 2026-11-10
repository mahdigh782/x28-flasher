"""No hardware: run with the frozen binary's --run-script to check the shipped GUI plumbing."""
import sys
import tempfile
import time
import types
from pathlib import Path

import gui


def wait(predicate):
    deadline = time.monotonic() + 20
    while not predicate():
        if time.monotonic() >= deadline:
            raise AssertionError('GUI smoke test timed out')
        time.sleep(0.02)


def command(script):
    return [sys.executable, '--run-script', str(script)]


with tempfile.TemporaryDirectory() as folder:
    folder = Path(folder)
    tool = folder / 'prompt.py'
    tool.write_text("import sys\nassert sys.stdin.isatty() and sys.stdout.isatty()\nanswer = input('Confirm: ')\nassert answer == 'WRITE test'\nprint('confirmed', flush=True)\n")
    job = gui.Job('smoke', command(tool))
    try:
        wait(lambda: 'Confirm: ' in job.tail)
        assert job.send('WRITE test')
        wait(lambda: job.code is not None)
        assert job.code == 0, job.lines
        assert 'confirmed' in job.lines, job.lines
    finally:
        job.stop(force=True)
        wait(lambda: job.code is not None)
    host = folder / 'host.py'
    host.write_text("import queue, sys\nfrom session_host import listen, say\ncommands = queue.Queue()\nlisten(sys.argv[1], commands)\nsay('X28SESSION connected')\nwhile True:\n    cmd = commands.get()\n    if cmd['kind'] == 'quit': break\n    say('X28DONE %s 0' % cmd['id'])\n")
    sock = str(folder / 'session.sock')
    app = types.SimpleNamespace(session=None)
    link = gui.SessionLink(command(host) + [sock], {'X28_SESSION_KEY': 'ab' * 32}, sock, app)
    app.session = link
    try:
        for _ in range(2):
            job = gui.RunJob('smoke', link)
            link.active = job
            assert link.submit({'kind': 'smoke', 'id': job.id})
            wait(lambda: job.code is not None)
            assert job.code == 0, job.lines
        assert link.connected
        link.disconnect()
        assert link.code == 0
    finally:
        link.disconnect(force=True)
print('frozen GUI smoke test ok')
