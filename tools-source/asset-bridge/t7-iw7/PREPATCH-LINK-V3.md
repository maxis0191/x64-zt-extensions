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
