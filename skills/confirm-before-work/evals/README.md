# Confirmation Exception Evaluator

This dependency-free evaluator checks that `AGENTS.md` and this skill contain
the same narrow self-maintaining knowledge exception. It also checks allowed
and rejected path/operation cases.

Run from any directory:

```powershell
& 'python' -B `
  '.\evals\validate.py' `
  --cases '.\evals\cases.json'
```

Exit code `0` means all cases and policy markers pass. Exit code `1` lists
missing markers or mismatched cases.


