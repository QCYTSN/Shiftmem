"""Reuse attribution for v2 strategy-experience metrics.

Protocol v2 counts an experience as *reused* only when it was supplied to the
reviewer, cited in the proposal, and the proposal passed the schema/bounds
validator. Retrieval without citation and citation inside a rejected proposal
are reported separately so H2's invalid-reuse rate is not inflated by mere
retrieval or by discarded proposals.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReuseAttribution:
    reused: list[str] = field(default_factory=list)
    retrieved_not_cited: list[str] = field(default_factory=list)
    cited_but_rejected: list[str] = field(default_factory=list)


def classify_reuse(
    supplied_ids: list[str],
    cited_ids: list[str],
    proposal_accepted: bool,
) -> ReuseAttribution:
    supplied = list(dict.fromkeys(supplied_ids))
    cited = [mid for mid in dict.fromkeys(cited_ids) if mid in supplied]
    cited_set = set(cited)

    if proposal_accepted:
        reused = cited
        cited_but_rejected: list[str] = []
    else:
        reused = []
        cited_but_rejected = cited

    retrieved_not_cited = [mid for mid in supplied if mid not in cited_set]
    return ReuseAttribution(
        reused=reused,
        retrieved_not_cited=retrieved_not_cited,
        cited_but_rejected=cited_but_rejected,
    )
