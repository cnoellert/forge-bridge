# Manual Targeted Authoring

Forge Bridge can author a prompt for one exact downstream generator, pause for
human correction, and submit the approved prompt through the normal generation
grant gate. The target is selected once and persisted with the author plan; the
make command cannot replace it.

## Workflow

1. List invocable targets:

   ```bash
   fbridge author-targets --operator generate_still
   ```

2. Author for one exact target:

   ```bash
   fbridge author "A rain-soaked car crosses an empty bridge" \
     --target-operator generate_still \
     --target-backend higgsfield-cli.nano_banana_2 \
     --json
   ```

   Keep the returned `run_id` and `artifact_id`.

3. Revise until the prompt is acceptable, then approve the final run:

   ```bash
   fbridge qc RUN_ID "Keep the bridge visible behind the car" --json
   fbridge qc REVISED_RUN_ID --approve --actor "$USER" --json
   ```

4. Call the read-only `forge_estimate_generation` MCP tool for the finalized
   target inputs. It returns the peer-declared estimate and a proposed
   `grant_id`. Ratify that exact quote:

   ```bash
   fbridge ratify-generation GRANT_ID --actor "$USER"
   ```

5. Submit the approved prompt. A prompt-only still needs no input payload:

   ```bash
   fbridge author-make APPROVED_AUTHOR_ARTIFACT_ID GRANT_ID --json
   ```

   Image-to-video supplies generic references and scalars without restating the
   target:

   ```bash
   fbridge author-make APPROVED_AUTHOR_ARTIFACT_ID GRANT_ID \
     --inputs-json '{
       "references": [{
         "artifact_id": "approved-still",
         "artifact_type": "image",
         "metadata": {
           "role": "structural",
           "url": "https://cdn.example/approved-still.png"
         }
       }],
       "scalars": {"duration_seconds": 5}
     }' \
     --json
   ```

6. Poll the returned artifact with `forge_generation_status`.

## Authority And Retry Rules

- `author-make` refuses an author artifact that is incomplete or still paused
  for QC.
- The persisted target is authoritative. Input JSON accepts only `references`
  and `scalars`; target overrides are rejected.
- The grant must be ratified and must match the exact operator and backend
  identity. A mismatch does not spend the grant.
- The default idempotency key permits one make per approved author artifact.
  An identical retry returns the existing artifact without another submit or
  grant spend. Use `--idempotency-key` only when the make identity is explicitly
  managed by the caller.

This is the manual single-beat path. It does not authorize autonomous paid
retries, automatic QC decisions, or a storyboard loop. Those remain gated on a
bounded generation-grant design and typed Vision QC contracts.
