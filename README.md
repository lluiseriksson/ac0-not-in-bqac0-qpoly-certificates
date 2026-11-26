# AC0-BQAC0-SEP-CERT-1.0

Independent zero-floating-point exact algebraic and constructive Lean 4.35.0 companion verification suite for Xiaoming Sun and Jingheng Wang's *"$\mathrm{AC}^0 \not\subseteq \mathrm{BQAC}^0/\mathrm{qpoly}$ via Sublinear-Degree Pauli Approximation"* (`arXiv:2611.34803v1`, November 25, 2026).

## Reproduction
```bash
(cd lean && lake build)
python -m src.ac0_bqac0_sep_verifier certificates
pytest -q
```

## Licenses
- Code, Lean 4 proofs, scripts, and certificates: **MIT** (`LICENSE-CODE`)
- Manuscript and figures: **CC-BY-4.0** (`LICENSE-DOCS`)
