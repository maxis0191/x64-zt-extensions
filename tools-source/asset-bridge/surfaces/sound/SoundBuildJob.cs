// Small Windows build owner: suspended creation, original handles, kill-on-close job.
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;
namespace IW7.SoundFFTelemetryV1 {
public sealed class BuildJob : IDisposable {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] struct Startup {
        public int cb; public string reserved, desktop, title;
        public uint x,y,cx,cy,charsX,charsY,fill,flags; public ushort show,reserved2;
        public IntPtr reservedPtr,input,output,error;
    }
    [StructLayout(LayoutKind.Sequential)] struct ProcessInfo { public IntPtr process,thread; public uint pid,tid; }
    [StructLayout(LayoutKind.Sequential)] struct BasicLimits {
        public long processTime,jobTime; public uint flags;
        public UIntPtr minWorking,maxWorking; public uint activeLimit;
        public UIntPtr affinity; public uint priority,scheduling;
    }
    [StructLayout(LayoutKind.Sequential)] struct IoCounters { public ulong a,b,c,d,e,f; }
    [StructLayout(LayoutKind.Sequential)] struct ExtendedLimits {
        public BasicLimits basic; public IoCounters io; public UIntPtr processMemory,jobMemory,peakProcess,peakJob;
    }
    [StructLayout(LayoutKind.Sequential)] struct Accounting {
        public long user,kernel,periodUser,periodKernel; public uint faults,total,active,terminated;
    }
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern IntPtr CreateJobObject(IntPtr attributes, string name);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool SetInformationJobObject(IntPtr job,int cls,ref ExtendedLimits info,int size);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool QueryInformationJobObject(IntPtr job,int cls,out Accounting info,int size,IntPtr returned);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool QueryInformationJobObject(IntPtr job,int cls,out ExtendedLimits info,int size,out uint returned);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern bool CreateProcess(string app,StringBuilder cmd,IntPtr pa,IntPtr ta,bool inherit,uint flags,IntPtr env,string cwd,ref Startup si,out ProcessInfo pi);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr job,IntPtr process);
    [DllImport("kernel32.dll", SetLastError=true)] static extern uint ResumeThread(IntPtr thread);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool TerminateJobObject(IntPtr job,uint code);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool TerminateProcess(IntPtr process,uint code);
    [DllImport("kernel32.dll", SetLastError=true)] static extern uint WaitForSingleObject(IntPtr handle,uint ms);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool GetExitCodeProcess(IntPtr process,out uint code);
    [DllImport("kernel32.dll", SetLastError=true)] static extern uint GetPriorityClass(IntPtr process);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern bool QueryFullProcessImageName(IntPtr process,uint flags,StringBuilder path,ref int size);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool GetProcessTimes(IntPtr process,out long created,out long exited,out long kernel,out long user);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
    IntPtr job,process,thread;
    public uint PID { get; private set; }
    public string Image { get { var path=new StringBuilder(32768);int size=path.Capacity; if(!QueryFullProcessImageName(process,0,path,ref size)) Fail();return path.ToString(); } }
    public string CreatedUtc { get { long created,exited,kernel,user; if(!GetProcessTimes(process,out created,out exited,out kernel,out user)) Fail();return DateTime.FromFileTimeUtc(created).ToString("o"); } }
    public uint Priority { get { return GetPriorityClass(process); } }
    public bool Exited { get { var value=WaitForSingleObject(process,0); if(value==0xffffffff) Fail(); return value==0; } }
    public uint ExitCode { get { uint value; if(!Exited || !GetExitCodeProcess(process,out value)) throw new InvalidOperationException("Original process has no exit"); return value; } }
    public uint Active { get { Accounting info; if(!QueryInformationJobObject(job,1,out info,Marshal.SizeOf(typeof(Accounting)),IntPtr.Zero)) Fail(); return info.active; } }
    // Class 9: JOBOBJECT_EXTENDED_LIMIT_INFORMATION.PeakJobMemoryUsed.
    // Query only our original handle; NULL would query the caller's job instead.
    public ulong PeakJobCommitBytes { get {
        if(job==IntPtr.Zero) throw new ObjectDisposedException("BuildJob");
        ExtendedLimits info; uint returned; int size=Marshal.SizeOf(typeof(ExtendedLimits));
        if(!QueryInformationJobObject(job,9,out info,size,out returned)) Fail();
        if(returned!=(uint)size) throw new InvalidOperationException("Incomplete job memory information");
        return info.peakJob.ToUInt64();
    } }
    static void Fail() { throw new Win32Exception(Marshal.GetLastWin32Error()); }
    private BuildJob() {}
    public static BuildJob Prepare(string application,string arguments,string cwd) {
        var owner=new BuildJob();
        try {
            owner.job=CreateJobObject(IntPtr.Zero,null); if(owner.job==IntPtr.Zero) Fail();
            var limits=new ExtendedLimits(); limits.basic.flags=0x2000; // KILL_ON_JOB_CLOSE; no breakaway.
            if(!SetInformationJobObject(owner.job,9,ref limits,Marshal.SizeOf(typeof(ExtendedLimits)))) Fail();
            var si=new Startup(); si.cb=Marshal.SizeOf(typeof(Startup)); ProcessInfo pi;
            if(!CreateProcess(application,new StringBuilder("\""+application+"\" "+arguments),IntPtr.Zero,IntPtr.Zero,false,
                0x08000000|0x00004000|0x4,IntPtr.Zero,cwd,ref si,out pi)) Fail(); // NO_WINDOW, BELOW_NORMAL, SUSPENDED
            owner.process=pi.process;owner.thread=pi.thread;owner.PID=pi.pid;
            if(!AssignProcessToJobObject(owner.job,owner.process)) Fail();
            if(owner.Priority!=0x4000) throw new InvalidOperationException("BelowNormal priority required");
            return owner;
        } catch {
            if(owner.process!=IntPtr.Zero) { TerminateProcess(owner.process,121); WaitForSingleObject(owner.process,10000); }
            owner.Dispose(); throw;
        }
    }
    public void Resume() {
        if(thread==IntPtr.Zero) throw new InvalidOperationException("Already resumed");
        if(ResumeThread(thread)!=1) Fail(); CloseHandle(thread);thread=IntPtr.Zero;
    }
    public void Stop() { if(!TerminateJobObject(job,122)) Fail(); }
    public void Dispose() {
        if(job!=IntPtr.Zero) { CloseHandle(job);job=IntPtr.Zero; }
        if(thread!=IntPtr.Zero) { CloseHandle(thread);thread=IntPtr.Zero; }
        if(process!=IntPtr.Zero) { CloseHandle(process);process=IntPtr.Zero; }
    }
}
}
