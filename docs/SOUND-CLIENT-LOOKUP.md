# Original sound: protected client lookup

Status on 2026-10-12: source implementation reviewed and applied locally;
**not compiled or run**. This diagnostic neither requests playback nor records
audio. Source review, native compilation, client execution, measured audio and
owner acceptance remain separate evidence.

## Entry and scope

`src/native/paris_test_fixture.cpp` observes the fixed original-sound bank after
the existing client scenario accepts `arm`. It runs on the fixture's existing
main-thread scheduler. There is no new console command, GSC token, mailbox action,
wire field, timer or arbitrary asset-name/address interface.

The helper requires a Release client, both `paris-server-client-test` and
`paris-isolated-lab`, preferred image base `0x140000000`, exact
`fs_game=mods/sdk_original_sound_v1`, active initialized CP on `cp_zmb`, no local
server, and the current bound loopback connection/challenge. The remote port must
equal `paris_lab_server_port` in 27100..27999; `sv_cheats` stays 0. The request's
PID, nonce, sequence and step must match the accepted scenario. The existing
protected heartbeat must be at most 500 ms old before observation, immediately
before the length call, and at completion.

Server protection/privacy remains in the existing fixture: dedicated test flag,
CP, LAN-only, nonempty password, bound player identity/endpoint, engine godmode and
inactivity protection. The future host runner must retain the private-instance
checks and correlate the existing fresh native observation stamp to its owned
server PID, client nonce, server generation and slot 0 for the sole-client case.
This source addition does not relax any of those gates.

There is one attempt per bound client nonce/server generation/connection challenge,
including missing or malformed banks. Another arm on that same connection does
not retry the observation. An exception before the latch is committed is incomplete
evidence; it is not a successful engine call.

## Loading and the two distinct observations

Before sending arm, the future Lookup runner must establish the exact protected,
playable mod session and verify delivery/cache evidence for all three standard
files under the complete runtime lease. Save the client log offset before arm.
The current `Loading zone` log is emitted before the original load call, so it
cannot serve as a completion fence. Disk existence and current-fastfile names
also do not prove completion.

The helper makes a closed observation of this one bank:

- `DB_FindXAssetHeader(SOUND_BANK, "community_original_sound_v1.all", 0)` must
  return a non-default asset with zone `mod` and both languages `all`.
- An identified bank with `aliasCount=0` establishes absence only in that bank.
  Otherwise require exactly one alias and one index entry, value 0 / next 65535.
  Never follow `next` or traverse a variable count/index.
- The single alias list/head must name `community_original_chime_v1`, alias ID
  1489483025, asset `community/original_chime_v1`, asset ID 1496246593, one head,
  loaded, nonlooping and precached.
- Separately call the original engine length entry with that literal alias.

Manual verification of the bank/index/head is **not** proof of an internal
alias-pointer resolver. No such function was attested in the inspected source.
A non-default identified bank proves that bank is visible in the client DB at
observation time; it does not prove all assets in the FF finished loading.

## Bounded snapshots and remaining native limits

All added engine-data snapshots use `ReadProcessMemory(GetCurrentProcess(), ...)`.
`VirtualQuery` first checks the fixed span lies in one committed readable region
without guard/noaccess. The API must return success **and** the copied byte count
must equal the requested size before any destination byte is interpreted.

Copies are fixed-size: bank 352 bytes, index 4, alias list 32, head 200, dvar 96,
client UI state 196, port string 6. Literal strings use at most 64 bytes including
the terminator and are compared only from local arrays. A failed or short string
copy produces its owning `bank_unreadable`, `alias_unreadable` or
`head_unreadable` status. An unreadable scope snapshot refuses that gate.

VirtualQuery is a prefilter, not a lifetime lock. Complete copies do not make
multiple observations atomic or rule out stale/inconsistent values. The existing
module-owned C++ party connection remains under the main-thread fixture ownership
rules. Neither the snapshot path nor `catch(std::exception)` protects the engine
DB/length calls against access violations or establishes their ABI safety. A
future qualified execution still needs owned-process crash and closure evidence.

## Original length entry and result contract

Pinned IW7-Mod upstream `77e6d4d24e918ee363b3feee3735c3b889dff7d7`,
`src/client/component/dedicated.cpp`, supplies `int(const char*)` and the original
entry `0x140C9BCE0` (RVA `0xC9BCE0`). In the inspected source the non-dedicated
client hook is inside `_DEBUG`, followed by an early return; the dedicated hook
occurs later. Thus the reviewed Release client path calls the original entry,
not the dedicated JSON length substitute. Executable memory protection is checked
but no checksum guess, prologue pattern or runtime-byte attestation is claimed.

The raw integer's units are not established by that caller. Preserve zero,
negative and positive values without interpreting zero as alias absence or
asserting a millisecond match to the separate 1000 ms PCM source.

One `[Paris sound lookup]` record carries PID, nonce, generation, sequence, step,
probe/begin/end ticks, final protection, status, bank identity flags, alias state,
index value/next and the separate `engine_length_called` / `engine_length_raw`.
Every record has `playback_verified=0`.

| Status | Evidence and limit |
| --- | --- |
| `bank_not_observed_load_unproven` / `default_bank_load_unproven` | Load unproven; alias and length unmeasured. Never early-load absence. |
| `alias_absent_in_observed_bank` | Count 0 in the identified non-default bank only; engine not called. |
| Snapshot/identity/count/index/head failure | Stop at that check; later evidence remains unmeasured. |
| `resolved_zero_length` / `resolved_negative_length` / `resolved_positive_length` | Manual table check passed and original call returned the reported raw value. No resolver, PCM or playback proof. |
| `protection_expired`, incomplete exception record, or no record | Reject qualified evidence, even if a raw value was retained. |

The future host parser must require one new complete record after its saved log
offset, exact active owned-session identity, ordered ticks, end minus probe at
most 500 ms and `protected_end=1`. An `armed` ACK alone is not lookup evidence.
Keep manual alias-index observation and original engine response as separate
results. The source addition does not implement or authorize that future SDK Run.

## Build integration and provenance

`ops/Build-Voice.ps1` already copies and inventories the fixture, applies its
existing isolated transformation and builds Release x64. The native-package
provider already includes the fixture in exact source checks. A future client
package must be rebuilt and qualified against the changed source before use;
the previous binary cannot supply this diagnostic. No provider inventory edit is
needed. StandardMod asset construction with the separately qualified C tool is
independent of this client executable change.

The source-only preview applied here was revision 2, SHA256
`7dec4f037bf384bd90ae9ef326191a863c2b1632e9cccbee18a3cbc2d0afb533`, against fixture
SHA256 `78e5e09a1f4c589113e05e1523aeb6f5b928fea23d55f428e226d5e8d253149d`.
Independent review found the revision-1 VirtualQuery/direct-copy race; revision 2
replaced those copies with the checked snapshot path. The coordinator reported
that P2 closed with no new P1/P2 before authorizing local application.

Ignored preview provenance retains **30 passing Python decision-model tests** and
the superseded revision 1. Those tests describe acceptance/rejection decisions;
they do not execute this C++, ReadProcessMemory, native layouts or engine calls.
No copy of the model is added as a C++ test. The patch passed `git apply --check`;
compilation, native execution, runtime protection and actual audio remain untested.

This work performs no build, Run, admission or resource polling. The Lookup
estimate remains 12/12 GiB and both recorder gates remain 20/20 GiB. Any later
execution needs its distinct coordinator decision and full existing lifecycle.
Main UDP 27016 and occupied owner clients remain outside this diagnostic scope.
