# Registration material bindings: closed metadata consumer

`registration_bindings_consumer.py` consumes only
`iw7.t7-registration-material-bindings/1`, profile
`t7-registration-material-bindings-v1`, native source
`fab935826c898806855376662a8a03317b3ad8f1`. It observes the original MODEL
registration for `p7_fre_platform_cap_02`, LOD0/material0. It does not import
retail image definitions or authorize a different native operation.

The distinct input has exactly 41 outer keys, nine keys per binding row and the
existing ten-key owned snapshot. It reuses `incoming_image_consumer.snapshot`
and `selected_image_request.validate_copied_image_metadata` for the existing
copied-image DTO. No duplicate image parser, selector, serializer, extraction
or capture pipeline is introduced. The original incoming, F2, registration33
and selected-image APIs remain unchanged.

## Inputs and diagnostic distinctions

Up to seven rows form the exact ordered prefix 0..6. Successful enumeration
requires all seven and the final registered MODEL/material/table recheck. The
row's copied hash is uint32 and **usage_u16** is uint16, with 65535 preserved;
neither is constrained to the old lead4/hashA0AB1041. The preliminary uint8 idea
was corrected from the pinned native source before a compiled/runtime candidate.
The old `usage_u8` key is not accepted in this report schema.

Each row retains its scalar hexadecimal registration chain, image-field presence,
owned raw name or NULL, leading-comma boolean or NULL, binding recheck and raw
snapshot. Hex values are recorded numbers; the consumer never casts/dereferences
them or treats numeric agreement as object/lifetime proof. Aliased names/image
fields and repeated hashes/usages are allowed metadata. A leading comma labels
a reference name; ordinary spelling is not evidence of a complete definition.
Any completed copy or copy fault must imply the producer's nonnull, eight-byte
aligned image-field gate and `address <= UINT64_MAX - 264`. Null, misaligned or
overflowing fields remain valid refusal diagnostics
when no copy/fault occurred. Peer Source review found the missing prerequisite in
the initial consumer; its corrective commit retains both causal negatives and the
positive misaligned pre-copy refusal. This is arithmetic on recorded metadata,
not native pointer access, ABI qualification or memory admission.
A second Source review found the omitted span-overflow prerequisite. Boundary
tests retain `fffffffffffffef0` as the last permitted aligned copy start and refuse
`fffffffffffffef8` and `fffffffffffffff8` for both complete copies and copy faults;
the same extreme values remain valid diagnostics before any copy/fault.

Snapshots require the same two complete 264-byte copies and internal header/name
rechecks when observed. A refused row retains its reason and NULL image/name;
it does not stop subsequent rows. Even seven refused image snapshots can belong
to a complete original enumeration and a successful native exit. The consumer
preserves both the per-row results and the separate global window classification.
Published zero scalar/part values are not a claim that all 264 raw bytes are zero.
Nonzero scalars likewise do not qualify a descriptor or payload.

The full header-copy cap is 3696 bytes, with at most 14 complete copies. Complete
published-copy totals must sum exactly. Any partial copy fault, or a structural
failure after an attempted registration, keeps the aggregate byte total NULL,
including a structural failure with zero completed copies. A genuinely unattempted
capture has ordinal0, no rows/chain and zero known copies/bytes. An incomplete
prefix is not seven fabricated absent images. The original callback search limit
is1024 with one unprobed refusal trigger at1025; match/duplicate accounting remains
separate from row results.

Owned names remain exact UTF-8, at most255 bytes, without NUL or C0 bytes below
0x20 under this profile. Quotation marks, backslashes and non-ASCII characters
are not normalized. `model_default` remains NULL: this new producer makes no
DB lookup or IsDefault call. The declared metadata-read bound is64KiB; it does
not report an invented actual read-byte count. The existing ordinary JSON input
guard stays32KiB; no global cap is raised. It rejects duplicate JSON fields,
nonfinite values, opaque suffixes, ADS/device paths, reparse inputs and oversized
or changing files using the existing `read_report` and `strict_json` helpers.

## API and outcomes

```python
consume(report) -> dict
classify(report, original_native_exit) -> dict
```

```text
python -B -S registration_bindings_consumer.py closed.json --native-exit-code 0
```

| Original window / native exit | Outcome |
| --- | --- |
| Complete enumeration /0 | RegistrationBindingsObserved |
| Complete enumeration /nonzero | ValidRegistrationBindingsFromFailedProcess |
| Globally refused /nonzero | RegistrationBindingsRefused |
| Globally refused /0 | Contradiction, ValueError |

Only explicit Python API `classify(None, exit)` represents `NoReport`. An existing
JSON null, malformed report or wrong schema is an error, not report absence.
The output schema is `iw7.t7-registration-bindings-consumer/1`. It retains a
detached copy of the complete observation and bounded per-row summaries without
choosing an image. Descriptor, source/model/renderer association, object/pointer
identity, allocation, atomicity, ABI, lifetime, pixels and Ready remain false;
qualified object mip count remains NULL and payload bytes remain zero.

This Source consumer and its authored fixtures do not qualify the producer's
C++ fixture, a compiled CLI, a native observation, FF, DDS or rendering. A future
real report must retain its own exact native inputs/exit/closure evidence.
