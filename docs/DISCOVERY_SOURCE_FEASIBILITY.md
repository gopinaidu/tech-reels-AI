# Discovery Source Feasibility — D-025

**Date verified:** 2026-08-08

## Purpose

This spike verifies that ReelAgent has a compliant, technically practical access path for each planned discovery source family before any source adapter is implemented.

The project preference remains:

**Official API → RSS/Atom/feed → supported public endpoint → scraping only when necessary and permitted.**

Scraping is not an automatic fallback. If a source does not expose an allowed access path, ReelAgent should omit that source rather than work around its terms.

## Recommendation

The MVP can proceed with discovery using:

1. Official vendor/project feeds and public release/documentation endpoints.
2. GitHub public APIs.
3. Hacker News official API.
4. arXiv API.
5. Selected engineering blogs only where an RSS/Atom/feed or other explicitly supported public access path exists.

**Reddit should not be a hard MVP dependency.** Its Data API is available, but current terms require OAuth and impose materially stronger use restrictions. Any ReelAgent Reddit adapter should remain deferred until the exact intended use is confirmed to fit Reddit's current Data API terms or separate permission is obtained where required.

This means lack of Reddit access does not block the first working discovery pipeline.

## Feasibility Matrix

| Source family | Preferred access | Authentication | Rate / usage constraints | Cost | MVP status |
|---|---|---|---|---|---|
| Official vendor/project docs and release notes | RSS/Atom/feed when offered; otherwise supported public documentation/release endpoint | Usually none for public feeds/pages; source-specific APIs may differ | Source-specific; adapter must document terms and polling behavior | Usually free for public sources | **Approved** |
| GitHub | GitHub REST API; GraphQL only when it provides a clear query advantage | Public REST data can be read unauthenticated; authenticated access preferred for useful limits | Public unauthenticated REST: 60 requests/hour. Authenticated user REST: generally 5,000 requests/hour. Search has separate limits; secondary rate limits also apply | No separate API fee for normal public API use under standard account limits | **Approved** |
| Hacker News | Official Hacker News Firebase API | None | Official API currently states there is no rate limit; client should still poll conservatively and cache results | Free | **Approved** |
| Reddit | Reddit Data API / Developer Platform | OAuth required | Subject to Responsible Builder Policy, Developer Terms and Data API Terms. Commercial use, excess-rate research, or uses outside expressly permitted terms may require a separate agreement | Potential fees / separate agreement depending on use | **Deferred / conditional** |
| arXiv | Official arXiv API returning Atom | None for normal public API queries | Use conservative request pacing; arXiv guidance asks clients making repeated calls to wait roughly three seconds between requests. Large queries should be paged/refined | Free for ordinary API use, subject to terms | **Approved** |
| Selected engineering blogs | RSS/Atom/feed first; source-supported public endpoint second | Usually none for public feeds | Per-site terms and feed behavior; no generic scraper | Usually free | **Approved only per-source after adapter checklist** |

## Source-Specific Notes

### 1. Official vendor/project documentation and release notes

This is the highest-authority discovery family and should remain the first place ReelAgent looks for release/change signals.

There is no single universal API for this family. Each concrete source must declare its supported access mechanism. Examples include RSS/Atom release feeds, project release APIs, changelogs, and supported public documentation pages.

Adapter rule:

- Prefer a published feed or API.
- Record the canonical source URL.
- Record the source's publication/release timestamp when available.
- Use conditional HTTP requests/caching when supported.
- Do not scrape a site merely because no feed was found; verify that automated access is allowed first.

### 2. GitHub

GitHub is practical for project releases, repository activity, tags, and selected trending signals.

Verified constraints:

- Public REST resources can be fetched without authentication.
- The unauthenticated primary REST limit is 60 requests/hour per originating IP.
- Authenticated requests generally receive a 5,000 requests/hour primary limit for a user.
- Search endpoints have separate/custom rate limits.
- GitHub also enforces secondary rate limits, so ReelAgent must obey `Retry-After` / rate-limit headers and must not retry aggressively.
- GitHub recommends authenticated requests and avoiding unnecessary polling.

MVP recommendation:

Use authenticated REST access through a least-privilege token or GitHub App when the adapter is implemented. Cache release/repository metadata and use conditional requests where applicable.

Official references:

- https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api

### 3. Hacker News

Hacker News exposes an official API backed by Firebase and provides near-real-time access to stories, comments, jobs, polls, and ranking lists.

Verified constraints:

- No registration/authentication is required.
- The official API documentation currently states that there is no rate limit.
- The API is intentionally low-level, so obtaining story/comment details can require multiple item requests.
- Clients are expected to tolerate added fields and API evolution.

MVP recommendation:

Use the official API for discovery/trend signal only. Cache fetched item IDs and item details so repeated discovery runs do not refetch unchanged content unnecessarily.

Official reference:

- https://github.com/HackerNews/API

### 4. Reddit

Reddit is valuable as practitioner/trend signal, but it is the source with the greatest access-policy uncertainty for ReelAgent.

Current verified constraints:

- Reddit requires OAuth for Data API authentication.
- Use is governed by the Responsible Builder Policy, Developer Terms and Data API Terms.
- Reddit's Data API Terms state that commercial purposes, research in excess of rate limits, or uses not expressly permitted may require a separate agreement.
- Reddit reserves the right to charge fees for Data API access.
- Reddit explicitly restricts some uses of Reddit user content involving machine-learning/AI training without rightsholder permission.
- Reddit has publicly signaled a longer-term move toward its Developer Platform for trusted automation while continuing limited public Data API access during the transition.

ReelAgent does **not** need Reddit content for model training. The intended use would be topic discovery and practitioner-signal extraction, but because generated public content could eventually support monetized channels, the exact use should be cleared before implementation.

MVP decision recommendation:

**Do not build the Reddit adapter in the first discovery increment.** Treat it as an optional later adapter after a focused policy check/approval. The system design must not depend on Reddit being available.

Official/current references:

- https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki
- https://redditinc.com/policies/data-api-terms

### 5. arXiv

arXiv provides a public query API suitable for discovering recent research by category, title, author, and other metadata.

Verified constraints:

- No normal authentication is required.
- Results are returned in Atom format.
- Clients should use modest page sizes and refine large result sets.
- arXiv guidance for repeated requests is to wait approximately three seconds between calls.
- For ReelAgent's small-volume use, this is comfortably within practical limits.

MVP recommendation:

Use targeted categories/queries and small result pages. Cache seen arXiv IDs and publication/update timestamps to avoid repeated processing.

References:

- https://info.arxiv.org/help/api/index.html
- https://arxiv.org/help/api/tou

### 6. Selected engineering blogs

There is no universal blog API. This family is feasible only as a registry of individually approved sources.

Each blog adapter/config entry must record:

- publisher/domain
- discovery URL
- supported access method (`rss`, `atom`, `api`, or other explicitly supported endpoint)
- authentication if any
- polling interval
- known terms/usage constraints
- attribution requirements
- last verification date

If a blog offers neither a feed nor a clearly permitted automated-access path, it should not be included in MVP discovery.

## Adapter Readiness Checklist

Before implementing any individual source adapter, verify and record:

- [ ] Exact endpoint/feed is identified.
- [ ] Access method is officially supported or explicitly permitted.
- [ ] Authentication requirement is understood.
- [ ] Rate limits / polling expectations are documented.
- [ ] Retry behavior is bounded and respects server guidance.
- [ ] Cost/paid-tier implications are known.
- [ ] Required attribution/provenance fields can be preserved.
- [ ] Terms were checked recently enough for the source's risk level.
- [ ] Retrieved content is treated as untrusted data under D-023.

## D-025 Resolution Proposal

D-025 can be considered resolved for initial implementation with the following scope:

- **Initial discovery adapters may target official feeds/docs, GitHub, Hacker News, and arXiv.**
- **Engineering blogs are enabled only source-by-source after the checklist above is satisfied.**
- **Reddit is deferred and is not a dependency of MVP discovery.** A separate policy/permission check is required before its adapter is implemented.

This resolution removes D-025 as a blocker for implementing the first compliant discovery adapter while preserving the project's no-workaround access rule.
