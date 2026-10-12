# Reusable feature proof prompts

Adapt these to the target checkout's current UI, real hooks, assets and data.
Use the existing runner and regression owners. Replace bracketed values before
running; a prompt template is not evidence.

## Token availability

"On [app URL], verify [exact asset/network] is [available/unavailable] in both
the deposit and withdrawal selectors under [actual edge-config state]. Record
an assertion for each selector. Exercise the UI without submitting a transaction.
Report each behavior separately if one route needs authentication."

## Metadata-driven UI, including Earn metrics when present

"Open [feature/entity] on [app URL]. Verify [required fields, such as APY and
TVL] render the expected values from [current provider response]. Record each
field assertion after loading finishes, and check the relevant loading/error
behavior. Keep the journey read-only."

## Quote identity

Inspect the UI and fixture's actual authentication/balance requirements. Getting
a read-only quote does not itself require settlement permission or holdings.

"For [user action] and [exact source/destination asset variants], obtain a quote
through the current UI. Assert the accepted quote's source, destination and amount
against the owning module contract and visible selection. Record the assertions
and finish without signing."

Before execution, list the requested behaviors and the proof layer for each.
After execution, map every required behavior to an actual assertion/evidence
path or a failed/blocked result. Login readiness proves login readiness; keep
feature assertions explicit. Account preflight applies to the journey that needs
it, while independent metadata, public UI and module checks can still run.
