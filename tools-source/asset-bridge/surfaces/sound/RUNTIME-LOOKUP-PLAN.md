# Original sound: next runtime evidence, source proposal only

Prepared after the successful `NativeDumpOnlyC` codec checkpoint on 2026-10-12.
This document authorizes no build, asset read, staging, game, recorder or playback.
The existing FF/SABL/SABS, dump and codec results remain immutable. The coordinator
owns shared/native helper changes and any later exact-source execution decision.

## Established evidence and the missing lookup

| Evidence | What it establishes | What it does not establish |
| --- | --- | --- |
| F `verify_zone` | The engine-backed ZoneTool load reaches the soundbank and branding rawfile callbacks. | Successful lookup of an alias through its index, bank sample delivery or playback. |
| F/C alias CSV dump | The bank contains the expected single alias/head and all 53 exported values. | The serialized `aliasIndex` is correct: CSV export iterates alias lists. |
| Independent SAB reader | Exact entry ID, bounds, seek/frame bytes, CRCs, payload/source MD5 and original PCM for this one loaded sample. | IW7 opening this bank through its runtime file path. |
| C dump plus strict FFmpeg | The native dump recovers the exact original PCM and WAV. | Client mixer output, physical audibility or general FLAC conformance. |

In the reviewed ZoneTool source, `iw7/zonetool.cpp:402-405` only logs each asset
while `globals.verify` is set; `verify_zone` at line 756 calls `load_zone` and
waits. `sound_bank::write` writes both alias arrays and `aliasIndex`, but the
dump/reader does not expose the latter. For this one-entry bank the expected
index is value 0, next 65535; that expectation is not observed runtime evidence.

The original fixture is deliberately tiny:

- Bank `community_original_sound_v1.all`, zone `sdk_original_sound_v1`.
- Alias `community_original_chime_v1`, ID 1489483025; one head, asset ID 1496246593.
- Loaded, nonlooping, precached; `scn_fx_unres_2d`, interface volume modifier,
  volume 0.5 and pitch 1; no secondary/stop alias or duck.
- F FF: 544 bytes, SHA256 `13e878aeec2c545d5e6c8c02a6b75eb6061fd1bec14c9199450ef6a45e135900`.
- F SABL: 114816 bytes, SHA256 `e0ce851bc7264a03d06e6ca2a44d15d424f1f4c01957ab0dda915879ca4d0110`.
- F SABS: 4096 bytes, SHA256 `e490efefe70da393fd7830102637f3e0df12f6b6b0945e8c54cada2a6fef3b6f`.

`checksumChecksum` remains the writer's sixteen `0xCC` bytes. Matching that
placeholder is not verification of its engine meaning. Do not repair, zero,
bypass validation or regenerate the bank speculatively. A later successful
runtime test would establish acceptance of these exact bytes in that scenario,
not the checksum algorithm or universal compatibility.

## Prefer the standard package; retain a separate diagnostic route

Aurora `party.cpp:86-90` advertises only `mod.ff`, `mod.sabl` and `mod.sabs`.
The bank still carries zone `sdk_original_sound_v1`; the writer's `create_path`
uses this zone for SAB filenames. Merely renaming all three files to `mod.*`
does not establish that the engine requests or finds the samples.

| Route | Internal bank zone / delivered names | Useful proof | Remaining limit |
| --- | --- | --- | --- |
| Recommended standard mod | Build a new `mod` zone; bank JSON `zone` is `mod`; deliver `mods/sdk_original_sound_v1/mod.ff`, `mod.sabl`, `mod.sabs`. | Exercises Aurora's intended three-file mod lookup/download path. | Requires a separately reviewed new package build and actual three-file delivery/engine evidence. |
| Local diagnostic using F | Keep bank zone `sdk_original_sound_v1`; stage F FF as `mod.ff` and original named SABs under `iw7-mod/zone`. | Can isolate engine lookup/sample use with the exact preserved F bytes. | Local fallback only; never FastDL compatibility or a distributable package qualification. |

For the recommended route, reuse the qualified C ZoneTool executable, original
WAV/FLAC/alias bytes and unique bank/alias names. The only intended source changes
are bank JSON `zone: "mod"` and the zone CSV basename `zone_source/mod.csv` with
its same one soundbank row. The external package ID stays `sdk_original_sound_v1`;
it does not have to equal the engine's standard `mod` zone. No new audio encoding,
native compiler rebuild or donor asset is required by this source design.

Create that source variant and its manifest only after the next source decision,
in a fresh output distinct from F. The existing closed source/reader/FF contracts
currently fix `ZONE` to `sdk_original_sound_v1`; add an explicit bounded mod-package
case rather than silently changing the meaning of historical receipts or accepting
arbitrary zone names. A future separately approved native invocation can use C's
existing build/verify/dump route for `mod`, with the same transaction, output
bounds and independent bank readback. Require `mod` in the new bank header and
the exact original alias/sample/PCM. Capture new FF/SAB hashes: they are unknown
now and must never be copied from F's receipt. Existing C compilation and the
historical codec proof do not need speculative reruns.

The common SDK already describes optional `mod.sabl`/`mod.sabs` client entries,
and `Package-CommunityMod.py` uses the existing manifest's client destinations
for `fastdl/`. Use that package/compatibility workflow; no second package format.
Its source transport support is not a measured sound delivery claim. For the
first standard runtime case, serve exactly the three new pinned routes from the
existing bounded loopback HTTP helper after a small reviewed three-asset extension.
Today `HudHttp.cs` accepts one FF and fixed HUD/model/beacon routes; it must not
be described as already supporting sound. Keep the current bounds/GET journal,
no directory serving or arbitrary paths. Snapshot/restore the base mod directory,
start it without these cached files, and require three actual GET/hash/cache
receipts before attributing playback to community package delivery. This is local
FastDL evidence; WAN/other-client acceptance remains separate.
Package metadata must retain the current blocked/runtime-unverified sound
capability status. Valid transport entries must not invent a demonstrated custom
sound capability or claim that matching protocol alone proves compatibility.

The optional source-supported local diagnostic route preserves F bytes: stage
the FF as `mods/sdk_original_sound_v1/mod.ff`, and the original named banks as
`iw7-mod/zone/sdk_original_sound_v1.sabl` and `.sabs`, on the candidate and the
base client. `fastfiles.cpp:109-151` first tries the engine file open, treats
`mod.*` specially, then falls back to `filesystem::find_file("zone/" + basename)`;
`filesystem.cpp:68-69` registers cdata and `iw7-mod`. This is a route to test,
not demonstrated delivery. Refuse pre-existing conflicting files and account
for search-path precedence. An observed open failure must preserve the requested
basename and diagnostics; do not silently rename or mutate the qualified bank.

This optional pre-staging keeps a diagnostic independent of HTTP. It is not the
recommended community-package acceptance path and does not qualify FastDL.
Use the existing base/candidate transaction machinery for the exact three files,
their prior existence and restoration. Do not borrow the model/HUD FF allowlist
or claim that its FF-only HTTP helper already transports sound banks.

## The lookup must be observed in the client

There is no ready-made Release client lookup command in the inspected
source. `dedicated.cpp:243-265` registers `generateSoundLookupData` only under
`_DEBUG`; it enumerates all banks and writes a map JSON. On a dedicated server,
`snd_lookup_sound_length_stub` instead consults `sounddata`, while sound streaming
is patched out. A dedicated `soundexists`/duration log must not be promoted to
proof that the client traversed this FF's alias index and opened its sample.
Do not inject a fake positive duration into `sounddata`.

## Smallest concrete implementation proposal

Reuse `ops/Agent-Lab.ps1`, `Base-Client.Core.ps1`, the existing private/protected
agent session and `Agent-Scenario.Core.ps1`. Add one narrowly scoped sound case
to that lifecycle; do not create a second general lab runner. The current
`actions/aim/combat/model/vertical` modes cannot simply be passed a sound FF.
The current native mailbox also rejects unknown actions; an arbitrary console
command is not a supported shortcut.

The minimum separate client-lookup witness needs a small extension to the existing
native test fixture, followed by its own later reviewed build. This proposal
does not perform that build or assert that the existing package contains it:

1. Bind a single diagnostic to the existing isolated/test flags, exact client
   session nonce and fresh protection generation; require CP Spaceland, private
   candidate identity and `sv_cheats=0`. Dispatch on the existing main scheduler.
   Use the newer session/sequence/deadline contract, not only the old PID mailbox.
2. Find the literal bank with `DB_FindXAssetHeader(..., allowCreateDefault=0)`;
   reject a missing/default bank. Check bounded names, the selected receipt's
   exact zone (`mod` for the standard package), language, alias count
   1, head count 1 and nonnull arrays before dereferencing. Read only its single
   `SndIndexEntry`, require value 0 / next 65535, then compare alias/head IDs,
   file name and loaded/nonlooping flags against the closed fixture contract.
3. Separately call the engine's original sound-length lookup for the literal
   alias. The inspected existing hook gives the source reference/signature
   `int(const char*)` at `0x140C9BCE0`; bind it to the exact reviewed IW7 native
   package before use, rather than treating this address as portable. Require
   a plausible result for the 1000 ms sample; preserve the actual value.
   Report this engine call independently from our explicit index traversal.
4. Emit one bounded client record with PID/session/generation/native tick,
   bank/alias/asset identities, index entries and lookup duration. No generic
   name, pointer, engine-call or command execution interface is needed.
5. A small dedicated fixture borrows the existing quiet arena, fresh
   `paris_test_protect`, heartbeat and `paris_agent_observationstamp` pattern.
   After the host accepts the fresh client lookup record, one ordinary Use
   action triggers one literal `player playsound("community_original_chime_v1")`.
   Log before/after the call with the same run identity; no loop or retry.
   A compile/runtime error or lost protection stops the case. A request log
   alone is still not audio output. Inspect any dedicated `soundexists` result
   as separate server evidence; do not let a duration JSON stand in for the
   client lookup or manufacture a positive server result.

Shared/native changes belong to the coordinator/native owner. Sound ownership
can supply the closed fixture contract, observation parser and marker scoring
under this directory after the proposal is selected. Do not edit the shared
recorder/provider or Test-Platform speculatively.

## One base client and the retained dedicated

Resolve the durable candidate described by current `docs/STORAGE-WORKFLOW.md`
(`Documents/IW7-Runtime/doom-server`) and the existing base installation. Recheck
them before a future Run; no historical managed-worktree path is launch authority.
Use one reduced client, no clone, no extra enemy and no second receiver. Keep
Main on 27016 outside all staging. Preserve an occupied owner client.

Borrow Agent-Lab's scoped executable/profile/server/bank transactions, fresh
native privacy observation, `g_password`, launch/config `sv_lanOnly`, heartbeat
suppression, protected join and 500 ms action freshness. Source-only Plan must
read bounded receipts and metadata; defer every executable/audio/FF/SAB read and
hash until the complete runtime lease and retained guards. Do not call existing
model/HUD payload-reading preparers just to obtain a Plan.

Lookup alone uses the existing reduced one-client estimate: 12 GiB RAM / 12 GiB
commit with debugger disabled (4 GiB dedicated plus 8 GiB client). This is a
future estimate, not a fresh admission measurement or a reservation.

For playback, reuse the original-owner recorder APIs in
`ops/voice-agent/Recorder.Core.ps1` and `Resource-RecorderOwnedProcess.Core.ps1`,
with `tests/native/audio_output_probe.cpp --record`. They already capture only
the target process tree, register before resume, retain exact kernel/image/file
identities, prove producer closure and preserve the host/lease on unknown cleanup.
The old `Record-Receiver.ps1` standalone launcher is not a replacement for this
current admission/ownership chain.

Both current recorder gates require **exact Runtime 20/20 GiB**, even though
the actual recorder target can be one client. The smallest change-free recorder
reuse therefore keeps this conservative whole-case reservation and starts only
the dedicated, one client and one recorder. Do not create a second client just
to match the helper's historical name. If 20/20 cannot be admitted, stop before
launch; a reviewed explicit one-client recorder budget would be a separate
shared-source decision. Do not silently lower or bypass either gate. One combined
lookup-then-play case can reuse this 20/20 lease if the later GO covers both phases.

## Distinguish the call from measured output

Start the existing recorder only after protected stable join and successful
client lookup. Require its fresh `WASAPI recording ready` PID/creation/tick
before the one Use event. A bounded 8-second capture allows at least two seconds
of pre-event baseline, the one-second marker and post-event decay. Continue
protection/identity monitoring while it records; no microphone, physical input
route, endpoint switch or device-wide fallback is required.
The target must be the sole synthetic test client in the passworded server;
cancel on another join. Do not enable voice relay, fake microphone capture, PTT
or speech fixtures. Process-tree output capture excludes unrelated apps; keep
human conversations out of the target process and never substitute system-wide
capture. The recorder does not open a microphone.

The original source code defines three faded triangle pulses: 500 Hz at
0.05-0.20 s, 750 Hz at 0.30-0.50 s and 1000 Hz at 0.60-0.90 s. After original
recorder closure, analyze its retained stereo 48 kHz PCM in-process under the
same lease. Compare baseline versus the event's bounded lag window, frequency
order and pulse envelope; account for stereo gain/mixing. Pin scoring thresholds
before execution using synthetic quiet/noisy/wrong-frequency/shifted controls.
Do not tune a threshold after hearing/seeing the real capture or require the
mixed output to have the original mono PCM hash.

Report separately: `FFLoaded`, `ClientAliasIndexObserved`,
`ClientEngineLookupObserved`, `SoundRequestIssued`, `ProcessOutputMarkerMeasured`,
`PhysicalAudibilityAccepted` and `Ready`. Only independent process audio matching
can qualify measured output. A positive lookup, successful script call, nonzero
RMS or active audio session alone cannot. Physical listening and broader maps,
languages, remote delivery and owner acceptance remain separate.

Close the recorder first through its original owner, analyze/revalidate while
guards and lease remain, stop only the owned client, require the existing valid
empty-server 30-second guard, restore exact base/candidate files and bank, then
release. Retain original host/ownership on any uncertain closure/restoration.
Save an independent host/process absence witness before reporting the case done.

## Source review basis

This preparation read source/text only and launched no game, recorder, codec or
build. Main policy reference read at `origin/main` f47d8423. Inspected local
IW7-Mod source HEAD was `77e6d4d24e918ee363b3feee3735c3b889dff7d7`; relevant actual
source bytes, not an inferred executable identity:

| Source under `src/client/component` | SHA256 |
| --- | --- |
| `dedicated.cpp` | `ca5a974599848cba36334f77d3738dd26cef3bffeb30ef313ead1274f70b6b1d` |
| `fastfiles.cpp` | `69a05cbbea77cb04ade74ea34c4dd8df6bf8ddf774921aa2921897e93cc1f336` |
| `party.cpp` | `09c38a053839cf6fc84aa7ac2ea8cdfd6a72b408be8cbc4e077796e2cc0e2447` |
| `filesystem.cpp` | `bb983d2d3c0c2e24242a1a86cc22b4a8ff4cb14cfd3f7846fbc358563a36f509` |
| `paris_test_fixture.cpp` | `54d662ff18fce319fc18f87ed11e715e4fa81cbb0895b40b16c0f657472d0a76` |

No runtime-ready command or binary package is claimed by this proposal. The next
action is source review of this limited case and assignment of the shared/native
extension, then exact-source tests and a separately qualified build/Run decision.
Before that decision, pure tests should reject wrong bank zone/name, default or
missing bank, bad/looping/out-of-range index, wrong IDs/head counts, stale session
or protection, foreign/missing HTTP routes, payload/hash drift, duplicate Use,
recorder not ready and positive audio scoring from baseline/wrong marker alone.
These are future checks for the proposed implementation, not tests run here.
