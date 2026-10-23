# Cynbit Backend Technical Audit

An evidence-bounded, passive review of publicly accessible Cynbit pages, accompanied by a local FastAPI validation example and contact-form retry model. The audit is for the Backend Developer Intern assessment and was prepared by Umer Rafiq on 22–23 October 2026.

> The local example is proposed reference code only. It is not Cynbit production code and does not connect to Cynbit systems.

## Scope and responsible testing

The review used normal browser navigation and ordinary HTTPS GET requests for eight public pages: home, careers, internship detail, services, contact, privacy, cookies, and terms. Public JavaScript bundles and browser storage names were inspected without invoking any form action or reading cookie values. No form was submitted; no authenticated/private resources, scanning, load tests, production data changes, or credentials were involved. No source code or internal infrastructure was available.

Verified observations are separated from unknown backend behavior and recommendations in [the audit report](report/backend-audit.md). The latest pass confirmed all eight sampled page GETs returned HTTP 200 and HSTS; five selected hardening headers were absent on each. This is a configuration observation, not proof of an exploit. The current contact client bundle substantiates a code-path reliability defect: a rejected server action skips the pending-state reset, leaving the submit button disabled. This was not triggered on production; a separate local model demonstrates a `finally`-based fix and retry tests. Browser storage names merit reconciliation against the cookie notice, but source, age, and attributes were not established. No exploitable security vulnerability was confirmed. See the [verification log](evidence/verification-log.md).

## Technologies

- Python 3.11+
- FastAPI and Pydantic v2
- Uvicorn
- pytest and FastAPI TestClient

## Repository structure

```text
.
|-- code-examples/
|   |-- app/main.py
|   |-- contact-form/contact-form.mjs
|   `-- tests/
|       |-- test_api.py
|       `-- contact-form.test.mjs
|-- evidence/
|   `-- verification-log.md
|-- report/
|   |-- backend-audit.md
|   `-- backend-audit.pdf
|-- .gitignore
|-- pytest.ini
|-- README.md
`-- requirements.txt
```

## Audit summary

| Status | Summary |
|---|---|
| Verified | Eight public pages (home, careers, internship detail, services, contact, privacy, cookies, terms) returned HTTP 200 to individual GET requests. |
| Verified | All eight sampled HTML responses returned HSTS `max-age=63072000`. |
| Verified | The contact page rendered name, email, organization, industry, and message controls plus a “Send Inquiry” button. |
| Verified observation | `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and `Permissions-Policy` were absent on all eight sampled HTML pages; this is not, by itself, an exploitable vulnerability. |
| Verified code-path defect | A rejected contact server-action Promise bypasses the pending reset, leaving the button disabled; production failure was not triggered. A separate local model fixes this with `finally` and proves retry works. |
| Potential privacy review | Browser storage names do not fully map one-to-one to the public cookie policy text; the identifiers' source and age are unknown. |
| Potential risk | The internship application UI marks several personal-data fields as required; necessity and backend handling are unknown. |
| Unverified | Actual form request/response and server-side validation, persistence, notifications, rate limits, authentication/authorization, cookie attributes/setters, and redirects. |
| Recommendation | Obtain authorized, sanitized Network evidence in staging and verify the form behavior using an approved test record. |

See the evidence IDs, limitations, and recommendations in [report/backend-audit.md](report/backend-audit.md).

## Local reference API

The demonstration validates an inquiry-shaped JSON request and returns a request ID. It enforces Pydantic field limits plus a configurable body cap (default 16 KiB) and applies API-oriented security headers to JSON routes (not interactive docs). It does **not** persist, email, or forward the inquiry and is not production-ready. It has no authentication, database, CORS policy, or rate limiter; HSTS is intentionally left to the HTTPS edge.

### Install and test (Windows PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
python -B -m pytest -p no:cacheprovider
node --test code-examples/tests/contact-form.test.mjs
```

The Python example uses Python 3.11+. The separate, dependency-free retry-model tests use Node.js 18+. To override the demo body limit in PowerShell before launch, set `$env:CYNBIT_REFERENCE_MAX_BODY_BYTES = '16384'`; invalid values stop app initialization.

### Run locally

```powershell
python -m uvicorn main:app --app-dir code-examples\app --reload
```

The interactive OpenAPI page is at `http://127.0.0.1:8000/docs`; the basic health route is `http://127.0.0.1:8000/health`.

Example local request:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/inquiries -Method Post -ContentType 'application/json' -Body '{"name":"Alex Rivera","email":"alex@example.com","message":"Please contact me about a project."}'
```

## Tests and results

Run the Python API tests and the dependency-free Node state tests from the repository root. Python coverage includes successful validation, trimming, required fields, email format, limits, generic errors, safe logs, request IDs, 404/405, malformed/non-object JSON, wrong types, extra fields, and declared/streamed over-limit bodies. Node coverage exercises success, resolved failure, rejected Promise, pending reset, safe generic errors, and retry.

**Execution result:** `python -B -m pytest -p no:cacheprovider` — **23 passed** (Python 3.11.9, pytest 9.1.1). `node --test code-examples/tests/contact-form.test.mjs` — **3 passed** (Node v24.15.0). Python syntax/import checks also passed. Tests make no requests to Cynbit and do not establish production security.

## PDF

The editable report is [report/backend-audit.md](report/backend-audit.md), and the rendered, checked PDF is [report/backend-audit.pdf](report/backend-audit.pdf). The PDF was printed from the Markdown-rendered report using local Microsoft Edge and checked for readable text and page count. If you edit the Markdown report, regenerate/export its PDF from a Markdown renderer, then confirm the PDF contains the updated findings, evidence IDs, test results, and page numbers before submission.

## Evidence limitations

- A single request's response size and elapsed time is not a performance benchmark.
- No form was submitted and no first-party server-action/API request or response was captured. The public bundle references actions, but invoking them could create real inquiries/applications.
- The REL-01 failure is established by static code-path analysis and reproduced in a local independent model; it was not triggered on the live site.
- Cookie values, setter, creation time, flags, and policy-consent behavior were not captured; the browser's cookie-attribute inspection API was unavailable.
- A console listener found no errors during one reload of `/cookies`; that narrow check is not representative of all pages or actions.
- No applicant data was entered or submitted; the application form’s required personal-data fields are a data-minimization review item, not a confirmed defect.
- A missing observation is not evidence that a control or endpoint is absent.
- Response headers do not establish the site's complete hosting or backend architecture.
- No raw HAR, cookies, request identifiers, user data, or secrets are committed.

## Security and privacy

Do not commit `.env` files, credentials, cookies, tokens, or unredacted browser captures. Review the server-side retention, access, and privacy requirements before extending the sample. Use a staging system and explicit authorization for any submission testing. The sample deliberately avoids logging request bodies and does not retain submitted data.

## Submission checklist

- [ ] Create or confirm the public repository URL (do not publish without review).
- [ ] Review the Markdown report and include the PDF if rendering has been verified.
- [ ] Confirm source code and test results are current.
- [ ] Confirm README setup/test commands work on the submission machine.
- [ ] Add sanitized evidence only; do not include raw browser profiles, HAR secrets, or personal data.
- [ ] Check for secrets, `.env`, caches, virtual environments, and unrelated personal files.
- [ ] Confirm the correct candidate portal and assessment requirements.
- [ ] Submit before **Saturday, 24 October 2026, 1:30 PM IST**.

No repository has been published and no assessment submission has been made.
