using System;
using System.IO;
using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text;
using System.Threading;

// One immutable asset, one bounded worker, no filesystem routing or child process.
public sealed class IW7DoomHttp : IDisposable
{
    public const string Route = "/mods/paris_enemy_doom_helmet_rigid_a/mod.ff";
    public string AssetRoute { get; private set; }
    private readonly byte[] payload;
    private readonly string journal;
    private readonly TcpListener listener;
    private readonly Thread worker;
    private readonly object sync = new object();
    private TcpClient active;
    private volatile bool stopping;
    private int gets;
    public string SHA256 { get; private set; }
    public string BaseUrl { get; private set; }
    public string Error { get; private set; }
    public bool Stopped { get { return !worker.IsAlive; } }
    public int CompletedGets { get { return Volatile.Read(ref gets); } }

    public IW7DoomHttp(byte[] bytes, string expectedHash, string logPath)
        : this(bytes, expectedHash, logPath, Route) { }

    public IW7DoomHttp(byte[] bytes, string expectedHash, string logPath, string route)
    {
        // Explicit experiment routes only; no arbitrary paths or directory serving.
        if (route != Route)
            throw new ArgumentException("Unreviewed laboratory asset route.");
        AssetRoute = route;
        if (bytes == null || bytes.Length != 91036)
            throw new ArgumentException("Exact measured Doom helmet FF size required.");
        payload = (byte[])bytes.Clone();
        using (var hash = System.Security.Cryptography.SHA256.Create())
            SHA256 = BitConverter.ToString(hash.ComputeHash(payload)).Replace("-", "");
        if (!String.Equals(SHA256, expectedHash, StringComparison.OrdinalIgnoreCase) ||
            SHA256 != "AD570ACED38C25305AF1C4C608B294C42C9951E71EE5C79E536E67D596166711")
            throw new ArgumentException("Doom HTTP payload hash mismatch.");
        journal = Path.GetFullPath(logPath);
        // Never append evidence from an earlier run.
        using (new FileStream(journal, FileMode.CreateNew, FileAccess.Write, FileShare.Read)) { }
        listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start(4);
        BaseUrl = "http://127.0.0.1:" + ((IPEndPoint)listener.LocalEndpoint).Port;
        worker = new Thread(Run) { IsBackground = true, Name = "IW7DoomHttp" };
        try { worker.Start(); } catch { listener.Stop(); throw; }
    }

    private void Run()
    {
        try
        {
            int attempts = 0;
            while (!stopping && attempts++ < 64)
            {
                TcpClient client = listener.AcceptTcpClient();
                lock (sync) { if (stopping) { client.Dispose(); break; } active = client; }
                try { Serve(client); }
                catch (IOException) { /* bounded incomplete request/disconnected recipient */ }
                catch (SocketException) { }
                finally { lock (sync) { active = null; } client.Dispose(); }
            }
            if (!stopping) Error = "HTTP request budget exhausted.";
        }
        catch (Exception e) { if (!stopping) Error = e.GetType().Name + ": " + e.Message; }
        finally { listener.Stop(); }
    }

    private void Serve(TcpClient client)
    {
        client.ReceiveTimeout = 2000; client.SendTimeout = 2000;
        NetworkStream stream = client.GetStream();
        Stopwatch timeout = Stopwatch.StartNew();
        byte[] header = new byte[4096]; int length = 0;
        while (length < header.Length)
        {
            if (timeout.ElapsedMilliseconds >= 2000) return;
            int b = stream.ReadByte(); if (b < 0) return;
            header[length++] = (byte)b;
            if (length >= 4 && header[length-4] == 13 && header[length-3] == 10 &&
                header[length-2] == 13 && header[length-1] == 10) break;
        }
        if (length < 4 || header[length-4] != 13 || header[length-3] != 10 ||
            header[length-2] != 13 || header[length-1] != 10) return;
        string first = Encoding.ASCII.GetString(header, 0, length).Split(new[] {"\r\n"}, StringSplitOptions.None)[0];
        bool allowed = first == "GET " + AssetRoute + " HTTP/1.1" || first == "GET " + AssetRoute + " HTTP/1.0";
        byte[] response = Encoding.ASCII.GetBytes(allowed ?
            "HTTP/1.1 200 OK\r\nContent-Type: application/octet-stream\r\nContent-Length: " + payload.Length + "\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n" :
            "HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n");
        stream.Write(response, 0, response.Length);
        if (!allowed) return;
        stream.Write(payload, 0, payload.Length); stream.Flush();
        string row = "{\"utc\":\"" + DateTime.UtcNow.ToString("o") + "\",\"method\":\"GET\",\"path\":\"" + AssetRoute +
            "\",\"bytes\":" + payload.Length + ",\"sha256\":\"" + SHA256 + "\"}\n";
        try { File.AppendAllText(journal, row, new UTF8Encoding(false)); }
        catch (IOException e) { Error = "HTTP journal failed: " + e.Message; return; }
        Interlocked.Increment(ref gets);
    }

    public void Dispose()
    {
        stopping = true; listener.Stop();
        lock (sync) { if (active != null) active.Dispose(); }
        if (!worker.Join(5000)) throw new IOException("Doom HTTP worker closure unconfirmed; retain reservation.");
    }
}
