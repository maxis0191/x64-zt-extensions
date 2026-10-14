# Proposed M5: one global_cp modal snapshot

M4 qualified/borrowed pack17 and progressed past global_mp, then timed out at
global_cp after 240 seconds. Its cause remains unknown; no next pack is inferred.
Keep the same strict 73-input supplement and 75-entry rollback, with the original
72-input baseline unchanged. The new opt-in DiagnosticZone global_cp requires
LoadDiagnostic, ModalTextOnly and the reviewed pack17 binding. Existing default
global_mp behavior remains unchanged; other zone names are refused.

This reuses the reviewed M3 Win32 reader and original H1 caller, not another
supervisor or pipeline. The one-shot trigger uses only the exact final
global_cp log line, 45 to 60 seconds elapsed and 15 seconds without log progress.
Its global phase is 120 seconds with 10-second closure reserve. It runs one owned
helper for at most 10 seconds, using the same 200 ms WM_GETTEXT and identity/HWND/
child checks. No CPU capture, dump, CDB or new window interaction is added.

An owned modal caption/body, missing body, timeout or truncation stays explicit.
No owned modal in the bounded scan remains NoModalWindowObserved; do not turn
it into a successful cause or material proof. Combined unknown closure retains
the original NoExit host/guards/admission. Normal known closure performs the
existing source/stock proof, alias restoration and release. No file/data name
from the earlier M3 message is assumed to explain the CP wait.

Pure source fixtures cover MP/CP separation, one helper, original identity,
negative windows and missing opt-ins before file/native access. Actual capture
is unrun until a new reviewed merged-source tuple and separate coordinated GO.
No identical M4 replay, other pack, client Game, writer/FF or physics acceptance
is part of this diagnostic proposal. Old plans/packages/captures remain intact.
