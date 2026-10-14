# Fixed link/lookup prepatch V3

The actual V2 mapped report (8504 bytes / SHA-256
`dd0d10a895ec9c42c1d4e7c87e812fab527e8ca4650e1aa67154530c64ee47d7`)
contains all 246 bytes of DB_AddXAsset and 30 bytes of Load_SimpleAsset.
Offline decoding shows Load_SimpleAsset passes type in ECX and header value
in RDX, calls DB_AddXAsset and stores the RAX result at return site
0x1401DB2C5. DB_AddXAsset creates a local entry, calls 0x1401D7960 with its
address in RCX and EDX=0, and returns the entry header at offset 8.
This supports the existing hook's argument/return usage; it has not proved
the complete engine ABI, a dependency/provider, or a correction to the fatal.

The source pinned at [BOIII 5aa7fac](https://github.com/Ezz-lol/boiii-free/blob/5aa7fac39c51438d9c1e312b99534b7fef3bff44/src/client/game/symbols/db/load.hpp)
names that exact call target DB_LinkXAssetEntry. Its pinned
[asset symbols](https://github.com/Ezz-lol/boiii-free/blob/5aa7fac39c51438d9c1e312b99534b7fef3bff44/src/client/game/symbols/db/xasset/core.hpp)
name DB_FindXAssetHeader at 0x1401D5FB0 and DB_IsXAssetDefault at
0x1401D7260. Their server-address selection was checked in the same pinned
symbol/ptr sources. Their names are source evidence, not observed call chains.

The next observation is explicitly finite, with three literal rows:

| Site | Site RVA | Bytes before | Window start | Bytes |
| --- | --- | --- | --- | ---: |
| DB_LinkXAssetEntry | 0x1D7960 | 0x2A60 | 0x1D4F00 | 16384 |
| DB_FindXAssetHeader | 0x1D5FB0 | 0 | 0x1D5FB0 | 256 |
| DB_IsXAssetDefault | 0x1D7260 | 0 | 0x1D7260 | 256 |

The main band ends at 0x1D8F00 and covers the nearby database lookup/default
code, reducing successive captures for each discovered helper. The two small
overlapping windows also obtain their own covering .pdata records. Total code
reads are 16896 bytes. There is no address selector, scan or automatic callee
following. Outside these constants, namespace, flag and schema, the V3 helper
is identical to V2. It retains the existing PE/MEM_IMAGE/region guards, exact
reads, 4 MiB cumulative bound, 2 MiB .pdata bound, 256 KiB report bound,
first-DPI capture before post_unpack/hooks, fresh exclusive output and immediate exit.

Profile `t7-prepatch-link-v3` uses sole flag `-t7-prepatch-link-v3`, report
`t7-prepatch-link-v3.local.json` and schema `iw7.t7-prepatch-link-observation/3`.
The build has exactly main Compile and link Link, fourteen profile fields,
and ten exact `ReuseCompile.PrepatchLinkV3` fields under schema
`iw7.t7-prepatch-link-build/3`. V1/V2, catalogue and export mixtures refuse.

Preparation requires `--prepatch-link-v3` and its paired
`--prepatch-link-v3-base-plan`. The only accepted V2 plan is 303783 bytes /
`0aca63cb09e8ecfc96dee34e1fdf94f8cb66e400f8a190ffdefd38bec3a2c549`;
the only imported text is its already wired main (14524 bytes / e719365c...).
The renderer changes its namespace/include to V3. It does not import the old
product tree or alter current material-parts/native CLI rendering. The six
non-main payloads and compiled CLI/xpak retain the same exact C422e/af6
source proofs as V2; the enclosing failed C group keeps its Failed status.

| V3 text | Bytes | SHA-256 |
| --- | ---: | --- |
| Helper | 15827 | cf839e18a68adb4ed3aae82d683ef110ab595fa8c172584e47ca4d11bb8db48d |
| Wiring | 2236 | 66f70ca5a979745288232d76496a339e08d639ddf34560aada6e6b63c5bcffa1 |
| Main | 14469 | 84cde2924df0a0553dd2cddb0ca173aed54af43d6874b06718c01d1a6cec4989 |

Source checks on 2026-10-14: seven V3 source/integration checks and 26 affected
reuse checks passed; 48 V3 PowerShell validation controls and the affected
100 V2 controls passed. No native process, provider or opaque input was used.
The actual worktree DEFAULT passed with 82 bindings (76 text, six binary
metadata), 1083 inputs, no missing pins and five native-type/hash/lease/run-root/
readiness flags false. Initial source checks caught a Python numeric-unit typo
and a missing V3-specific bound for the large immutable base-plan text; both
were corrected before the passing DEFAULT. These are preparation results.

Next: exact source review/private Git workflow, immutable source and fresh
DEFAULT qualification, then separate coordinator main/link and capture GOs.
V2 code, binary f11, report dd0d and closure evidence remain frozen. The
reference/default branch, provider, cause and Zombies catalogue remain unqualified.

## Dated OS preparation checkpoint, 2026-10-14

The original V3 recipe `add72114...` remains immutable and was not executed.
Its historical TZRES input became stale after Windows servicing. PR83 supplies
an explicit dated context, limited to that one resource and the fixed closed
qualification proof. The new preparation reuses the complete source packet at
`a8ecff7cb61323cd0e6f75d10e596d55e63a7753`; later documentation heads do not
change that packet. The V3 helper, wired main, fourteen profile fields, ten
marker fields, retained C compilation and original V2 recipe remain unchanged.

Three operator approaches were refused before real V3 preparation. A lacked
admission and owned child lifecycle. B reused a shared helper whose unknown-exit
branch disposed the original process handle. C retained that owner but marked
creation as uncertain only after the factory call, permitting a throw to leave
cleanup confirmed. The additive D correction marks uncertainty before creation
and retains the actual owner through unknown wait/termination outcomes. Its
five authored cases exercise the actual scoped helper and admission finally:
known exit disposes/releases once; three unknown-owner cases retain the same
owner without disposal/release; unknown creation retains cleanup and the lease.
SourceE/shared helpers remain unchanged. This scoped correction does not
qualify the shared helper's unknown-exit branch.

The separately authorized D Analysis ran on 2026-10-14 at 10:39 UTC. One lease
covered the owned Python maker and actual DEFAULT, each bounded to 60 seconds.
Both returned zero. The original NoExit host and its external launch parent
were recorded before preparation. The actual PTY returned zero, and a fresh
10:40:58 UTC observation found all four owned process IDs absent, no heavy
processes and no leases. These are real preparation/closure results, not CPP.

| Closed text evidence | Bytes | SHA-256 |
| --- | ---: | --- |
| New recipe | 305621 | e484cef7415b2697c188b0202f3771af15377ecb56d98a0a85bfc1d2418fe530 |
| Admission receipt | 2906 | 7e6399bdfbadffb4c1898e31ce15d955171a6c05a3770d18e344d0da997ae779 |
| Independent closure | 609 | 139ef87c16447ffdc0470b5daa54f86f5b636b2fe2115e466d9324eeb9eeb420 |
| Generated CPP wrapper | 3639 | 583b22cc7e33099f4e8e5a1694c99c6fdca99b98d61437a1d8e4eadf82192daf |
| Generated CPP capsule | 5911 | bf3c1c2a6efdd00da29e97f3901df3ac0376462dc1afe072fe9781c2d9ee6110 |

DEFAULT validated 83 bindings (77 text, six opaque metadata), 1083 Inputs,
no missing pins and the exact 14/10/11 profile/marker/OS-context shapes. All five
native-type/binary-hash/lease/run-root/readiness flags stayed false. Comparing
the old and new recipe metadata, with only the source/prepared root routing
normalized, found exactly one changed Input hash: qualified TZRES. The other
1082 Input hashes/sizes and prepared CPP bytes remain unchanged.

The CPP wrapper was generated only from the actual new recipe hash after that
passing DEFAULT. It retains the original dot-sourced runner/context/guards/lease
and keeps the original NoExit host when closure is unknown. It has not been
invoked. Next: review this concrete wrapper/capsule, obtain a separate main/link
CPP slot, then qualify its measured closed outputs before a separate V3 capture
GO. No executable/PDB tuple, capture, provider, failure cause, catalogue or game
acceptance is claimed at this checkpoint.

## Closed main/link compilation, 2026-10-14

The coordinator separately authorized one CPP group against the actual
`e484cef7415b2697c188b0202f3771af15377ecb56d98a0a85bfc1d2418fe530`
recipe and its reviewed original-host wrapper. The unchanged source packet is
still `a8ecff7cb61323cd0e6f75d10e596d55e63a7753`, not a later documentation head.
Only main Compile and link Link ran. Both original compiler roots returned zero;
the group passed in 17,335.8599 ms and finished at 11:23:21 UTC.

Each stage captured its sole VCTIP descendant twice in the original job, with
the expected original compiler as parent. Its scoped stop was followed by
original-root exit zero, ActiveProcesses zero and an empty job member list.
Inputs were reverified under the original reservation. The original host
retained the runner's context/guards/state, then confirmed context closed,
no lease and zero guards. The actual PTY completed with exit zero. A fresh
11:27:16 UTC inventory found the launch parent, original host, two compiler
roots and two VCTIP descendants absent, with no heavy processes or leases.

| Original leased output / closed text | Bytes | SHA-256 |
| --- | ---: | --- |
| EXE | 21777408 | d89c4cf326f21038d9fbcc6a18c18db2c17c17f448400a8567ee2e5fdca6a8bb |
| PDB | 136982528 | d45781dc051dd5ed2fc57c86b093296207c7623b8810df9ecd04f08851a648c3 |
| Build receipt | 17200 | 0cc0c8b6b46fd75d09c53b3e3c3dc9af40aa4211a786629fcf2f791c52111328 |
| Independent closure | 1207 | 6066a2d8ca8f999e23eb1ce7b26167a5a4a8efd43be8915388ba019bf6be439c |
| Six closed text pins index | 2189 | b13107f072b164640a4344d8281df79b5b2f3fc1ee229813764ce7e55159e4c2 |

Artifact tuples above come exclusively from the original leased receipt; no
EXE/PDB or other opaque input was reread or hashed after release. The six-row
index binds Entry, Completion, actual ToolExit, Inventory, Build and Bundle
under `iw7.t7-prepatch-link-v3-closed-pins/3`. It preserves original raw records
and distinguishes observed PTY completion from the host's earlier CanExit.
TreeClosureConfirmed, LeaseReleased and InputsReverified are true;
Quarantined, CandidateExecuted and Ready are false.

This qualifies a closed instrumented build only. No native candidate, FF,
stock or game operation ran. Next: bind the new recipe, OS proof, measured
executable and closed witnesses in a reviewed V3 consumer cohort, then obtain
a separate capture GO. ABI, provider, failure cause, catalogue and gameplay
remain unqualified; old V2 outputs and recipes remain immutable.
