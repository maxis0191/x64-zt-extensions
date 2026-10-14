# Proposed M3: read the original target's modal text

M2 captured a retail MessageBoxW wait but did not recover its caption/body.
The new explicit `-LoadDiagnostic -ModalTextOnly` mode reuses M2's original H1
target, one Extract admission, 72 stock inputs, 120-second global phase and
restoration. It keeps the 45-to-60-second global_mp stall trigger. It runs one
ten-second owned Python helper; no new CPU sample, dump or CDB operation occurs.
The old packages, plans, captures and consumed M2 operator remain immutable.

The helper reuses `recipient_dialog.py` Win32Reader primitives without changing
that recipient module. Its full FatalDialogProbe cannot be reused: it expects
Python to create the target and accepts only a Fatal Error caption. Here the
original target is created by H1 in PS7, and M2 did not reveal the caption.
The adapter accepts the first #32770 window owned by that exact original target.

The caller first checks its live original job's PID/image/creation identity.
The helper retains its own read-only process handle, checks the same image/hash
and exact 100ns creation FILETIME, and checks that target/helper parent PIDs match
the original caller. It verifies process identity, HWND process ownership and
child relationship before/after reads. Caption/class changes or failed identity
checks discard text attribution. It does not claim an independent job-membership
query or an atomic UI snapshot. No process/window mutation or click is requested.

GetWindowText reads the caption; cross-process Static controls use only
WM_GETTEXT through existing SendMessageTimeoutW, with 200 ms and
SMTO_ABORTIFHUNG|SMTO_ERRORONEXIT, without broadcast or NOTIMEOUTIFNOTHUNG.
Primary API references: [GetWindowTextW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowtextw),
[SendMessageTimeoutW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendmessagetimeoutw),
[GetWindowThreadProcessId](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowthreadprocessid).

Existing enumeration is bounded to 256 top-level callbacks/eight target windows;
only one dialog, eight controls and 16 KiB UTF-8 text are selected. The record is
at most 64 KiB, created once under the owned runtime. A two-second soft control
budget is not a hard capture deadline; the ten-second original helper deadline
and combined closure reserve remain authoritative. Saturation, timeout and
missing text remain explicit. No observed modal in the bounded selection is a
negative result, not successful body recovery, and does not trigger another run.

Authored source fixtures cover identity/parent/FILETIME, reassignment, nonfatal
captions, negative scans, timeout/truncation and one-helper dispatch. They load
no Win32 DLL, stock, native owner or actual window. Real enumeration/text,
cleanup and any dependency diagnosis are unrun until a fresh reviewed package,
plan, NoExit capsule and coordinated GO. CP material proof and writer/FF remain
gated; no zone skip or gameplay is part of this proposal.
