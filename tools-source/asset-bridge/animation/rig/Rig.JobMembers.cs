// Read-only observations of the ORIGINAL pinned BuildJob; owns no job or process.
// Derived from reviewed Material V2 b08fc1e; source-bound local observer.
// Loaded only inside the separately admitted rig native group, never in Plan.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32.SafeHandles;

namespace IW7.AnimationRig {
public sealed class Member {
    public uint PID;
    public bool? InOriginalJob;
    public string Image, CreatedUtc, Error, ParentError;
    public uint? ParentPID;
}
public sealed class Observation {
    public string CapturedUtc;
    public uint AssignedCount, ListedCount;
    public Member[] Members;
}
public static class JobMembers {
    const int Capacity = 64;
    [StructLayout(LayoutKind.Sequential)] struct BasicProcess {
        public int exitStatus; public IntPtr peb; public UIntPtr affinity;
        public int priority; public UIntPtr pid, parent;
    }
    [UnmanagedFunctionPointer(CallingConvention.Winapi)]
    delegate int QueryBasic(IntPtr process, int kind, out BasicProcess value, uint length, out uint returned);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool QueryInformationJobObject(IntPtr job, int kind, IntPtr value, uint length, out uint returned);
    [DllImport("kernel32.dll", SetLastError=true)] static extern SafeProcessHandle OpenProcess(uint access, bool inherit, uint pid);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool IsProcessInJob(SafeProcessHandle process, IntPtr job, out bool member);
    [DllImport("kernel32.dll", SetLastError=true)] static extern uint GetProcessId(SafeProcessHandle process);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool GetProcessTimes(SafeProcessHandle process, out long created, out long exited, out long kernel, out long user);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, ExactSpelling=true, SetLastError=true)] static extern bool QueryFullProcessImageNameW(SafeProcessHandle process, uint flags, StringBuilder path, ref uint size);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, ExactSpelling=true)] static extern IntPtr GetModuleHandleW(string name);
    [DllImport("kernel32.dll", CharSet=CharSet.Ansi, ExactSpelling=true)] static extern IntPtr GetProcAddress(IntPtr module, string name);
    static void Check(bool ok) { if(!ok) throw new Win32Exception(Marshal.GetLastWin32Error()); }
    static IntPtr BorrowOriginalJob(object owner) {
        if(owner == null || owner.GetType().FullName != "IW7.CommunityBuild.BuildJob")
            throw new InvalidOperationException("Exact source-bound BuildJob required");
        var field = owner.GetType().GetField("job", BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.DeclaredOnly);
        if(field == null || field.FieldType != typeof(IntPtr)) throw new InvalidOperationException("Pinned job field layout changed");
        var job = (IntPtr)field.GetValue(owner);
        if(job == IntPtr.Zero || job == new IntPtr(-1)) throw new InvalidOperationException("Live original job handle required");
        return job; // borrowed synchronously; never close, duplicate, replace or mutate it
    }
    static QueryBasic OptionalParentQuery() {
        var module = GetModuleHandleW("ntdll.dll"); // borrowed loaded system module
        if(module == IntPtr.Zero) return null;
        var address = GetProcAddress(module, "NtQueryInformationProcess");
        return address == IntPtr.Zero ? null : Marshal.GetDelegateForFunctionPointer<QueryBasic>(address);
    }
    static Member ReadMember(uint pid, IntPtr job, QueryBasic parentQuery) {
        var item = new Member { PID=pid };
        // QUERY_LIMITED_INFORMATION only: no terminate, VM-read/write or debug access.
        using(var process = OpenProcess(0x1000, false, pid)) {
            if(process.IsInvalid) { item.Error="OpenProcess: " + Marshal.GetLastWin32Error(); return item; }
            try {
                if(GetProcessId(process) != pid) throw new InvalidOperationException("Opened process id differs");
                bool member; Check(IsProcessInJob(process, job, out member)); item.InOriginalJob=member;
                if(!member) { item.Error="Listed PID no longer belongs to original job"; return item; }
                long created, exited, kernel, user; Check(GetProcessTimes(process, out created, out exited, out kernel, out user));
                item.CreatedUtc=DateTime.FromFileTimeUtc(created).ToString("o");
                var image=new StringBuilder(32768); uint size=(uint)image.Capacity;
                Check(QueryFullProcessImageNameW(process, 0, image, ref size)); item.Image=image.ToString();
                if(parentQuery == null) item.ParentError="NtQueryInformationProcess unavailable";
                else {
                    BasicProcess basic; uint returned;
                    int status=parentQuery(process.DangerousGetHandle(), 0, out basic, 48, out returned);
                    if(status != 0 || returned != 48 || basic.pid.ToUInt64() != pid || basic.parent.ToUInt64() > uint.MaxValue)
                        item.ParentError="Basic process query status/layout: " + status + "/" + returned;
                    else item.ParentPID=(uint)basic.parent.ToUInt64();
                }
            } catch(Exception error) { item.Error=error.Message; }
        }
        return item;
    }
    public static Observation Capture(object owner) {
        if(IntPtr.Size != 8 || Marshal.SizeOf<BasicProcess>() != 48) throw new InvalidOperationException("Windows x64 diagnostic ABI required");
        IntPtr job=BorrowOriginalJob(owner);
        int bytes=8 + Capacity*IntPtr.Size;
        IntPtr buffer=Marshal.AllocHGlobal(bytes);
        try {
            uint returned; Check(QueryInformationJobObject(job, 3, buffer, (uint)bytes, out returned));
            uint assigned=unchecked((uint)Marshal.ReadInt32(buffer, 0)), listed=unchecked((uint)Marshal.ReadInt32(buffer, 4));
            if(assigned > Capacity || listed > Capacity || listed != assigned || returned < 8 + listed*8 || returned > bytes)
                throw new InvalidOperationException("Complete bounded original-job PID list required");
            var result=new Observation { CapturedUtc=DateTime.UtcNow.ToString("o"), AssignedCount=assigned, ListedCount=listed };
            var members=new List<Member>(); var seen=new HashSet<uint>(); var query=OptionalParentQuery();
            for(int index=0; index<listed; index++) {
                ulong value=unchecked((ulong)Marshal.ReadInt64(buffer, 8+index*8));
                if(value == 0 || value > uint.MaxValue || !seen.Add((uint)value)) throw new InvalidOperationException("Invalid or duplicate job PID");
                members.Add(ReadMember((uint)value, job, query));
            }
            result.Members=members.ToArray();
            GC.KeepAlive(owner);
            return result;
        } finally { Marshal.FreeHGlobal(buffer); }
    }
}
}
