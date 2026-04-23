---
title: "🌙 Nightly Build Failure — {{ date | date('YYYY-MM-DD') }}"
labels: bug, ci, nightly
---

## 🌙 Nightly Build Failed

The nightly build failed on **{{ date | date('YYYY-MM-DD') }}**.

**Workflow Run:** {{ env.WORKFLOW_URL }}

Please investigate and fix the failing tests.

### What to check:
- [ ] New Python version compatibility
- [ ] Dependency updates breaking tests
- [ ] Flaky tests
- [ ] Database compatibility issues