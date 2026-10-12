# SDK resource tools: Plan F preparation, not executed

The [failed Build E](BUILD-E-RESULT.md) is preserved separately in `532f9e8`.
Its two actual C++ probes pass, but its final link reports LNK1158 because the
declared PATH omits the installed SDK resource compiler. No ZoneTool candidate
exists. This correction prepares a future build only.

The existing Windows SDK 10.0.26100.0 x64 bin directory contains:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `rc.exe` | 55640 | `43da1503c262c30894c851589bf0155f8365d77e63a5f7bc13982320e3a6b42d` |
| `rcdll.dll` | 264536 | `9a11e4759adc48abe1fa9e3082ad7db4b53f4d6d77701c13729f4ffd47ae934c` |

These 320176 bytes are not members of Seal C. Plan F declares exactly these two
`sdk_tools` and also binds each as one ordinary bootstrap `source_pins` entry.
The existing entry opens their read guards before hashing or importing code and
retains them until safe completion, or in its existing AppDomain quarantine.
No new guard owner, scheduler, closure provider or copy of SDK tooling is added.
The worker verifies their lengths and hashes at startup and immediately before
and after the final link. SDK version, architecture, file name, size and digest
are fixed. Missing/duplicate/unbound tools and overlap with the old seal fail.

The exact native PATH is now, in order: the existing pinned MSVC x64 bin directory,
the installed `Windows Kits/10/bin/10.0.26100.0/x64`, and Windows System32. Both
PowerShell and Python reject an omitted SDK directory, an extra directory or
changed order. The declared environment still clears implicit compiler/linker
options and inherits no personal PATH. No SDK reinstall, directory copy, manifest
suppression or warning-policy change is involved. No SDK executable has been run
to prepare or test this source correction.

The fresh native output would be `runtime/zt-sound-md5-d`; it remains absent.
The unchanged response revision helper produces twelve new response files under
`runtime/content-surfaces/original-sound-checksum-build-review-c`. Compared with
the executed E responses, their only byte changes relocate the private output
from `zt-sound-md5-c` to `zt-sound-md5-d`. Compiler and linker flags, resource input,
the patched include overlay, library inputs and all warning settings are unchanged.
The responses total 81758 bytes. Their 11026-byte revision manifest SHA-256 is
`def849210423dd56bbb798f222328fb879d1d18b957c3e54f279bdfb7d0904e3`.

The existing ignored `original-sound-checksum-build-plan-a` directory contains:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `build-plan-f.local.json` | 37761 | `91280092489387e909516693d4234c60ea0416657166cf6bd8674bd974729c3a` |
| `build-command-f.local.ps1` | 1083 | `cd5639e41cb7124fc4fb99c9eaed4711472566653501db911ec350e695b2da94` |

Plan F has 42 bootstrap source pins, including the twelve revised responses and
two new SDK tools. The original 1410 guarded Seal C inputs, six qualified providers,
fourteen native stages, 4/6 GiB admission, 512/768 MiB output bounds, one-hour
observed deadline and unchanged two-second original-job drain remain in force.
The host command must run only after a separate coordinator GO in a fresh
PowerShell 7 `-NoLogo -NoProfile -NoExit` host. As before, a live host must retain
uncertain closure/quarantine and can exit only after closure/release checks.
This is a complete future build, not a link-only retry using partial E outputs.

Source verification passed: fifteen Python tests, including four new SDK cases;
fourteen PowerShell SDK contract cases; seven response contract cases; and the
default Plan in both PowerShell and Python. The entry guard fixture proved
seventeen denied writes through parse/output and nine files writable after return,
including small private copies of both SDK binary inputs. It never requests write
access to installed SDK files. These checks create no native candidate, load no
job types and request no reservation. They establish binding and guard behavior;
they do not establish that the future link will succeed.

The E Plan and failed final state still have their recorded hashes. All failed
outputs remain intact. Integration, independent review and the next native slot
belong to the coordinator. No new build, SAB/FF execution, playback or readiness
claim is authorized by this document.
