# NJDG data-access pilot

Inspection date: 9 October 2026. Source: https://njdg.ecourts.gov.in/njdg_v3/?p=home&app_token=

## Retrieved sample

The pilot follows the portal's Alerts > Instituted in Last Month > Criminal path, filtered to Maharashtra, Pune, District and Session Court ,Pune. The establishment's displayed aggregate count is 890. The first 25 displayed entries were captured from the case-list table after the user completed its CAPTCHA. This is a convenience sample in portal order.

The sample contains 16 Bail Applications, 6 Sessions Cases, 2 Criminal Appeals and 1 Criminal Revision. These are court proceedings. They are not confirmed journalist cases or 25 independent FIR families. The calendar boundaries behind the portal's “Last Month” label have not been independently verified. Two detail views, Sessions Case / 619 / 2026 and Bail Application / 4780 / 2026, were inspected after user-completed CAPTCHAs.

## Fields observed

| Field | Verified from the retrieved list | Coverage |
|---|---|---|
| State, district, establishment | Yes, from the selected navigation context | 25/25 |
| Case type, number, year | Yes, from each displayed case label | 25/25 |
| CNR | Displayed in the inspected details | Observed in 2/2 inspected details; 23 uninspected |
| Filing and registration dates | Displayed in the inspected details | Observed in 2/2 inspected details; 23 uninspected |
| Stage and next hearing date | Displayed in the inspected details | Observed in 2/2 inspected details; 23 uninspected |
| Explicit pending/disposed status | No value separately recorded in the inspected views | Kept unknown |
| Act and section | Displayed in the inspected details | Observed in 2/2 inspected details; 23 uninspected |
| Police station, FIR number and year | Displayed in the inspected details | Observed in 2/2 inspected details; 23 uninspected |
| Order or judgment links | No download link visible in the inspected details | Two views checked; 23 uninspected |
| Journalist or expression nexus | Not established by this list | Unknown for all 25 |

The exported CSV includes both inspected details and deliberately leaves unobserved detail fields blank. Journalist status is “unknown” for every row. Blank fields record the collection limit, not the absence of the fact in the court's record.

## Inspected detail example

Sessions Case / 619 / 2026 has displayed CNR MHPU01-008973-2026, normalized as MHPU010089732026. Its filing date is 7 August 2026 and registration date is 21 September 2026. The displayed next hearing is 23 October 2026 and the stage is preserved verbatim as “Argument on Exh.____Unready.” The Acts table lists Bharatiya Nyaya Sanhita sections 124(1),352. FIR metadata lists Kothrud Police Station, FIR 140, year 2026. These facts are portal metadata, not independent verification of allegations or legal applicability. These sections do not match the scored provisions in the current catalogue.

Bail Application / 4780 / 2026 has displayed CNR MHPU01-010140-2026, normalized as MHPU010101402026. Its filing and registration dates are both 5 September 2026. The displayed next hearing is 12 October 2026 and its stage is “Order.” That stage does not establish whether bail was granted or denied. The Acts table separately lists Bharatiya Nagarik Suraksha Sanhita section 483 and Bharatiya Nyaya Sanhita sections 103, 3(5). These Act names and section sets remain distinct. FIR metadata lists Chatushrungi Police Station, FIR 272, year 2026. None of these displayed provisions matches a scored provision in the current catalogue.

The raw detail text and observed link lists are saved in `njdg-raw-details.json`. Normalized fields in `njdg-observed-details.json` retain original text spans and source-text hashes. No explicit pending/disposed value or journalist label is inferred from hearing dates or a party name.

## Access finding

The portal required a CAPTCHA to reach the establishment's list. Opening Sessions Case / 619 / 2026 then prompted a second CAPTCHA before the detail view. After the user completed it, that detail was captured. Opening Bail Application / 4780 / 2026 prompted another CAPTCHA, which the user also completed. Both tested detail entries therefore required verification. The pilot has not tried to bypass these checks and does not establish unattended bulk-detail access.

The CSV was generated from observed table rows and the inspected detail text. The portal's native CSV button was tested once, but no downloadable file was captured before the browser download wait timed out. This does not establish that export is broken for a human browser. No public bulk-detail API or provision-based search has been verified in this pilot.

## Next technical step

The pilot confirms that law fields and procedural dates can be read from at least one detail view. Next, use reviewed details for exact Act-and-section matching against the existing law catalogue. For document extraction experiments, continue with the existing AWS judgment snapshot until a usable NJDG document-acquisition route is confirmed. Require CNR or independently checked proceeding identity for linking. High Court and District Court proceedings may have different CNRs even when they relate to the same underlying FIR.

No law score is assigned to these rows until the actual charge provision and version have been verified. The current law-score table remains a separate structural index.
