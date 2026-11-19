# Product brief and operating model

## Vision and measures

Regional service teams and corporate leaders repeatedly reconcile dashboards before deciding what to do. InsightPortal gives them a place to discover accountable analytics products, compare regional performance and take definition disputes back to the right owner. The fictional scenario covers a multi-region equipment service business.

| Decision to support | Primary person | Success signal | Proposed pilot threshold |
| --- | --- | --- | --- |
| Prioritise delivery and margin interventions | Executive sponsor | Users can explain the KPI and identify a region in a walkthrough | 4 of 5 pilot participants |
| Close the month using consistent numbers | FP&A analyst | Revenue reconciles to signed-off serving inputs | 100% of included region-months |
| Replace recurring equivalent dashboard requests | Product Owner | New requests link to a product or name the gap | At least 80% in the first review |
| Make local managers self-sufficient | Site lead | Eligible users opening a product in the latest week | At least 70% by domain |
| Keep products useful after launch | Each domain lead | Returning share and satisfaction | At least 65% repeat use and 4.0/5 |

Thresholds describe proposed success criteria. All example analytics, cohorts and decision records are synthetic.

## Stakeholder map

| Stakeholder | Decision or expectation | Engagement |
| --- | --- | --- |
| Executive sponsor | Resolve scope trade-offs when several departments need the same delivery slot | Monthly outcome review |
| Finance / FP&A | Own recognised revenue and margin and reconcile the close | Monthly close workshop and sprint review for finance changes |
| Commercial / Sales Operations | Own bookings and win rate, surface regional adoption barriers | Weekly discovery during pilot, fortnightly review |
| Operations / Service Delivery | Own delivery commitments, monitor source freshness and action regional outliers | Weekly operations review |
| People / People Analytics | Own training and absence definitions and propose safe cohort granularity | Review every expansion of workforce dimensions |
| Data Governance | Ratify shared dimensions, contract changes and dissemination rules | Refinement for changes to grain, semantics or access |
| Product Owner | Own vision, prioritisation, acceptance evidence and stakeholder communications | Weekly intake, fortnightly refinement and sprint review |
| Analytics engineering and architecture | Own implementation estimates, parity and serving design | Architecture review for new source or grain |
| Release Lead | Validate the agreed release evidence and record the simulated rollout | Release review with the domain steward and Product Owner |

## RACI and data ownership

R is responsible, A is accountable, C is consulted and I is informed. The domain steward is the lead listed in the corresponding [consumption contract](../contracts/metrics.v1.json).

| Decision | Product Owner | Domain steward | Other domain leads | Governance | Engineering | Release Lead |
| --- | --- | --- | --- | --- | --- | --- |
| Rank and scope requests | A/R | C | C | C | C | I |
| Define and reconcile a KPI | C | A | C | C | R | I |
| Publish shared dimensions and contract schema | C | C | C | A | R | I |
| Approve a domain acceptance decision | C | A/R | I | C | C | I |
| Verify serving quality and freshness | I | A | I | C | R | C |
| Approve release after acceptance evidence | C | C | I | C | R | A |

If a steward submits an intake item, the demo delegates its acceptance or decline to Data Governance. A separate Release Lead records rollout. The roles are simulated for local demonstrations.

## Discovery and cross-domain agreements

| Conflict surfaced in simulated discovery | Agreed definition and acceptance | Where to inspect |
| --- | --- | --- |
| Sales uses signed order values in a view Finance expects to reconcile to closed books | Finance owns revenue at fulfilment. Commercial owns net bookings at booking month. Shared calendar and region permit comparison. A reconciliation bridge requires source identifiers and a grain agreement; it is deferred. | Revenue and bookings dictionary entries, IP-101 and IP-201 |
| Regional dispatch teams reset the committed completion time when rescheduling | Operations owns the original promised time rule. Ratios pool completed visit counts. A reason-code drill-down requires cross-region completeness. | On-time delivery, IP-102 and IP-203 |
| People wants deeper cuts while leadership asks for site comparisons | Publish region-month cohorts and no employee identities. Withhold the product on a cohort below the demo support threshold. Treat real disclosure risk assessment as a release dependency. | Training compliance, Data Health, IP-103 and IP-202 |
| Each department requests its own front page | Ship one executive landing page with one KPI per domain, then link to domain detail. Keep certified definitions in a shared semantic layer. | Executive overview, product catalog and IP-101 |

## Delivery cadence

Use two-week sprints. Intake captures requests in the portal. The Product Owner reviews score, evidence, dependencies and blast radius in refinement and promotes only ready work to GitHub Issues, the engineering delivery backlog. At planning, reserve one reliability slot. Domain leads share a written decision record before the review so distributed stakeholders can comment asynchronously. A steward validates the agreed walkthrough, then the Release Lead records the decision. Review four weeks of adoption at the next monthly sponsor review.

**Definition of Ready.** Name an affected user and decision, owner, baseline or proxy, agreed KPI or proposed contract change, testable acceptance criteria, dependency and data/rollout risk. If required evidence is missing, time-box a technical spike.

**Definition of Done.** Implement and review the change, reconcile totals to serving inputs, test adverse cases, update the dictionary and API contract, document ownership and migration impact, obtain domain acceptance, capture release evidence and specify the adoption check.

## Adoption decisions

The adoption screen models eligible participants, weekly active users by product, repeat use among latest-week active users and the average survey rating. A weekly active user is an eligible pilot member who opened that product at least once that week. Repeat use means activity in the latest week and at least one prior week within the four-week window. Different products can include the same participants. Sample sizes stay visible and local demo feedback stays distinct from the synthetic cohort baseline. One simulated respondent can revise one rating per domain.

In the demo Operations has 79 of 125 eligible users active and reports 3.8/5 satisfaction. The Product Owner proposes a dispatch walkthrough on delivery commitments, then reviews comparable cohort engagement after the next release. People Analytics also falls below the active-user threshold and enters discovery with its steward before requesting new charts. Adoption alone cannot justify expanding a workforce data contract.
