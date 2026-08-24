# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
from genlayer import *


class ArbitrationEscrow(gl.Contract):
    """
    AI Arbitration Escrow

    A dispute-resolution primitive for two-party agreements (e.g. a
    freelancer and a client). Instead of relying on a centralized platform
    or a manual arbitrator, disputes are resolved by AI validators who
    independently examine each side's evidence (fetched live from the web)
    and reach consensus on a verdict via the Equivalence Principle.

    Deal lifecycle (state machine):
        FUNDED
          -> (no dispute) -> RELEASED_TO_FREELANCER
          -> (dispute raised, counter-evidence submitted)
             -> RESOLVED_FOR_CLIENT
             -> RESOLVED_FOR_FREELANCER

    Design notes:
    - This contract manages agreement state and dispute resolution logic.
      Actual value custody (holding real funds) depends on how value
      transfer is wired up at the network/application level; the `amount`
      field here records the agreed amount for reference and downstream
      integration, not an enforced token lock.
    - Evidence is a URL + a short claim describing what that URL should
      demonstrate (e.g. a delivered page, a message thread, a commit).
      The LLM verifies each claim against the live page content, the same
      pattern used in AI Notary, then compares both sides to decide who
      the evidence supports more strongly.
    - Reusable as a primitive: any two-party agreement contract needing
      dispute resolution can wrap or extend this instead of re-implementing
      arbitration logic from scratch.
    """

    deals: DynArray[str]

    def __init__(self):
        pass

    @gl.public.write
    def create_deal(self, freelancer: str, description: str, amount: int) -> None:
        assert len(freelancer) > 0, "Freelancer address cannot be empty"
        assert len(description) > 0, "Description cannot be empty"
        assert amount >= 0, "Amount cannot be negative"

        deal = {
            "id": len(self.deals),
            "client": str(gl.message.sender_address),
            "freelancer": freelancer,
            "description": description,
            "amount": amount,
            "status": "FUNDED",
            "client_evidence_url": "",
            "client_claim": "",
            "freelancer_evidence_url": "",
            "freelancer_claim": "",
            "resolution_reasoning": "",
        }
        self.deals.append(json.dumps(deal, sort_keys=True))

    @gl.public.write
    def release_funds(self, deal_id: int) -> None:
        deal = json.loads(self.deals[deal_id])
        assert deal["status"] == "FUNDED", "Deal is not in a releasable state"
        assert str(gl.message.sender_address) == deal["client"], \
            "Only the client can release funds without a dispute"

        deal["status"] = "RELEASED_TO_FREELANCER"
        self.deals[deal_id] = json.dumps(deal, sort_keys=True)

    @gl.public.write
    def submit_client_evidence(self, deal_id: int, evidence_url: str, claim: str) -> None:
        deal = json.loads(self.deals[deal_id])
        assert deal["status"] == "FUNDED", "Deal is not open for evidence"
        assert str(gl.message.sender_address) == deal["client"], \
            "Only the client can submit client-side evidence"

        deal["client_evidence_url"] = evidence_url
        deal["client_claim"] = claim
        deal["status"] = "DISPUTED"
        self.deals[deal_id] = json.dumps(deal, sort_keys=True)

    @gl.public.write
    def submit_freelancer_evidence(self, deal_id: int, evidence_url: str, claim: str) -> None:
        deal = json.loads(self.deals[deal_id])
        assert deal["status"] == "DISPUTED", "A dispute must be raised first"
        assert str(gl.message.sender_address) == deal["freelancer"], \
            "Only the freelancer can submit freelancer-side evidence"

        deal["freelancer_evidence_url"] = evidence_url
        deal["freelancer_claim"] = claim
        self.deals[deal_id] = json.dumps(deal, sort_keys=True)

    @gl.public.write
    def resolve_dispute(self, deal_id: int) -> None:
        deal = json.loads(self.deals[deal_id])
        assert deal["status"] == "DISPUTED", "Deal is not under dispute"
        assert deal["freelancer_evidence_url"] != "", \
            "Both sides must submit evidence before resolution"

        client_claim = deal["client_claim"]
        client_url = deal["client_evidence_url"]
        freelancer_claim = deal["freelancer_claim"]
        freelancer_url = deal["freelancer_evidence_url"]
        description = deal["description"]

        def verify_dispute() -> str:
            client_content = gl.nondet.web.render(client_url, mode="text")[:6000]
            freelancer_content = gl.nondet.web.render(freelancer_url, mode="text")[:6000]

            prompt = f"""
You are an impartial arbitrator resolving a dispute between a client and
a freelancer over a work agreement.

AGREEMENT DESCRIPTION:
{description}

CLIENT'S CLAIM:
{client_claim}

CLIENT'S EVIDENCE (fetched from {client_url}):
{client_content}

FREELANCER'S CLAIM:
{freelancer_claim}

FREELANCER'S EVIDENCE (fetched from {freelancer_url}):
{freelancer_content}

Decide, based ONLY on the evidence above, whether the agreed work was
genuinely delivered as described. Be conservative: only rule in favor of
the freelancer if the evidence clearly supports that the work was
completed as agreed. Otherwise rule in favor of the client.

Return ONLY valid JSON in exactly this structure:
{{"winner": "client" or "freelancer", "reasoning": "one or two short sentences"}}
"""
            result = gl.nondet.exec_prompt(prompt)
            result = result.replace("```json", "").replace("```", "").strip()

            parsed = json.loads(result)
            normalized = {
                "winner": parsed.get("winner", "client"),
                "reasoning": parsed.get("reasoning", ""),
            }
            return json.dumps(normalized, sort_keys=True)

        consensus_result = gl.eq_principle.prompt_comparative(
            verify_dispute,
            principle="The winner field must be exactly the same.",
        )

        parsed_result = json.loads(consensus_result)
        winner = parsed_result.get("winner", "client")

        deal["status"] = (
            "RESOLVED_FOR_FREELANCER" if winner == "freelancer" else "RESOLVED_FOR_CLIENT"
        )
        deal["resolution_reasoning"] = parsed_result.get("reasoning", "")
        self.deals[deal_id] = json.dumps(deal, sort_keys=True)

    @gl.public.view
    def get_deal(self, deal_id: int) -> str:
        assert 0 <= deal_id < len(self.deals), "Invalid deal ID"
        return self.deals[deal_id]

    @gl.public.view
    def get_all_deals(self) -> list[str]:
        return list(self.deals)

    @gl.public.view
    def total_deals(self) -> int:
        return len(self.deals)
