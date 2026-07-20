# The "one-behind deploy" bug in ogc-app-pack-generator

This document is the **canonical explanation** of the bug this fork patches. It is
written so it can be pasted directly into an upstream support ticket / GitHub issue
against [MAAP-Project/ogc-app-pack-generator](https://github.com/MAAP-Project/ogc-app-pack-generator),
**and** so an automated agent (Jules) can reliably tell (a) what "buggy" means and
(b) whether upstream has resolved it.

---

## TL;DR

The **"Deploy application package"** step in `action.yml` builds the raw-CWL URL from
**`${{ github.sha }}`** (the commit checked out at the *start* of the run). But the CWL
is **committed and pushed two steps earlier**, and its filename is **branch-based**
(`process_<repo>_<branch>.cwl`) and **overwritten every run**. So the URL pinned to
`github.sha` resolves to the file as it was *before* this run — i.e. the **previous
run's CWL**. Every deploy therefore registers **one run behind**.

**Fix:** build the URL from the commit that was *just pushed* (`$(git rev-parse HEAD)`)
instead of `${{ github.sha }}`.

---

## Affected code

`action.yml` → step **"Deploy application package"** (upstream `main`, ~lines 118–124):

```yaml
- name: Deploy application package
  if: ${{ inputs.deploy-app-pack == 'true' }}
  run: |
    FILE_PATH=cwl_workflows/${{ env.WORKFLOW_FILE_NAME }}
    RAW_URL="https://raw.githubusercontent.com/${{ github.repository }}/${{ github.sha }}/${FILE_PATH}"
    python3 ${{ github.action_path }}/deploy_app_pack.py --process-cwl-url ${RAW_URL} ...
  shell: bash
```

The generated CWL filename is set earlier in `action.yml`:

```yaml
WORKFLOW_FILE_NAME="process_${REPO_NAME}_${GITHUB_REF_NAME}.cwl"
```

— note it is keyed on the **branch**, not on the algorithm or content, so it is
**overwritten on every run of the same branch**.

## Why it is exactly "one behind"

Within a single action run the steps execute in this order:

1. **Generate CWL** → writes `cwl_workflows/process_<repo>_<branch>.cwl`.
2. **Commit and push workflow file** → commits + pushes that CWL as a **new commit**
   `C_new` (whose parent is `github.sha`).
3. **Deploy application package** → builds `RAW_URL` at **`github.sha`** = `C_new`'s
   parent = the repo state **before** step 2 = the CWL left there by the **previous**
   run.

So `deploy_app_pack.py --process-cwl-url` fetches and registers the **previous run's
CWL**, never the one this run just generated.

## Reproduction / observed evidence

Registering algorithms in sequence (each a separate run on the same branch):

| Run (by intent) | CWL it generated & pushed | CWL it actually deployed (`github.sha`) |
|---|---|---|
| capella   | capella   | (whatever was there before) |
| umbra     | umbra     | capella |
| satellogic| satellogic| **umbra** |
| list_dates| list_dates| **satellogic** |

We observed exactly this: the run whose title was *"satellogic"* registered
`umbra-ogc-test`; the *"list_dates"* run registered `satellogic-ogc-test`; `list_dates`
only registered after a **5th "flush" run**. In general: registering **N** algorithms
needs **N+1** runs, and a **single** algorithm must be run **twice**.

## Impact

- The registered OGC process points at a **stale (previous) CWL** — wrong image tag /
  wrong inputs than the operator intended for that run.
- Anyone registering algorithms with this action must know to run it twice / add a
  throwaway "flush" run. Silent and easy to miss.

## Suggested fix

Deploy the CWL at the commit that was **just pushed**, not the checkout commit:

```yaml
RAW_URL="https://raw.githubusercontent.com/${{ github.repository }}/$(git rev-parse HEAD)/${FILE_PATH}"
```

After the "Commit and push workflow file" step, `HEAD` **is** the new CWL commit
`C_new`. If the CWL was byte-identical to the previous run (no new commit), `HEAD` is
unchanged too — so this is correct in both cases. (Equivalent alternatives: capture the
pushed SHA as a step output, or use `github.event.after` on push events.)

## How to tell whether upstream has FIXED it

Inspect the **"Deploy application package"** step in upstream's `action.yml`. Upstream
is **FIXED** iff the CWL URL passed to `deploy_app_pack.py --process-cwl-url` is built
from the **just-pushed commit** — e.g. `$(git rev-parse HEAD)`, `github.event.after`, or
a captured post-commit SHA — **rather than `${{ github.sha }}`**. If that line still
uses `${{ github.sha }}`, upstream is **still buggy**.

## Environment

- Action: `MAAP-Project/ogc-app-pack-generator@main`
- Observed: July 2026
- Workaround in place: this repo (`Disasters-Learning-Portal/ogc-app-pack-generator`) is
  a fork whose **only** delta is the one-line fix above (see the `# FORK PATCH` comment
  in `action.yml`). Consumers pin the fork until upstream lands the fix; once upstream is
  fixed, the fork is retired and consumers switch back to `MAAP-Project/...`.
