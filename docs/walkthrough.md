# Stakeholder walkthrough

Allow twelve minutes. Start with a new local workspace so the supplied requests and ratings are in their baseline states.

| Time | Reviewer and scenario | Evidence to look for |
| --- | --- | --- |
| 0–2 min | Executive sponsor opens Executive overview and chooses April on the revenue trend, then Metro Belt | The regional panel changes to April. Selecting the region updates all cards while preserving the monthly drill. |
| 2–4 min | Finance and Commercial open Metric dictionary and compare recognised revenue with net bookings | Recognition and booking events have different ownership and booking dates. Both use the same month and region and can coexist without pretending to reconcile. |
| 4–6 min | Operations compares its trend and visits, then opens Data health | On-time rate pools visits. Operations shows a validated but late publication. Other domains remain current. |
| 6–7 min | People Analytics opens training compliance and checks its grain, exclusions and owner | Cohort-level scope and rule are visible. The release checks cover the small-cohort scenario. |
| 7–10 min | An analyst submits a fictional request. Product Owner triages it. Domain steward accepts. Release Lead records release. | The intake queue reorders by score. Incorrect actors are rejected. The versioned decision history remains visible after reload. |
| 10–12 min | Product Owner opens adoption results and adds a local Operations rating | Baseline and local feedback remain separate. Use the low Operations satisfaction to propose a specific follow-up experiment. |

To reproduce the withheld state instead of modifying a demo database, run `python -m pytest tests/test_analytics.py -k quality_gates`. For visual and interaction evidence, run the browser check described in the README.
