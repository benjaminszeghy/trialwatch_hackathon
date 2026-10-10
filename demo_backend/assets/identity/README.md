# Case desk visual identity

This is a presentation layer for the existing local dashboard. It changes no collection, scoring, feedback or API behavior.

The typeface pairing was verified on [TrialWatch's official page](https://cfj.org/trialwatch/) on 10 October 2026: Poppins for navigation and body text, Noto Serif for lead text. This dashboard uses the same open fonts, with Noto Serif additionally used for headings, case names and key numbers.

[Monocle](https://monocle.com/) supplied the editorial reference: serif hierarchy, fine dividing rules, quiet navigation, compact metadata and emphasis through typography. The warm ivory, ink and muted red palette and case-review layout are our own adaptation. No Monocle logo, proprietary Plantin font, CFJ logo or Cubano font is included. This is a student research dashboard, not an official TrialWatch brand implementation.

## Assets

`identity.css` is loaded after the existing dashboard styles. It covers the queue, dialogs, feedback controls and responsive layouts. FastAPI serves the directory at `/assets/identity`; the isolated demo mounts the same assets under `/demo/assets/identity`.

The five self-hosted Latin WOFF2 files total approximately 68 KiB. Poppins includes 400, 500, 600 and 700 weights; Noto Serif uses its variable font. Both families are distributed under the SIL Open Font License 1.1. Copies of the licenses and exact source URLs, retrieval date, file sizes and SHA-256 hashes are included in `fonts/` and `font-sources.json`. Font loading requires no third-party request during the demo.

Responsive checks cover desktop tables, tablet case cards and the full-width phone review sheet. Reduced-motion preferences remove decorative transitions; keyboard focus is visible. Priority colors remain paired with textual labels, and selected Yes/No controls retain their pressed state and accessible labels.
