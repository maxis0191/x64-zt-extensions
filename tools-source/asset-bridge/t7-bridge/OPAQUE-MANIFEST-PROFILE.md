# Optional opaque startup manifest observation

`EngineOutputProfile: ObservedStartupManifestA` is a separate opt-in catalogue
profile. `ObservedStartupA` keeps its original empty identity-directory policy.
Existing plans, output budgets, runtime deadlines and admission estimates do not
change. A newly prepared plan still needs its own review and explicit runtime GO.

The new profile permits one optional ordinary file at exactly
`work/identities/dedicatedpc/LPC/.manifest`. Its producer and format are unknown.
The profile never reads, hashes, decodes or exports its contents. Observing this
file does not establish engine compatibility or a successful catalogue.

During progress observations, the file may contain zero through eight bytes.
Its native file identity is recorded in memory for that attempt and must remain
unchanged. Redirections, reparse ancestry, a directory in its place, another
identity entry or more than eight bytes are refused. If an already observed file
disappears, validation also fails. A file never produced is allowed to stay absent.

At final validation, native closure and the still-held admission context are
required. A present file must be exactly eight bytes. A read/share-read handle
freezes its length and identity and remains in the existing context's guards
until cleanup; no byte read is needed. The identity is compared both with the
earlier observation and after opening that handle. A replaced file cannot pass
merely because its name and size match. Final absence cannot later become presence.

The file contributes one entry and its actual length to the existing output
counter. The 64-entry ceiling and total/mutable/receipt byte limits stay intact.
No extra directory, alternate path, private identity key, copy fallback, retry or
silent upgrade of an old plan is allowed. Failed historical receipts remain failed.

`Test-T7CatalogueOpaqueManifest.ps1` uses original tiny temporary fixtures and the
existing filesystem identity helper. It covers unchanged legacy refusal, optional
absence, growth, exact final length, retained sharing guards and cleanup, file
replacement and disappearance, an injected replacement race, a real synthetic
junction, unrelated paths, admission/context refusals and exact entry accounting.
It neither opens game stock nor starts an engine or acquires a resource lease.
