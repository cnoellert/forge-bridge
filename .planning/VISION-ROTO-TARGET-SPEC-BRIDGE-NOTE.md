# Vision Roto Target Spec — Bridge Note (#60)

Bridge composition for the greenscreen→roto demo now routes an explicit
chain-authored `target_spec` into `forge_roto_ref` alongside `clip_ref`.
The target is NL/markup owned by the authored chain, not inferred from
`is_greenscreen`.

SEAM-1 is closed: `forge_is_greenscreen` takes the plate-reading signature the
bridge needed (`shot_id` + `clip_ref`). The demo no longer carries synthetic
`frame_stats`; detection routing is clip-ref driven.

Binding ruling: bridge passes `clip_ref` + `target_spec` through to the
vision sibling tool. Bridge does not author, reinterpret, or inspect the
matte; it only carries the request and checks the returned wire envelope.
This is consistent with the #52 ruling that bridge passes `clip_ref`.

Verdict bar: the demo accepts either a well-formed artifact reference
(`artifact_refs[0].artifact_type == "DerivedHoldoutsArtifact"`, a non-empty
`payload_id`, and a `locator` ending in `.exr`) or a structured honest
abstention with a named reason and no locator. The `mock://` path is the safe
fast path used by the bridge harness; real plate SAM2/ViTMatte remains an
operator-coordinated heavy round-trip.

Vision internals live in forge-vision at `f42441c`. Do not mirror that pipeline
description here; this note records only the bridge-side wire and verdict.
