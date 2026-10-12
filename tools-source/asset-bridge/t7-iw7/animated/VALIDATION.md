# Animated T7 source qualification — 2026-10-12

Base: private project `origin/main` at
`645fb8a823fcf1001c696b11f9cc549ce30ba25d`.
Branch: `codex/t7-animated-contract`, existing T7 worktree reused.
All changes belong to `tools-source/asset-bridge/t7-iw7/animated/`.
Retained native source: `fab935826c898806855376662a8a03317b3ad8f1`.

## Completed local checks

Python 3.12, standard library only; original fixtures generated in memory.

| Check | Result | Evidence boundary |
| --- | --- | --- |
| `python -m unittest discover -s tools-source/asset-bridge/t7-iw7/animated -p 'test_*.py' -v` | 16 tests passed | Includes 64 influence-class permutations, literal independent blend bytes, independent original bind/weight-hypothesis oracle, explicit malformed/overflow/channel refusals. No C++ execution. |
| `python tools-source/asset-bridge/t7-iw7/animated/demonstrate_losses.py` | Completed, expected refusal codes | Original `[2,1,2]` order-loss example; four correctly sized arrays with count 65536; extra byte channel and startup notification. Reports runtime/native/ready false. |
| `python -m unittest discover -s tools-source/asset-bridge/t7-iw7 -p test_readback.py -v` | 31 tests passed | Existing static T7 reader regression; no donor assets read. |
| `python -m unittest discover -s tools-source/asset-bridge/animation/rig -p test_rig_chain.py -v` | 18 tests passed | Existing original-fixture rig chain; both model offset 272 and surface offset 88 remain refused. |
| `git apply --check` for each proposed patch in the retained native source tree | Exit 0 each | Read-only applicability check, not compilation or application. |
| Native source `git diff --stat` for the five pinned files | Empty | No shared converter changes by this work. Source-byte hashes recorded in `source-contract.json`. |

Total: **65 Python tests passed**. The fixtures contain no copied retail bytes,
player identifiers, credentials or raw runtime logs. The tests use only local
source and original in-memory/temporary fixture data. No clone, cache, tool
installation, asset extraction, native build, admission or runtime operation
was part of this work. The previous catalogue activity is a separate task and
is not claimed as animation-conversion evidence.

## Review findings and limits

- The current weight reorder is conditional on an unsorted input. Retained T7
  source search does not establish a mandatory ordering invariant or any real
  donor occurrence. The patch is proposed from a reproducible original case.
- Every vertex attribute and all triangle corners move together in the
  permutation proof. Unknown flags, rigid/collision lists, streamed storage and
  discarded part-bit data are outside its supported scope.
- Four uint16 counter conversions and ten uint8 bone-category conversions have
  explicit pre-cast refusals in the proposed native guard. A refused conversion
  cannot reach the proposed dump wrapper unchecked.
- The native proposals are deliberately separate review artifacts, unapplied
  and uncompiled. Their decoded Python preflight is not connected to native
  pointer reads. Neither patch is a complete converter safety/semantics fix.
- Skeleton position stride (12-byte declaration versus 16-byte comment),
  engine stored-weight direction, complete clip key schedules, material binding
  and real animation playback remain unverified. These limitations are explicit
  in the README and successful component reports.

## Handoff / remaining work

The coordinating chat owns independent review, private PR, exact-head CI and
merge. This branch's local commit is a source handoff, not a completed GitHub
merge or deployment. It does not alter the rigid profile or authorize native
export/engine load.

Next: assign the two native proposals for review; resolve and bound actual
source buffers, hierarchy/position stride, and clip prefix/schedule semantics
before a separate admitted native fixture/donor validation. Real donor evidence
must identify the donor and show vertex/weight association and animation output;
synthetic success alone cannot satisfy that gate.
