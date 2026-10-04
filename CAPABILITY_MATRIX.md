# Capability / limitation matrix — geometric V0, engine 0.3.0

| Capability | V0 | Limit |
| --- | --- | --- |
| Unit normalization | YES | mm/cm/m; exact decimal strings or integers; ambiguous single thousands groups refused |
| Rectangle containment | YES | One positioned item inside a rectangular 2D envelope |
| Rectangle intersection | YES | Item vs explicit reservations; edge contact is not overlap |
| Explicit clearance | YES | Global directional full-face sweep; no circulation certification |
| 0/90/180/270 rotation | YES | Bounding-box dimensions swap; no automatic positioning |
| Source conflict detection | YES | All records for the same semantic field considered |
| UNKNOWN/INFERRED blocking | YES | Admission never upgrades their geometric status |
| Recomputed unit derivation | YES | Conversion lineage only, no arbitrary formulas |
| Immutable admitted snapshot | YES | Process-local opaque receipt and copied canonical payload |
| Raw model JSON admission | NO | Always requires separate host capability |
| Source authentication | NO | Host must verify real confirmation/source outside model channel |
| User authentication | NO | No login or identity infrastructure |
| Domain stale receipt rejection | YES | Same live LifecycleRegistry shared by hosts; new revision/revocation invalidates previous receipts |
| Admission traceability | YES | Authoritative receipt/event/snapshot metadata; process-local IDs only |
| Persistent/global revocation | NO | Registry memory only; independent domains/processes do not share revocation |
| Deterministic evaluation | YES | Same request, receipt, version and current admission state |
| Physical measurement accuracy validation | NO | Calculates over admitted supplied facts |
| Photo measurement | NO | No image processing |
| Automatic scale inference | NO | No pixel-to-length conversion |
| Layout optimization | NO | No position search |
| Furniture shrinking | NO | Dimensions never modified to pass |
| ABNT certification | NO | No normative engine |
| Accessibility certification | NO | No compliance or route certification |
| Structural analysis | NO | No structural model |
| Automatic repair | NO | No proposal alteration |
| Full room planning | NO | No layout generator |
| Height/3D compatibility | NO | 2D footprint only, including niche examples |
| Delivery and assembly fit | NO | No transport or assembly path |
| Operating-door swing inference | NO | User/host supplies explicit rectangular reservation |
| LLM status control | NO | Engine/formatter decide the authoritative result |
| Arbitrary-code sandbox | NO | Host must isolate untrusted execution |
| Network / third-party runtime dependencies | NO | Python standard library |
| Filesystem required by library API | NO | CLI examples/tests use local files |
| Persistent storage / database | NO | Transient trust bookkeeping only |
| Platform-specific adapter | NO | Not implemented |
