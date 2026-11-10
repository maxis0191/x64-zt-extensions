# Fixed-route sound HTTP transport

The original sound package requires three client downloads: `mod.ff`, `mod.sabl`
and `mod.sabs`. The previous `IW7HudHttp` instance could serve only one file.
The helper now has one dedicated constructor for the three immutable arrays,
their three expected SHA-256 hashes and a fresh journal path. It continues to use
one loopback listener and one worker. There is no directory server, second HTTP
implementation or new package format.

| Fixed route | Maximum bytes |
| --- | ---: |
| `/mods/sdk_original_sound_v1/mod.ff` | 1600 |
| `/mods/sdk_original_sound_v1/mod.sabl` | 131072 |
| `/mods/sdk_original_sound_v1/mod.sabs` | 4096 |

All inputs must be nonempty, bounded, cloned and hash-verified before journal or
listener creation. These are fixture ceilings, not measured artifact sizes.
The new standard package's exact sizes/hashes are still unavailable in this
transport checkpoint; do not reuse historical package hashes or enlarge caps
automatically. The intended internal bank zone remains `mod`.

The two historical constructors retain their original four-route whitelist.
HUD/model still allow at most 1600 bytes; beacon/self-contained beacon allow
1 MiB. A historical instance cannot serve a sound route, and a sound instance
cannot serve historical routes. `AssetRoute` and `SHA256` continue to identify
the primary FF; they are not whole-package evidence.

Only exact raw GET request lines using HTTP/1.0 or HTTP/1.1 are accepted. The
existing 404 response, header parser, loopback binding, 64-attempt budget, socket
timeouts and worker disposal are preserved. Every completed journal row binds
the selected file's route, byte count and SHA-256. `CompletedGets` counts rows
across all files, including retries; a failed journal append does not increment it.

## Synthetic validation — 2026-10-12 19:18 UTC

Base commit: `41ff82050471e6909d9d75ced2c6923b085e0b81`.
Actual compiled HTTP source SHA-256:
`caf1c4729f6f1b38b5a3a928648bde5448f631ffac86c94cbde0c9057e80eac5`.

Six targeted Python/PowerShell tests pass. Each fixture compiles the real C#
helper with Add-Type, uses only synthetic arrays and local ephemeral loopback
sockets, disposes its clients/service, checks worker closure and exits its child
PowerShell process. No game, native build, real package/audio/FF/SAB read, native
executable hash or public network download is part of these tests.

The five tests selected from `tests/ops/hud_lab_test.py` are:

- `test_inprocess_http_exact_bytes_routes_budget_and_blocked_reader_disposal`
- `test_inprocess_beacon_http_exact_route_bytes_and_independent_size_limits`
- `test_sound_http_validates_all_inputs_before_side_effects_and_keeps_legacy_routes`
- `test_sound_http_three_immutable_assets_raw_get_routes_and_per_file_journal`
- `test_sound_http_journal_failure_request_budget_and_partial_read_closure`

The sixth is `ModelSourceTests.test_model_http_exact_route_and_cache_scope` from
`tests/ops/model_lab_test.py`. The existing CI workflow already invokes both test
files; no workflow or Agent-Lab/SDK/staging source changes were needed. This
checkpoint records local validation, not an executed exact-head CI result.

Coverage includes null/empty/oversized input and wrong hash at each of the three
positions before journal creation, exact-size bounds, immutable clones of all
three inputs, both HTTP versions, out-of-order requests and an FF retry. The
sound instance serves seven verified synthetic bodies: FF three times, SABL twice,
SABS twice. Each row's hash/size/path and timestamp is checked after closure.
Fifty-one raw noncanonical/method/foreign-route requests return an empty 404 and
add no successful journal rows. Separate fixtures verify failed journal append,
the exact 64-attempt exhaustion error and disposal during a partial request.

The first version of the negative-request fixture failed its explicit 51-case
cardinality guard before sending that matrix: PowerShell concatenation/comma
precedence grouped expressions incorrectly. Parenthesized path expressions and
individual interpolated request strings corrected the fixture. The C# source
did not change; the corrected full six-test selection passes. Preserve this as
a test-authoring failure, not an HTTP transport failure. `git diff --check` passes.

## Integration and acceptance still pending

The Agent-Lab parameters and lifecycle integration remain an ignored preview.
No runtime sound mode or package deployment is introduced here. The integration
owner must bind reviewed standard package metadata, admission and existing
profile transactions before reading payloads or starting a real client.

A future cold-cache witness must prove absence before launch and then a matching
actual GET, byte count/hash and cache file for each of the three distinct routes.
Three FF retries cannot stand in for missing SAB downloads. Preserve retry counts,
require clean HTTP closure and restore exact owned cache/profile state before
release. The HTTP journal does not measure requester PID; keep that unmeasured
unless independent evidence supplies it.

Synthetic HTTP success does not prove engine downloads, FF load, alias lookup,
sound playback, physical audibility, WAN compatibility or owner acceptance.
Keep those states separate and keep `Ready=false`. The next step is coordinator
integration of this scoped commit and exact-head review/CI, followed by the
separately qualified package and Agent-Lab work.
