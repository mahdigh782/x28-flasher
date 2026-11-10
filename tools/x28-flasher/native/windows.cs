// A native Windows window for the existing localhost UI; no external browser.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

sealed class FlasherWindow : Form
{
    readonly WebView2 web = new WebView2();
    readonly Label status = new Label { Text = "Starting X28 Flasher…", Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleCenter };
    readonly HttpClient http = new HttpClient(new HttpClientHandler { UseProxy = false, UseCookies = false });
    readonly TaskCompletionSource<Uri> ready = new TaskCompletionSource<Uri>();
    readonly JavaScriptSerializer json = new JavaScriptSerializer();
    readonly Timer monitor = new Timer { Interval = 2000 };
    readonly bool selftest;
    readonly string folder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "X28 Flasher");
    readonly object logLock = new object();
    Process backend;
    Uri origin;
    string token;
    bool closing, allowClose, checking;
    public int ExitCode;

    public FlasherWindow(bool test)
    {
        selftest = test;
        Text = "X28 Flasher";
        ClientSize = new Size(1280, 860);
        MinimumSize = new Size(800, 600);
        StartPosition = FormStartPosition.CenterScreen;
        web.Dock = DockStyle.Fill;
        Controls.Add(web);
        Controls.Add(status);
        http.Timeout = TimeSpan.FromSeconds(3);
        Shown += async delegate { await Start(); };
        FormClosing += CloseRequested;
        monitor.Tick += async delegate {
            if (checking || closing) return;
            checking = true;
            try { await State(); }
            catch { if (!closing && !IsDisposed && backend != null && backend.HasExited) { allowClose = true; Close(); } } // page Quit
            finally { checking = false; }
        };
    }

    void Log(string text)
    {
        try { lock (logLock) File.AppendAllText(Path.Combine(folder, "native.log"), text + Environment.NewLine); }
        catch (IOException) { }
        catch (UnauthorizedAccessException) { }
    }

    async Task Start()
    {
        try
        {
            Directory.CreateDirectory(folder);
            var environment = await CoreWebView2Environment.CreateAsync(null, Path.Combine(folder, "WebView2"));
            if (closing || IsDisposed) return;
            await web.EnsureCoreWebView2Async(environment);
            if (closing || IsDisposed) return;
            web.CoreWebView2.Settings.AreDevToolsEnabled = false;
            web.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
            web.CoreWebView2.NavigationStarting += delegate(object sender, CoreWebView2NavigationStartingEventArgs e) {
                Uri target;
                if (!Uri.TryCreate(e.Uri, UriKind.Absolute, out target)) { e.Cancel = true; return; }
                if (origin != null && target.GetLeftPart(UriPartial.Authority) == origin.AbsoluteUri.TrimEnd('/')) return;
                e.Cancel = true;
                OpenLink(target);
            };
            web.CoreWebView2.NewWindowRequested += delegate(object sender, CoreWebView2NewWindowRequestedEventArgs e) {
                e.Handled = true;
                Uri target;
                if (Uri.TryCreate(e.Uri, UriKind.Absolute, out target)) OpenLink(target);
            };
            var start = new ProcessStartInfo(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "x28-flasher.exe"), "gui") {
                UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true,
                StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8
            };
            start.EnvironmentVariables["X28_NO_BROWSER"] = "1";
            backend = Process.Start(start);
            backend.OutputDataReceived += delegate(object sender, DataReceivedEventArgs e) {
                if (e.Data == null) return;
                Log(e.Data);
                var match = Regex.Match(e.Data, @"^x28-flasher is (?:open|already running) at (http://127\.0\.0\.1:\d+/\?t=[A-Za-z0-9_-]+)$");
                if (match.Success) {
                    if (selftest && e.Data.StartsWith("x28-flasher is already running"))
                        ready.TrySetException(new Exception("Close the existing flasher before running its native self-test."));
                    else ready.TrySetResult(new Uri(match.Groups[1].Value));
                }
            };
            backend.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs e) { if (e.Data != null) Log(e.Data); };
            backend.BeginOutputReadLine();
            backend.BeginErrorReadLine();
            if (await Task.WhenAny(ready.Task, Task.Delay(45000)) != ready.Task) throw new Exception("The backend did not start. See " + Path.Combine(folder, "native.log"));
            var url = await ready.Task;
            if (closing || IsDisposed) return;
            origin = new Uri(url.GetLeftPart(UriPartial.Authority) + "/");
            token = url.Query.Substring(3);
            if (selftest)
            {
                web.CoreWebView2.NavigationCompleted += async delegate(object sender, CoreWebView2NavigationCompletedEventArgs e) {
                    try {
                        if (!e.IsSuccess) throw new Exception("Native UI navigation failed: " + e.WebErrorStatus);
                        var title = await web.CoreWebView2.ExecuteScriptAsync("document.title");
                        if (title.IndexOf("X28", StringComparison.OrdinalIgnoreCase) < 0) throw new Exception("Native UI page did not load: " + title);
                        await State();
                        Log("native window selftest ok");
                    }
                    catch (Exception error) { ExitCode = 1; Log(error.ToString()); }
                    Close();
                };
            }
            web.Source = url;
            status.Visible = false;
            monitor.Start();
        }
        catch (Exception error)
        {
            ExitCode = 1;
            if (Directory.Exists(folder)) Log(error.ToString());
            status.Text = "Could not start X28 Flasher.\n" + error.Message;
            if (selftest) Close();
        }
    }

    static void OpenLink(Uri target)
    {
        if (target.Scheme == "https" || target.Scheme == "http")
            Process.Start(new ProcessStartInfo(target.AbsoluteUri) { UseShellExecute = true });
    }

    async Task<string> Api(HttpMethod method, string path)
    {
        using (var request = new HttpRequestMessage(method, new Uri(origin, path)))
        {
            request.Headers.Add("Cookie", "x28=" + token);
            if (method == HttpMethod.Post) {
                request.Headers.Add("Origin", origin.AbsoluteUri.TrimEnd('/'));
                request.Content = new StringContent("{}", Encoding.UTF8, "application/json");
            }
            using (var response = await http.SendAsync(request)) {
                response.EnsureSuccessStatusCode();
                return await response.Content.ReadAsStringAsync();
            }
        }
    }

    async Task<Dictionary<string, object>> State()
    {
        return json.Deserialize<Dictionary<string, object>>(await Api(HttpMethod.Get, "/api/state"));
    }

    async void CloseRequested(object sender, FormClosingEventArgs e)
    {
        if (allowClose) return;
        e.Cancel = true;
        if (closing) return;
        closing = true;
        monitor.Stop();
        try
        {
            Dictionary<string, object> state = null, job = null;
            if (origin != null) {
                try { state = await State(); } catch { }
                if (state != null && state.ContainsKey("job")) job = state["job"] as Dictionary<string, object>;
                bool busy = job != null && (bool)job["running"];
                if (!selftest && (busy || state == null) && MessageBox.Show(this,
                    "Quitting stops the worker. An interrupted write cannot be undone. Quit anyway?",
                    busy ? "A job is still running" : "Could not check the backend", MessageBoxButtons.YesNo,
                    MessageBoxIcon.Warning, MessageBoxDefaultButton.Button2) != DialogResult.Yes) {
                    closing = false; monitor.Start(); return;
                }
                if (busy) {
                    await Api(HttpMethod.Post, "/api/job/" + job["id"] + "/stop");
                    for (int i = 0; i < 50; i++) {
                        await Task.Delay(100);
                        var current = (await State())["job"] as Dictionary<string, object>;
                        if (current == null || !(bool)current["running"]) break;
                    }
                }
                await Api(HttpMethod.Post, "/api/quit");
            }
        }
        catch (Exception error) { Log(error.ToString()); }
        finally
        {
            if (closing) {
                if (backend != null && !backend.HasExited && !backend.WaitForExit(4000)) backend.Kill();
                allowClose = true;
                Close();
            }
        }
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing) { monitor.Dispose(); http.Dispose(); if (backend != null) backend.Dispose(); }
        base.Dispose(disposing);
    }

    [STAThread]
    static int Main(string[] args)
    {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        using (var window = new FlasherWindow(Array.IndexOf(args, "--selftest") >= 0)) {
            Application.Run(window);
            return window.ExitCode;
        }
    }
}
