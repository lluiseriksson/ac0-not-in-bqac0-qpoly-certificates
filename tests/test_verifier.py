"""Unit, forgery, AST zero-float, and exact algebraic tests for AC0-BQAC0-SEP-CERT-1.0."""

from __future__ import annotations

import ast
import copy
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import ac0_bqac0_sep_verifier as V

CERTS_DIR = ROOT / "certificates"


def _load(name: str) -> dict:
    return json.loads((CERTS_DIR / name).read_text(encoding="utf-8"))


def test_ast_zero_float_and_no_forbidden_imports() -> None:
    src_path = ROOT / "src" / "ac0_bqac0_sep_verifier.py"
    tree = ast.parse(src_path.read_text(encoding="utf-8"), filename=str(src_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            pytest.fail(f"Forbidden float literal {node.value!r} at line {node.lineno}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "float":
            pytest.fail(f"Forbidden float() call at line {node.lineno}")
        if isinstance(node, ast.Div):
            pytest.fail(f"Forbidden true-division operator / at line {node.lineno}")
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Div):
            pytest.fail(f"Forbidden true-division /= at line {node.lineno}")
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in {"math", "numpy", "scipy", "decimal"}
        if isinstance(node, ast.ImportFrom):
            assert node.module not in {"math", "numpy", "scipy", "decimal"}


@pytest.mark.parametrize("cert_path", sorted(CERTS_DIR.glob("*.json")), ids=lambda p: p.name)
def test_all_16_canonical_certificates_pass(cert_path: pathlib.Path) -> None:
    res = V.verify_file(cert_path)
    assert res["schema_version"] == V.SCHEMA_VERSION
    assert res["cert_id"].startswith("C")


def test_key_exact_metrics() -> None:
    r01 = V.verify_file(CERTS_DIR / "C01_universal_cnf_n5_inactive.json")
    assert r01["num_active_blocks"] == 0 and r01["total_literals"] == 5
    r03 = V.verify_file(CERTS_DIR / "C03_universal_cnf_n4096_deep.json")
    assert r03["total_literals"] <= 3 * 4096 and r03["num_active_blocks"] >= 4
    r09 = V.verify_file(CERTS_DIR / "C09_pauli_twirl_m2_depth2.json")
    assert r09["twirl_group_size"] == 16 and r09["thm12_deg_exponent"] == [5, 6]
    r14 = V.verify_file(CERTS_DIR / "C14_css_doubled_steane_14_2.json")
    assert r14["logical_qubits_km"] == 2 and r14["syndrome_eigenspace_dim"] == 4
    r16 = V.verify_file(CERTS_DIR / "C16_index_k3_deg4.json")
    assert r16["exact_approx_degree"] == 4 and r16["truth_table_checked"] == 2048


# Adversarial forgery tests
def test_reject_float_and_dup_json(tmp_path: pathlib.Path) -> None:
    p1 = tmp_path / "f.json"
    p1.write_text('{"x": 0.5}', encoding="utf-8")
    with pytest.raises(V.VerificationError, match="floating-point"):
        V.verify_file(p1)
    p2 = tmp_path / "d.json"
    p2.write_text('{"a": 1, "a": 2}', encoding="utf-8")
    with pytest.raises(V.VerificationError, match="Duplicate"):
        V.verify_file(p2)


def test_reject_non_orthogonal_css() -> None:
    c = _load("C13_css_steane_7_1_3.json")
    c["payload"]["M_X"][0][0] = 0  # breaks M_Z M_X^T = 0 mod 2
    with pytest.raises(V.VerificationError, match="CSS orthogonality"):
        V.verify_certificate(c)


def test_reject_b_ge_km_in_nlts() -> None:
    c = _load("C13_css_steane_7_1_3.json")
    c["payload"]["arbitrary_inputs_b"] = 1  # == k_m
    with pytest.raises(V.VerificationError, match="must be < k_m"):
        V.verify_certificate(c)


def test_reject_eps_above_1_100() -> None:
    c = _load("C06_chebyshev_filter_R8_r1_h4.json")
    c["payload"]["approx_eps"] = [1, 50]
    with pytest.raises(V.VerificationError, match="1/100"):
        V.verify_certificate(c)


def test_reject_cutoff_R_exceeds_width_N() -> None:
    c = _load("C06_chebyshev_filter_R8_r1_h4.json")
    c["payload"]["width_N"] = 4  # < cutoff_R = 8
    with pytest.raises(V.VerificationError, match="exceeds width_N"):
        V.verify_certificate(c)


def test_reject_dup_var_in_clause() -> None:
    c = _load("C04_selector_embed_m3_w2.json")
    c["payload"]["target_clauses"] = [[1, 1]]
    with pytest.raises(V.VerificationError, match="Duplicate variable"):
        V.verify_certificate(c)


def test_reject_wrong_schema_mode_and_file_guards(tmp_path: pathlib.Path) -> None:
    bad = copy.deepcopy(_load("C01_universal_cnf_n5_inactive.json"))
    bad["schema_version"] = "BAD"
    with pytest.raises(V.VerificationError, match="schema_version"):
        V.verify_certificate(bad)
    bad["schema_version"] = V.SCHEMA_VERSION
    bad["mode"] = "bogus"
    with pytest.raises(V.VerificationError, match="Unknown verification mode"):
        V.verify_certificate(bad)
    with pytest.raises(V.VerificationError, match="regular file"):
        V.verify_file(tmp_path)
    big = tmp_path / "big.json"
    big.write_bytes(b" " * (V.MAX_JSON_BYTES + 1))
    with pytest.raises(V.VerificationError, match="size"):
        V.verify_file(big)
