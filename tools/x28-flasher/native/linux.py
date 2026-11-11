#!/usr/bin/python3
"""GTK/WebKit desktop window for the bundled backend; run with the distro Python, not PyInstaller."""
import argparse
import http.client
import json
import os
import subprocess
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import GLib, Gtk, WebKit2  # noqa: E402


class Window:
    def __init__(self, selftest=False):
        self.selftest, self.code = selftest, 0
        self.backend, self.origin, self.token = None, None, None
        self.closing = self.loaded = False
        self.started = time.monotonic()
        self.folder = Path(GLib.get_user_state_dir()) / 'x28-flasher'
        self.folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.log = (self.folder / 'native.log').open('a', encoding='utf-8', buffering=1)
        self.window = Gtk.Window(title='X28 Flasher')
        self.window.set_icon_name('x28-flasher')
        self.window.set_default_size(1280, 860)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.connect('delete-event', self.close)
        data = WebKit2.WebsiteDataManager(base_data_directory=str(self.folder / 'webkit'),
                                         base_cache_directory=str(Path(GLib.get_user_cache_dir()) / 'x28-flasher'))
        self.web = WebKit2.WebView(web_context=WebKit2.WebContext(website_data_manager=data))
        self.web.connect('decide-policy', self.navigation)
        self.web.connect('load-changed', self.load_changed)
        self.web.connect('load-failed', self.load_failed)
        self.web.connect('web-process-terminated', lambda web, reason: self.fail('The UI engine stopped. See ' + self.log.name))
        self.window.add(self.web)
        self.web.load_html('<title>X28 Flasher</title><p>Starting X28 Flasher…</p>', None)
        self.window.show_all()
        GLib.timeout_add(1000, self.monitor)
        try:
            backend = Path(__file__).resolve().with_name('x28-flasher')
            self.backend = subprocess.Popen([str(backend), 'gui'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            text=True, encoding='utf-8', errors='replace',
                                            env={**os.environ, 'X28_NO_BROWSER': '1', 'PYTHONUNBUFFERED': '1'})
            threading.Thread(target=self.output, daemon=True).start()
        except OSError as error:
            self.fail(str(error))

    def output(self):
        for line in self.backend.stdout:
            self.log.write(line)
            for prefix in ('x28-flasher is open at ', 'x28-flasher is already running at '):
                if line.startswith(prefix):
                    GLib.idle_add(self.load, line[len(prefix):].strip(), 'already running' in prefix)

    def load(self, url, reused):
        if self.closing:
            return False
        parsed = urlparse(url)
        token = parse_qs(parsed.query).get('t', [''])[0]
        if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not parsed.port or not token:
            self.fail('Invalid backend address')
        elif self.selftest and reused:
            self.fail('Close the existing flasher before running its native self-test.')
        else:
            self.origin, self.token = f'http://127.0.0.1:{parsed.port}', token
            self.web.load_uri(url)
        return False

    def api(self, path, post=False):
        conn = http.client.HTTPConnection('127.0.0.1', urlparse(self.origin).port, timeout=3)
        try:
            headers = {'Cookie': f'x28={self.token}'}
            if post:
                headers.update({'Origin': self.origin, 'Content-Type': 'application/json'})
            conn.request('POST' if post else 'GET', path, body='{}' if post else None, headers=headers)
            response = conn.getresponse()
            if response.status != 200:
                raise OSError(f'Backend returned HTTP {response.status}')
            return json.loads(response.read())
        finally:
            conn.close()

    def navigation(self, web, decision, kind):
        if kind not in (WebKit2.PolicyDecisionType.NAVIGATION_ACTION, WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION):
            return False
        uri = decision.get_navigation_action().get_request().get_uri()
        parsed = urlparse(uri)
        if uri == 'about:blank' or (self.origin and f'{parsed.scheme}://{parsed.netloc}' == self.origin):
            return False
        decision.ignore()
        if parsed.scheme in ('https', 'http'):
            webbrowser.open(uri)
        return True

    def load_changed(self, web, event):
        if self.origin and event == WebKit2.LoadEvent.FINISHED and not self.loaded and (web.get_uri() or '').startswith(self.origin + '/'):
            self.loaded = True
            if self.selftest:
                try:
                    assert 'X28' in (web.get_title() or ''), 'native UI page did not load'
                    self.api('/api/state')
                    self.log.write('native window selftest ok\n')
                except Exception as error:
                    self.code = 1
                    self.log.write(str(error) + '\n')
                self.close()

    def load_failed(self, web, event, uri, error):
        if error.matches(WebKit2.network_error_quark(), WebKit2.NetworkError.CANCELLED) or error.matches(
                WebKit2.policy_error_quark(), WebKit2.PolicyError.FRAME_LOAD_INTERRUPTED_BY_POLICY_CHANGE):
            return False
        self.fail('Could not load the native UI: ' + error.message)
        return False

    def fail(self, message):
        if self.closing:
            return
        self.code = 1
        self.log.write(message + '\n')
        if self.selftest:
            self.close()
        else:
            dialog = Gtk.MessageDialog(transient_for=self.window, modal=True, message_type=Gtk.MessageType.ERROR,
                                       buttons=Gtk.ButtonsType.CLOSE, text=message)
            dialog.run()
            dialog.destroy()
            self.close()

    def monitor(self):
        if self.closing:
            return False
        if not self.loaded and time.monotonic() - self.started > 45:
            self.fail('The backend did not start. See ' + self.log.name)
        elif self.loaded:
            try:
                self.api('/api/state')
            except OSError:
                if self.backend.poll() is not None:
                    self.window.destroy()
                    Gtk.main_quit()  # the page's Quit button stopped the backend
                    return False
        return not self.closing

    def close(self, *args):
        if self.closing:
            return True
        state = None
        if self.origin:
            try:
                state = self.api('/api/state')
            except OSError:
                pass
        job = (state or {}).get('job') or {}
        if not self.selftest and self.origin and (state is None or job.get('running')):
            dialog = Gtk.MessageDialog(transient_for=self.window, modal=True, message_type=Gtk.MessageType.WARNING,
                                       buttons=Gtk.ButtonsType.YES_NO, text='Quit X28 Flasher?')
            dialog.format_secondary_text('Quitting stops the worker. An interrupted write cannot be undone. Quit anyway?')
            dialog.set_default_response(Gtk.ResponseType.NO)
            answer = dialog.run()
            dialog.destroy()
            if answer != Gtk.ResponseType.YES:
                return True
        self.closing = True
        self.window.hide()
        try:
            if self.origin:
                if job.get('running'):
                    self.api(f"/api/job/{job['id']}/stop", post=True)
                    for _ in range(50):
                        if not (self.api('/api/state').get('job') or {}).get('running'):
                            break
                        time.sleep(0.1)
                self.api('/api/quit', post=True)
                # Also wait when attached to an existing backend, so no hidden server is left running.
                for _ in range(80):
                    time.sleep(0.1)
                    try:
                        self.api('/api/state')
                    except OSError:
                        break
        except OSError as error:
            self.log.write(str(error) + '\n')
        finally:
            if self.backend and self.backend.poll() is None:
                try:
                    self.backend.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.backend.kill()
                    self.backend.wait()
            self.window.destroy()
            if Gtk.main_level():
                Gtk.main_quit()
        return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    GLib.set_prgname('x28-flasher')
    GLib.set_application_name('X28 Flasher')
    window = Window(args.selftest)
    if not window.closing:
        Gtk.main()
    return window.code


if __name__ == '__main__':
    raise SystemExit(main())
