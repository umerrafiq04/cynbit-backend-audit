# Verification Log

- **Assessment:** Cynbit Backend Developer Intern assessment
- **Candidate:** Umer Rafiq
- **Observation date:** 22–23 October 2026 (IST)
- **Method:** Ordinary navigation, public HTTPS GETs, scoped browser inspection, and static review of publicly referenced JavaScript. No contact or job-application action was invoked.

## Previously registered items

| ID | Earlier claim | Fresh verification | Handling |
|---|---|---|---|
| OBS-01 | Homepage returned `Strict-Transport-Security: max-age=63072000`. | Same HSTS value appeared on all eight sampled public HTML GETs (E-018). | Retain as a positive observation; do not generalize beyond sampled routes. |
| OBS-02 | Contact form was visible; submission and backend behavior were untested. | UI and a public client handler were verified. The handler calls `submitInquiry`; no actual request or response was captured and no action was invoked (E-004, E-014). | Retain the client-flow evidence and explicitly leave production behavior unknown. |
| REC-01 | Confirm validation, limits, abuse controls, and privacy practices in an authorized environment. | Public evidence does not establish whether those controls exist. | Retain only as a recommendation; no confirmed defect. |
| REC-02 | Capture sanitized Network evidence and assess route headers. | Selected headers were checked on eight routes, but no full Network export or first-party action exchange was available (E-018). | Partially addressed; retain authorized Network-evidence recommendation. |

**Prior-item tally:** Four reviewed; one verified (OBS-01), two partially verified (OBS-02 and REC-02), one unverified as an existing-condition claim (REC-01, recommendation only); none incorrect or removed.

## Fresh route and response-header pass

At 20:28:51-20:28:54 IST, ordinary GETs for `/`, `/careers`, `/careers/backend-developer-intern`, `/services`, `/contact`, `/privacy`, `/cookies`, and `/terms` each returned HTTP 200 HTML (E-017). All returned HSTS `max-age=63072000`. The selected headers CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, and Permissions-Policy were absent on each sampled response.

`Access-Control-Allow-Origin: *` was present on `/`, `/services`, `/privacy`, `/cookies`, and `/terms`; it was absent on `/careers`, `/contact`, and the internship detail page. The sampled responses contained public page content; wildcard CORS on these GETs alone does not establish a CORS vulnerability. None of the eight final responses returned `Set-Cookie`. Direct response sizes are recorded in the report. Redirect chains were not recorded.

The route-header pass was repeated at 19:26:42–19:26:46 IST on 23 October (E-018). All exact full URLs and per-route values are in the report. Each requested URL ended with a 200 response with HSTS `max-age=63072000`; the five selected headers remained absent. Wildcard CORS was present on the homepage, services, privacy, cookies, and terms pages; absent on careers, internship detail, and contact. No final response returned `Set-Cookie`. PowerShell's default redirect handling was used; redirect chains and intermediate headers were not recorded. The observation applies only to these point-in-time final HTML responses.

## Policy-page review

| Evidence | Page | Observation and limit |
|---|---|---|
| E-011 | `/privacy` | Returned 200 at 20:28:54 IST; page showed last updated 20 May 2026. Text describes minimizing collection, typically name/email/professional context, and names Resend and Prisma among providers. These are public statements, not independently verified implementation details. |
| E-012 | `/cookies` | Returned 200 at 20:28:54 IST; page showed last updated 20 May 2026. Text describes Google Analytics/page-interaction metrics and browser settings for managing cookies. This is not a full tag inventory or legal assessment. |
| E-013 | `/terms` | Returned 200 at 20:28:54 IST; page showed last updated 20 May 2026. No legal analysis was performed. |

## Forms, browser, and static client evidence

| Evidence | Surface | Observation and limit |
|---|---|---|
| E-008 | Internship application UI | Browser snapshot/initial HTML showed 23 controls and required date of birth, gender, phone, WhatsApp, and permanent address fields, plus a data-processing statement. No information was entered or sent. |
| E-009 | Contact form HTML | Required name, email, and message; optional company and industry. The five initial controls had no `maxlength` attribute. This does not establish runtime or server-side limits. |
| E-014 | Public JavaScript bundles | Contact bundle GET returned 200 at 20:31:07 IST on 22 Oct (24,534 bytes). It references `submitInquiry`, constructs `FormData`, shows a success state saying the inquiry was received and architects notified, and clears loading only after the awaited action returns. Application bundle returned 200 (28,394 bytes) and references `submitCandidateApplication`, adding a job identifier and serialized education data. No action was invoked. |
| E-015 | Browser storage | Names observed in the shared browser context: cookies `_ga`, `_ga_LK6CQWCWX0`, `_gcl_au`; local-storage keys `_gcl_ls`, `cynbit_newsletter_seen`; no session-storage keys. Values were not read. Exact observation time was not separately captured. Cookie-attribute inspection was unavailable, so setter, age, flags, and prior-visit state are unknown. |
| E-016 | Browser console | No page/console errors were observed during one reload of `/cookies`. This is one narrow reload, not a site-wide check. |
| E-005/E-010 | Limited browser request events | A third-party analytics POST appeared as `ERR_ABORTED` during navigation. The event view was incomplete; this does not show an application failure and does not establish that a first-party API is absent. |
| E-019 | Latest contact client bundle | GET of `https://www.cynbit.in/_next/static/chunks/app/(marketing)/contact/page-c119885162e933b7.js` returned 200 and 24,534 bytes at 19:24:38 IST on 23 Oct. In component `u`, `[e,t]` is pending/setter, `[a,i]` success/setter, `[l,n]` error/setter; handler `d` awaits `x` (`submitInquiry`). Pending is set true before the await, reset false only after, and bound to the button's `disabled` prop. Resolved success and failure both reach reset; rejection does not. No catch/finally or other pending reset exists in the component handler. Static review only: no form action was submitted and no rejection was triggered in production. |

## REL-01 local reproduction and reference API changes

- Added `code-examples/contact-form/contact-form.mjs`, a standalone model with a `finally` pending reset and generic error message for rejected/resolved failures.
- Added three built-in Node tests covering success, resolved failure, rejection, state cleanup, safe error text, and a successful retry.
- Added an environment-configurable request limit to the FastAPI reference API (16 KiB default), including streamed bodies, and restrictive headers on API JSON routes only. Invalid limit values fail app startup. Swagger docs are excluded from the API-only CSP.
- Expanded pytest coverage for empty/whitespace fields, declared and streamed over-limit requests, request ID/error envelope behavior, and API headers.

**Local test results:** `python -B -m pytest -p no:cacheprovider` — **23 passed**. `node --test code-examples/tests/contact-form.test.mjs` — **3 passed**. These verify only the local examples; they do not reproduce a live Cynbit action rejection or establish production security.

| ID | Local verification | Result and boundary |
|---|---|---|
| E-020 | Contact-form state-model tests | `node --test code-examples/tests/contact-form.test.mjs`: exit 0, 3/3 passed for success, resolved failure, rejected action, pending cleanup, generic error, and retry. This is the independent local model, not Cynbit code. |
| E-021 | FastAPI reference tests | `python -B -m pytest -p no:cacheprovider`: exit 0, 23/23 passed. Tests apply only to the local validation example. |
| E-022 | Fresh setup and server launch | In a new Python 3.11 venv, `python -m pip install --disable-pip-version-check -r requirements.txt` and `python -m pip check` both exited 0; pytest passed 23/23. Uvicorn CLI (`main:app`, app directory `code-examples\app`, explicit local host/port, auto-reload disabled) returned `GET /health` 200 `{"status":"ok"}`. The exact test PID was stopped after the response; no graceful server exit code is claimed. No Cynbit endpoint was contacted. |
| E-023 | Final report PDF | Regenerated from the final Markdown with local Mistune and Edge. Six pages; text extraction verified all 10 section headings, findings REL-01/HDR-01/PRIV-01/PRIV-02/CORS-01, current Python/Node test totals, and page numbering. Visual readability was checked in the integrated PDF reader. |

## Local example validation

`python -B -m pytest -p no:cacheprovider` passed **23 tests** (Python 3.11.9, pytest 9.1.1). `node --test code-examples/tests/contact-form.test.mjs` passed **3 tests** (Node v24.15.0). Python AST syntax parsing and import of the local FastAPI app passed. Tests target only local examples and make no requests to Cynbit.

## Clean setup and launch verification

- Created a temporary Python 3.11 virtual environment outside the repository.
- Installed the exact pinned `requirements.txt`; `python -m pip check` reported no broken requirements.
- In that environment, `python -B -m pytest -p no:cacheprovider` passed 23 tests.
- Started Uvicorn locally; `GET /health` returned HTTP 200 with `{"status":"ok"}`; the test server shut down cleanly.
- The Node test command passed all 3 local contact-state tests.
- No test or launch validation invoked a Cynbit form action or API.

## Findings interpretation and limits

- No exploitable security vulnerability was confirmed. No high- or critical-severity security issue is claimed.
- REL-01 is a low-severity code-path defect verified in the current public contact bundle: if the server action rejects, the pending state remains set and the button disabled. The scenario is substantiated by static control-flow analysis and the independent local model; it was not triggered on production.
- PR-01 and PR-02 are review recommendations, not confirmed privacy violations. Applicant-field necessity and browser-storage identifiers' source/purpose/age remain unknown.
- Missing selected headers are observations and defense-in-depth recommendations, not proof of XSS, clickjacking, or another exploit.
- No production form was submitted, no first-party server-action request/response was recorded, and no production data was created.
- No screenshots or HAR were saved. Cookie values, analytics query values, personal data, and action identifiers were not retained.
- Use written authorization and a designated staging environment before testing form submission or validation behavior.
