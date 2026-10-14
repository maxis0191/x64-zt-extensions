# Proposed World M4 stock supplement

M3 read the original target's Fatal Error body, without truncation:
`Could not find asset file assetfile17.pak`. The immutable baseline72 contains
only zone/assetfile1.pak. The retained flat dedicated and base client both hold
pack17, with equal metadata but distinct file IDs; content equality between them
has not been established. Reuse the retained dedicated already supplying pack1.

Optional RequiredPak17Binding plus its SHA256 accepts one small metadata receipt
with schema iw7.world-required-pak17/1. It binds the unchanged baseline digest,
reviewed manifest digest9116255e and one fixed zone/assetfile17.pak input from the
same directory/volume as the baseline pack1 source. Its size is104595492 and
its expected SHA256 is6f5c0d1937b5a707d4e1fb3009f68a827714d9e4a72ff2d6570b57dbf6b0f058,
from the immutable reviewed manifest's pack17 row (1166 entries,248142B).
This is a historical expected digest, not a fresh payload hash. Bind current
NTFS ID, UTC timestamp and attributes in the local receipt; do not choose the
base client merely because its size/time match.

The pure supplement validator adds one input to a new World plan only. It reads
no stock and does not mutate the original72, common StockBinding code, FF/rig
recipes, stock attributes or generated packages. Source planning pins the receipt
and validator; all donor identity/content checks stay after the existing single
admission and under the ordinary read guards, before the original tool starts.
Existing rollback now manages75 entries (73inputs plus tool/request); the borrowed
extra file is a hardlink and is removed/restored through the same transaction.
No full game copy, new supervisor, native CPP patch or CP/MP skip is introduced.

zone/ follows the existing pack1 binding and retained source zone-path convention;
the engine's successful pack17 lookup at that alias is still unrun. A fresh
package/plan/operator and separate GO must validate the added dependency. This
does not assume that pack17 is the final missing dependency or that CP material
proof, FF, rendering or physics will pass. The M3 operator remains consumed.
