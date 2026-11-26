"""Generate all 16 canonical JSON certificates (C01..C16) for AC0-BQAC0-SEP-CERT-1.0."""

from __future__ import annotations

import json
import pathlib
import sys
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ac0_bqac0_sep_verifier import SCHEMA_VERSION, verify_file

CERTS_DIR = ROOT / "certificates"
CERTS_DIR.mkdir(parents=True, exist_ok=True)


def _r(num: int, den: int = 1) -> list[int]:
    f = Fraction(num, den)
    return [f.numerator, f.denominator]


def _write(filename: str, cert_id: str, mode: str, payload: dict) -> pathlib.Path:
    doc = {"schema_version": SCHEMA_VERSION, "cert_id": cert_id, "mode": mode, "payload": payload}
    out = CERTS_DIR / filename
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> int:
    written: list[pathlib.Path] = []

    # C01..C03: Mode 1a — Disjoint-block monotone universal selector CNF H_n (<= 3n literals, >= 1/(12n) classical adv)
    written.append(_write(
        "C01_universal_cnf_n5_inactive.json", "C01", "universal_selector_cnf_and_advice",
        {"submode": "disjoint_block_universal_cnf", "input_length_n": 5},
    ))
    written.append(_write(
        "C02_universal_cnf_n64_blocks.json", "C02", "universal_selector_cnf_and_advice",
        {"submode": "disjoint_block_universal_cnf", "input_length_n": 64},
    ))
    written.append(_write(
        "C03_universal_cnf_n4096_deep.json", "C03", "universal_selector_cnf_and_advice",
        {"submode": "disjoint_block_universal_cnf", "input_length_n": 4096},
    ))

    # C04..C05: Mode 1b — Exact exhaustive universal selector embedding H_{m,w}(x, y_prog) == F(x)
    written.append(_write(
        "C04_selector_embed_m3_w2.json", "C04", "universal_selector_cnf_and_advice",
        {"submode": "selector_cnf_embedding_and_relevance", "m_vars": 3, "width_w": 2,
         "target_clauses": [[1, 2], [2, 3], [1, 3]]},
    ))
    written.append(_write(
        "C05_selector_embed_m4_w3.json", "C05", "universal_selector_cnf_and_advice",
        {"submode": "selector_cnf_embedding_and_relevance", "m_vars": 4, "width_w": 3,
         "target_clauses": [[1, 2, 3], [2, 3, 4], [1, 4]]},
    ))

    # C06..C08: Mode 2a — Exact rational Chebyshev integer-spectrum filter q(x) + Cor 1.3 maj_3 amplification
    written.append(_write(
        "C06_chebyshev_filter_R8_r1_h4.json", "C06", "pauli_twirling_and_chebyshev_filter",
        {"submode": "chebyshev_integer_filter", "width_N": 12, "cutoff_R": 8, "zero_order_r": 1, "chebyshev_deg_h": 4,
         "approx_eps": _r(1, 100)},
    ))
    written.append(_write(
        "C07_chebyshev_filter_R12_r2_h6.json", "C07", "pauli_twirling_and_chebyshev_filter",
        {"submode": "chebyshev_integer_filter", "width_N": 16, "cutoff_R": 12, "zero_order_r": 2, "chebyshev_deg_h": 6,
         "approx_eps": _r(1, 200)},
    ))
    written.append(_write(
        "C08_chebyshev_filter_R16_r2_h8.json", "C08", "pauli_twirling_and_chebyshev_filter",
        {"submode": "chebyshev_integer_filter", "width_N": 24, "cutoff_R": 16, "zero_order_r": 2, "chebyshev_deg_h": 8,
         "approx_eps": _r(1, 1000)},
    ))

    # C09..C10: Mode 2b — Exact Pauli twirling over P_m (m=2,3) & Thm 1.1 degree exponent separation (d=2,4)
    written.append(_write(
        "C09_pauli_twirl_m2_depth2.json", "C09", "pauli_twirling_and_chebyshev_filter",
        {"submode": "pauli_twirl_and_peeling_budget", "twirl_qubits_m": 2, "circuit_depth_d": 2},
    ))
    written.append(_write(
        "C10_pauli_twirl_m3_depth4.json", "C10", "pauli_twirling_and_chebyshev_filter",
        {"submode": "pauli_twirl_and_peeling_budget", "twirl_qubits_m": 3, "circuit_depth_d": 4},
    ))

    # C11..C12: Mode 3a — Theorem 5.1 state 2-design low-weight Pauli mass & GNW stabilizer gap
    written.append(_write(
        "C11_state_2design_m16_r3.json", "C11", "state_2design_and_nlts_bounds",
        {"submode": "state_2design_and_stabilizer_gap", "num_qubits_m": 16, "pauli_deg_r": 3},
    ))
    written.append(_write(
        "C12_state_2design_m24_r4.json", "C12", "state_2design_and_nlts_bounds",
        {"submode": "state_2design_and_stabilizer_gap", "num_qubits_m": 24, "pauli_deg_r": 4},
    ))

    # C13..C14: Mode 3b — Theorem 5.3 CSS code orthogonality & logical multiplicity 2^b < 2^{k_m}
    # C13: [[7, 1, 3]] Steane CSS code (k_m=1, b=0 -> 1 < 2)
    steane_h = [
        [1, 0, 1, 0, 1, 0, 1],
        [0, 1, 1, 0, 0, 1, 1],
        [0, 0, 0, 1, 1, 1, 1],
    ]
    written.append(_write(
        "C13_css_steane_7_1_3.json", "C13", "state_2design_and_nlts_bounds",
        {"submode": "css_nlts_syndrome_multiplicity", "block_length_m": 7, "M_Z": steane_h, "M_X": steane_h,
         "arbitrary_inputs_b": 0},
    ))
    # C14: [[8, 3, 2]] / [[14, 2, 3]] doubled Steane CSS code (k_m=2, b=1 -> 2 < 4)
    steane2 = [r + [0] * 7 for r in steane_h] + [[0] * 7 + r for r in steane_h]
    written.append(_write(
        "C14_css_doubled_steane_14_2.json", "C14", "state_2design_and_nlts_bounds",
        {"submode": "css_nlts_syndrome_multiplicity", "block_length_m": 14, "M_Z": steane2, "M_X": steane2,
         "arbitrary_inputs_b": 1},
    ))

    # C15..C16: Mode 4 — Section 6 INDEX_{2^k} exact approximate degree k+1 (k=2 on 6 bits, k=3 on 11 bits)
    written.append(_write(
        "C15_index_k2_deg3.json", "C15", "index_function_exact_degree",
        {"address_bits_k": 2},
    ))
    written.append(_write(
        "C16_index_k3_deg4.json", "C16", "index_function_exact_degree",
        {"address_bits_k": 3},
    ))

    for p in written:
        res = verify_file(p)
        print(f"[GEN+PASS] {res['cert_id']} -> {p.name}")
    print(f"Generated and verified {len(written)} certificates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
