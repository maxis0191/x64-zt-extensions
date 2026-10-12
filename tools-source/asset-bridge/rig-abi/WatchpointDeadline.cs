// Source-only addition. Compile/load only in an admitted future native group.
// Borrows the existing BuildJob object; no new job, PID lookup, attach or P/Invoke.
using System;
using System.Reflection;
using System.Threading;

namespace IW7.RigWatch {
public sealed class OriginalJobDeadline {
    readonly object gate = new object();
    readonly object owner;
    readonly MethodInfo stop;
    readonly AutoResetEvent wake = new AutoResetEvent(false);
    readonly Thread thread;
    long due;
    bool requested, closing, attempted, completed;
    long? observed;
    string failure;

    public OriginalJobDeadline(object originalOwner, long absoluteDueMs) {
        if(originalOwner == null || originalOwner.GetType().FullName != "IW7.CommunityBuild.BuildJob")
            throw new ArgumentException("Exact pinned original BuildJob required");
        owner = originalOwner;
        stop = owner.GetType().GetMethod("Stop", Type.EmptyTypes);
        if(stop == null || stop.ReturnType != typeof(void))
            throw new ArgumentException("Pinned Stop API changed");
        long now = Environment.TickCount64;
        if(absoluteDueMs < now - 270000 || absoluteDueMs > now + 240000)
            throw new ArgumentException("Bounded absolute observation deadline required");
        due = absoluteDueMs;
        thread = new Thread(Watch) { IsBackground = true, Name = "Rig original-job deadline" };
        thread.Start();
    }

    public long DueMs { get { lock(gate) return due; } }
    public bool StopAttempted { get { lock(gate) return attempted; } }
    public bool StopCompleted { get { lock(gate) return completed; } }
    public long? StopObservedMs { get { lock(gate) return observed; } }
    public string StopFailure { get { lock(gate) return failure; } }

    public void Tighten(long absoluteDueMs) {
        lock(gate) {
            if(closing || requested || attempted || absoluteDueMs > due)
                throw new InvalidOperationException("Deadline may only tighten before stop");
            due = absoluteDueMs;
            wake.Set();
        }
    }

    public void RequestStop() {
        lock(gate) {
            if(closing) throw new InvalidOperationException("Deadline owner already closed");
            requested = true;
            wake.Set();
        }
    }

    void Watch() {
        try {
            while(true) {
                int wait;
                lock(gate) {
                    if(closing) return;
                    long now = Environment.TickCount64;
                    if(requested || now >= due) {
                        attempted = true;
                        observed = now;
                        break;
                    }
                    wait = (int)Math.Min(due - now, int.MaxValue);
                }
                wake.WaitOne(wait);
            }
            // Stop is invoked once, on the original object and handles. It can
            // stop a suspended debuggee without a debugger prompt or stdin.
            stop.Invoke(owner, null);
            lock(gate) completed = true;
        } catch(Exception error) {
            lock(gate) failure = (error.InnerException ?? error).Message;
        } finally { GC.KeepAlive(owner); }
    }

    public void CloseAfterJobClosed() {
        // Never let a generic Dispose silently disarm protection for a live job.
        bool exited = (bool)owner.GetType().GetProperty("Exited").GetValue(owner);
        uint active = (uint)owner.GetType().GetProperty("Active").GetValue(owner);
        if(!exited || active != 0) throw new InvalidOperationException("Original root exit and Active0 required");
        lock(gate) {
            if(attempted && !completed && failure == null)
                throw new InvalidOperationException("Original Stop call still pending");
            closing = true;
            wake.Set();
        }
        if(!thread.Join(1000)) throw new InvalidOperationException("Deadline thread did not close");
        wake.Dispose();
    }
}
}
