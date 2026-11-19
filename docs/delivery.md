# Roadmap and delivery evidence

The Product Owner owns the roadmap. GitHub Issues hold delivery decisions, dependencies and acceptance evidence after the backlog is initialised. [The issue and milestone seed](backlog.json) is the portable backlog for a repository without existing issues. Requests in the portal stay at intake until the Product Owner promotes an agreed slice into delivery. The demo sorts intake by `3 × impact + 2 × urgency − effort`. The delivery order also accounts for governance gates and prerequisites and can override the intake ranking.

| Release | Scope | Exit decision |
| --- | --- | --- |
| [v1.0.0](releases/v1.0.0.md) · Local demo | Catalog, semantic registry, four domain marts, filters and drill-down, release workflow, health and adoption | Finance can reconcile revenue, each domain can explain its KPIs, invalid contracts are withheld and an intake item reaches a recorded release |
| v1.1 · Pilot discovery | Bookings-to-revenue bridge spike, People disclosure assessment, dispatch reason-code discovery | Compare bridge precision, approve workforce release boundary and agree coverage threshold before committing to new detail |
| v1.2 · Managed serving | Snowflake parity in a dedicated environment, scheduled publication telemetry and identity design | Prove Snowflake parity, approved reader privileges, ownership, alert routing and rollback of a bad publication before any managed pilot |

## Release communication and acceptance

1. Distribute a short preview with the story, change in definitions, data cut-off and participation criteria. Give remote reviewers an asynchronous option.
2. Run the [walkthrough](walkthrough.md). Ask each steward to reconcile one metric to its source and show an example of an SLA breach or unsupported slice.
3. Rank discovery gaps. Record the acceptance result and reason in the linked issue. Record the demo release decision using the Release Lead.
4. Review adoption in four weeks. Carry forward a finding only when a named owner agrees which decision or workflow it should improve.

## Prioritisation and risk register

| Risk or pressure | Decision | Evidence and follow-up |
| --- | --- | --- |
| Revenue and bookings get relabelled as a single commercial total | Keep two metrics and prioritise a bridge spike over adding charts | Dictionary and IP-201 |
| Late Operations publication erodes trust but leadership needs a monthly trend | Display freshness warning and serve the validated publication. Withhold on structural failure. | Data health and IP-102 |
| Workforce metrics invite low-support segmentation | Keep regional grain with a synthetic support gate, defer additional dimensions and obtain governance input | IP-103 and IP-202 |
| Snowflake support could hide a warehouse outage via a fallback | Use explicit mode selection and a sanitised unavailable state. Require parity evidence in a dedicated environment. | IP-301 |
| Synthetic reviewer roles cannot support a real shared deployment | Keep the demo on localhost. Put corporate authentication, authorisation, immutable audit retention and operational monitoring behind the next architecture gate. | IP-302 |

## AI-assisted delivery

OpenAI Codex supported implementation, tests and documentation. For a future team, Copilot or Claude Code can help draft tests or surface migration edge cases. Reviewers remain accountable for KPI semantics, leakage reviews and acceptance evidence. The release process uses deterministic fixtures and executable tests so reviewers can verify claims independently.
