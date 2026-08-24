# AI Arbitration Escrow

An Intelligent Contract on [GenLayer](https://genlayer.com) that resolves disputes between two parties in an agreement (e.g. a freelancer and a client) using AI-powered consensus instead of a centralized arbitrator.

## Why this exists

Freelance and service agreements often break down over "was the work actually delivered as agreed?" disputes. Centralized platforms resolve this with a human support team; this contract resolves it with independent AI validators who examine live web evidence from both sides and reach consensus on a verdict — transparently, on-chain, and without a single party controlling the outcome.

## How it works

1. **`create_deal(freelancer, description, amount)`** — the client opens an agreement, describing the work and the agreed amount.
2. **`release_funds(deal_id)`** — if there's no dispute, the client simply releases the deal as fulfilled.
3. If there's a disagreement:
   - **`submit_client_evidence(deal_id, evidence_url, claim)`** — the client states their claim and links to supporting evidence (e.g. a message thread, a broken deliverable).
   - **`submit_freelancer_evidence(deal_id, evidence_url, claim)`** — the freelancer does the same (e.g. a link to the delivered work).
   - **`resolve_dispute(deal_id)`** — the contract fetches both evidence pages live, and an LLM arbitrator judges, based only on that evidence, whether the work was genuinely delivered. Validators reach consensus on the verdict via GenLayer's comparative Equivalence Principle before it's written on-chain.

## Deal state machine

```
FUNDED
  ├─ no dispute → RELEASED_TO_FREELANCER
  └─ dispute raised, both sides submit evidence
       └─ resolve_dispute() → RESOLVED_FOR_CLIENT | RESOLVED_FOR_FREELANCER
```

## Design notes

- **State design**: each deal is a self-contained record (client, freelancer, description, amount, status, evidence, resolution reasoning), stored append-friendly in a `DynArray`, with clear, explicit status transitions.
- **Consensus**: dispute resolution uses `gl.eq_principle.prompt_comparative` — validators must agree on the `winner` field, not just each independently guess. This is a meaningfully different problem from a simple "AI says yes/no" wrapper: the LLM is asked to weigh two competing, evidenced claims against each other.
- **Reusability**: this is meant as a primitive. Any two-party agreement contract that needs dispute resolution (marketplaces, service agreements, bounty platforms) can extend or call into this pattern instead of re-implementing arbitration logic from scratch.
- **Known limitation**: like other GenLayer contracts that fetch live web content, evidence pages that are heavy client-side single-page apps (SPA) may not render their real content before the fetch completes, which can affect the arbitrator's judgment. Prefer evidence hosted on static or server-rendered pages where possible.
- **Value custody**: this contract manages agreement *state* and *dispute logic*. The `amount` field records the agreed amount for reference; actual fund custody/transfer depends on how value transfer is wired up at the network/application level.

## Example flow

```python
# Client opens a deal
create_deal(freelancer="0xFreelancerAddress...", description="Landing page redesign", amount=500)

# No dispute — client is happy
release_funds(deal_id=0)

# --- OR, if there's a disagreement ---

# Client disputes
submit_client_evidence(deal_id=0, evidence_url="https://...", claim="The delivered page is missing the pricing section")

# Freelancer responds
submit_freelancer_evidence(deal_id=0, evidence_url="https://...", claim="The pricing section is live at this URL")

# Anyone triggers resolution — validators fetch both pages and reach consensus
resolve_dispute(deal_id=0)

# Check the outcome
get_deal(deal_id=0)
```

## Deployed on GenLayer Bradbury Testnet

- Contract address: `TODO — add after deployment`
- Deployment transaction: `TODO — add after deployment`

## Related project

See also [ai-notary-genlayer](https://github.com/MIKI4222/ai-notary-genlayer), a simpler GenLayer contract that verifies whether a claim is supported by live web content — the evidence-verification pattern used here builds on that idea.
