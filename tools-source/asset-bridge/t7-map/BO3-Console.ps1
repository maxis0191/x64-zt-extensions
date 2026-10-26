param([int]$ProcessId,[string]$Command,[int]$Tail=1500)
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices; using System.Collections.Generic;
public static class BC {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr p, EnumProc f, IntPtr l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern int GetWindowLong(IntPtr h, int i);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, string l);
  [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, StringBuilder l);
  public static IntPtr[] Edits(uint pid){ IntPtr input=IntPtr.Zero, output=IntPtr.Zero;
    EnumWindows((h,l)=>{uint p; GetWindowThreadProcessId(h,out p); var c=new StringBuilder(64); GetClassName(h,c,64);
      if(p==pid && c.ToString()=="BOIII WinConsole"){ EnumChildWindows(h,(ch,l2)=>{var c2=new StringBuilder(64);GetClassName(ch,c2,64); if(c2.ToString()=="Edit"){ if((GetWindowLong(ch,-16)&0x4)!=0) output=ch; else input=ch;} return true;},IntPtr.Zero);} return true;},IntPtr.Zero);
    return new IntPtr[]{input,output}; }
}
"@
$e=[BC]::Edits([uint32]$ProcessId)
if($e[0] -eq [IntPtr]::Zero){throw 'BOIII console input not found'}
if($Command){ [void][BC]::SendMessage($e[0],0x000C,[IntPtr]::Zero,$Command); [void][BC]::SendMessage($e[0],0x0102,[IntPtr]13,[IntPtr]::Zero); Start-Sleep -Milliseconds 1500 }
$sb=New-Object Text.StringBuilder 262144; [void][BC]::SendMessage($e[1],0x000D,[IntPtr]262144,$sb); $t=$sb.ToString(); $t.Substring([Math]::Max(0,$t.Length-$Tail))
