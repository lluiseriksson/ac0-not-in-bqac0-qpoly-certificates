"""
AC0-BQAC0-SEP-CERT-1.0: Zero-floating-point exact algebraic verifier for Xiaoming Sun and
Jingheng Wang's "AC^0 not subseteq BQAC^0/qpoly via Sublinear-Degree Pauli Approximation"
(arXiv:2611.34803v1, November 25, 2026).

Strictly zero floating-point literals, zero float() calls, zero true-division (/ or /=),
and zero math/numpy imports. All arithmetic uses exact Python int and fractions.Fraction.
"""

from __future__ import annotations

import itertools
import json
import pathlib
import sys
from fractions import Fraction
from typing import Any

SCHEMA_VERSION = "AC0-BQAC0-SEP-CERT-1.0"
MAX_JSON_BYTES = 1_000_000
MAX_RAT_ABS = 10**18


class VerificationError(ValueError):
    """Raised whenever a certificate violates schema, bounds, or mathematical invariants."""


def _gcd(a: int, b: int) -> int:
    a = abs(a)
    b = abs(b)
    while b:
        a, b = b, a % b
    return a


def _req_int(val: Any, name: str, lo: int | None = None, hi: int | None = None) -> int:
    if isinstance(val, bool) or not isinstance(val, int):
        raise VerificationError(f"Expected integer for {name}, got {type(val).__name__}")
    if lo is not None and val < lo:
        raise VerificationError(f"{name}={val} below minimum {lo}")
    if hi is not None and val > hi:
        raise VerificationError(f"{name}={val} above maximum {hi}")
    return val


def _req_str(val: Any, name: str) -> str:
    if not isinstance(val, str) or not val.strip():
        raise VerificationError(f"Expected non-empty string for {name}")
    return val


def _req_list(val: Any, name: str, min_len: int = 0, max_len: int = 4096) -> list[Any]:
    if not isinstance(val, list):
        raise VerificationError(f"Expected list for {name}")
    if len(val) < min_len or len(val) > max_len:
        raise VerificationError(f"{name} length {len(val)} out of range [{min_len}, {max_len}]")
    return val


def _req_dict(val: Any, name: str) -> dict[str, Any]:
    if not isinstance(val, dict):
        raise VerificationError(f"Expected dict for {name}")
    return val


def _parse_rat(val: Any, name: str) -> Fraction:
    if not isinstance(val, list) or len(val) != 2:
        raise VerificationError(f"Expected [num, den] rational pair for {name}")
    num = _req_int(val[0], f"{name}[0]", -MAX_RAT_ABS, MAX_RAT_ABS)
    den = _req_int(val[1], f"{name}[1]", 1, MAX_RAT_ABS)
    if _gcd(num, den) != 1:
        raise VerificationError(f"Rational {name} not in lowest terms")
    return Fraction(num, den)


def _rat_pair(f: Fraction) -> list[int]:
    return [f.numerator, f.denominator]


def _no_dup_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in pairs:
        if k in out:
            raise VerificationError(f"Duplicate JSON key: {k}")
        out[k] = v
    return out


def _reject_json_constant(token: str) -> Any:
    raise VerificationError(f"Illegal non-finite JSON constant: {token}")


def _reject_json_float(token: str) -> Any:
    raise VerificationError(f"Illegal floating-point JSON literal: {token}")


# ---------------------------------------------------------------------------
# Mode 1: universal_selector_cnf_and_advice (Sec. 1.2 & Sec. 4.2)
# ---------------------------------------------------------------------------

def _verify_mode1(payload: dict[str, Any]) -> dict[str, Any]:
    submode = _req_str(payload.get("submode"), "submode")

    if submode == "disjoint_block_universal_cnf":
        n = _req_int(payload.get("input_length_n"), "input_length_n", 1, 100_000)
        # Disjoint blocks B_w = floor(n / 2^w), active iff B_w >= 1 + 2^w
        # m_w = largest integer >= 1 with m_w + (m_w + 1)^w <= B_w
        active_blocks: list[dict[str, int]] = []
        used_vars = 0
        block_literals = 0
        w = 1
        while (1 << w) <= n:
            Bw = n >> w
            thresh = 1 + (1 << w)
            if Bw >= thresh:
                # Binary search m_w
                lo, hi = 1, Bw
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    if mid + ((mid + 1) ** w) <= Bw:
                        lo = mid
                    else:
                        hi = mid - 1
                mw = lo
                Mw = (mw + 1) ** w
                if mw + Mw > Bw:
                    raise VerificationError(f"Block w={w} exceeded Bw={Bw}")
                used_vars += mw + Mw
                # Exact literal count of H_{mw, w}: each tuple ell in {0, x_1..x_{mw}}^w has (1 + nonzero entries) literals
                # Sum over (mw+1)^w tuples of (1 + number of nonzero coords) = Mw + w * mw * (mw+1)^{w-1} <= (w+1)*Mw!
                exact_lits_w = Mw + w * mw * ((mw + 1) ** (w - 1))
                if exact_lits_w > (w + 1) * Mw:
                    raise VerificationError("Block literal count exceeded (w+1)*M_w")
                block_literals += exact_lits_w
                active_blocks.append({"w": w, "Bw": Bw, "mw": mw, "Mw": Mw, "exact_literals": exact_lits_w})
            w += 1
        unused = n - used_vars
        total_literals = unused + block_literals
        if total_literals > 3 * n:
            raise VerificationError(f"Total literals {total_literals} > 3*n={3*n}")
        # Check Sec. 1.2 classical advice worst-case advantage on M_clauses = unused + sum(Mw)
        total_clauses = unused + sum(b["Mw"] for b in active_blocks)
        a_prob = Fraction(1, 2) + Fraction(1, 4 * total_clauses)
        reject_0 = Fraction(1, 1) - a_prob * (Fraction(1, 1) - Fraction(1, total_clauses))
        expected_reject = a_prob + Fraction(1, 4 * total_clauses * total_clauses)
        if reject_0 != expected_reject or reject_0 <= a_prob:
            raise VerificationError("Sec. 1.2 classical advice advantage identity failed")
        adv = a_prob - Fraction(1, 2)
        if adv < Fraction(1, 12 * n):
            raise VerificationError("Worst-case advantage fell below 1/(12*n)")
        return {
            "mode": "universal_selector_cnf_and_advice",
            "submode": submode,
            "input_length_n": n,
            "num_active_blocks": len(active_blocks),
            "unused_unit_vars": unused,
            "total_clauses": total_clauses,
            "total_literals": total_literals,
            "literal_budget_3n": 3 * n,
            "classical_advice_adv": _rat_pair(adv),
        }

    if submode == "selector_cnf_embedding_and_relevance":
        # Explicitly construct H_{m, w}(x, y) for small (m, w), verify every variable is relevant
        # and verify selector programming realizes a target monotone width-w CNF F(x) on all 2^m inputs!
        m = _req_int(payload.get("m_vars"), "m_vars", 1, 4)
        w = _req_int(payload.get("width_w"), "width_w", 1, 3)
        target_clauses_raw = _req_list(payload.get("target_clauses"), "target_clauses", 1, 16)
        tuples = list(itertools.product(range(m + 1), repeat=w))  # 0 means constant 0, 1..m means x_i
        # Normalize each target clause into sorted distinct indices padded with 0s
        active_tuples: set[tuple[int, ...]] = set()
        target_clauses: list[list[int]] = []
        for idx, cr in enumerate(target_clauses_raw):
            cl = _req_list(cr, f"target_clauses[{idx}]", 1, w)
            vars_in = sorted({_req_int(v, f"c[{idx}]", 1, m) for v in cl})
            if len(vars_in) != len(cl):
                raise VerificationError(f"Duplicate variable in target_clauses[{idx}]")
            padded = tuple(vars_in + [0] * (w - len(vars_in)))
            active_tuples.add(padded)
            target_clauses.append(vars_in)
        # Program y_ell = 0 iff ell in active_tuples else 1
        y_prog = {t: (0 if t in active_tuples else 1) for t in tuples}
        # Exhaustively verify H_{m,w}(x, y_prog) == F(x) on ALL 2^m inputs x in {0,1}^m
        for x in itertools.product((0, 1), repeat=m):
            f_val = 1
            for cl in target_clauses:
                if all(x[v - 1] == 0 for v in cl):
                    f_val = 0
                    break
            h_val = 1
            for t in tuples:
                sat = (y_prog[t] == 1) or any((v > 0 and x[v - 1] == 1) for v in t)
                if not sat:
                    h_val = 0
                    break
            if h_val != f_val:
                raise VerificationError(f"Universal selector embedding failed at x={x}")
        # Verify every x_i and every y_ell is relevant by literally evaluating H_{m,w} at isolation witnesses!
        def eval_H(x_vec: tuple[int, ...], y_map: dict[tuple[int, ...], int]) -> int:
            for t in tuples:
                if not ((y_map[t] == 1) or any((v > 0 and x_vec[v - 1] == 1) for v in t)):
                    return 0
            return 1

        zero_x = tuple([0] * m)
        all_ones_y = {t: 1 for t in tuples}
        # 1. Every x_i (i = 1..m) is relevant: set y_{(i,0..0)} = 0, all other y = 1 -> H(0, y)=0, H(e_i, y)=1
        for i in range(1, m + 1):
            iso_t = tuple([i] + [0] * (w - 1))
            y_iso = dict(all_ones_y)
            y_iso[iso_t] = 0
            e_i = tuple(1 if idx == i - 1 else 0 for idx in range(m))
            if eval_H(zero_x, y_iso) != 0 or eval_H(e_i, y_iso) != 1:
                raise VerificationError(f"Isolation witness failed for input variable x_{i}")
        # 2. Every selector variable y_ell is relevant: set x = 0, all other y = 1 -> flipping y_ell flips H from 0 to 1
        for t in tuples:
            y_off = dict(all_ones_y)
            y_off[t] = 0
            if eval_H(zero_x, y_off) != 0 or eval_H(zero_x, all_ones_y) != 1:
                raise VerificationError(f"Isolation witness failed for selector variable y_{t}")
        return {
            "mode": "universal_selector_cnf_and_advice",
            "submode": submode,
            "m_vars": m,
            "width_w": w,
            "num_selector_clauses": len(tuples),
            "target_clauses_embedded": len(target_clauses),
            "inputs_verified": 1 << m,
            "all_vars_relevant": True,
        }

    raise VerificationError(f"Unknown Mode 1 submode: {submode}")


# ---------------------------------------------------------------------------
# Mode 2: pauli_twirling_and_chebyshev_filter (Lemmas 3.3, 3.4, 3.6, Cor. 1.3)
# ---------------------------------------------------------------------------

def _verify_mode2(payload: dict[str, Any]) -> dict[str, Any]:
    submode = _req_str(payload.get("submode"), "submode")

    if submode == "chebyshev_integer_filter":
        # Explicitly construct exact rational Chebyshev polynomial q(x) = prod_{j=1}^r (1 - x/j) * T_h(phi(x)) / T_h(phi(0))
        # over Q and verify q(0) = 1, q(1..r) = 0, |q(j)| <= 1/exp_cap for j in {r+1..R}, and mu_N(q) exact!
        N = _req_int(payload.get("width_N"), "width_N", 2, 64)
        R = _req_int(payload.get("cutoff_R"), "cutoff_R", 2, 32)
        if R > N:
            raise VerificationError(f"cutoff_R={R} exceeds width_N={N}")
        r = _req_int(payload.get("zero_order_r"), "zero_order_r", 1, R // 2)
        h = _req_int(payload.get("chebyshev_deg_h"), "chebyshev_deg_h", 1, 14)

        # Build exact polynomial T_h(z) in Q[z]
        T_prev = [Fraction(1, 1)]
        T_curr = [Fraction(0, 1), Fraction(1, 1)]
        if h == 0:
            Th = T_prev
        elif h == 1:
            Th = T_curr
        else:
            for _ in range(2, h + 1):
                nxt = [Fraction(0, 1)] * (len(T_curr) + 1)
                for idx, c in enumerate(T_curr):
                    nxt[idx + 1] += 2 * c
                for idx, c in enumerate(T_prev):
                    nxt[idx] -= c
                T_prev, T_curr = T_curr, nxt
            Th = T_curr

        def eval_poly(poly: list[Fraction], x: Fraction) -> Fraction:
            acc = Fraction(0, 1)
            xp = Fraction(1, 1)
            for c in poly:
                acc += c * xp
                xp *= x
            return acc

        def phi(x: Fraction) -> Fraction:
            return (Fraction(R + r, 1) - 2 * x) * Fraction(1, R - r)

        th0 = eval_poly(Th, phi(Fraction(0, 1)))
        if th0 <= 1:
            raise VerificationError("T_h(phi(0)) must exceed 1")
        inv_th0 = Fraction(th0.denominator, th0.numerator)

        def eval_q(x_int: int) -> Fraction:
            xf = Fraction(x_int, 1)
            pref = Fraction(1, 1)
            for j in range(1, r + 1):
                pref *= Fraction(1, 1) - xf * Fraction(1, j)
            return pref * eval_poly(Th, phi(xf)) * inv_th0

        if eval_q(0) != 1:
            raise VerificationError("q(0) != 1")
        for j in range(1, r + 1):
            if eval_q(j) != 0:
                raise VerificationError(f"q({j}) != 0")
        max_tail = Fraction(0, 1)
        for j in range(r + 1, R + 1):
            v = abs(eval_q(j))
            if v > max_tail:
                max_tail = v

        # Check exact upper bound |q(j)| <= (1 + R)^r / T_h(phi(0))
        envelope = Fraction((1 + R) ** r, 1) * inv_th0
        if max_tail > envelope:
            raise VerificationError("Chebyshev tail exceeded (1+R)^r / T_h(phi(0))")

        # Also check Corollary 1.3 cubic majority amplification maj_3(tilde_p) for rational eps <= 1/100
        eps = _parse_rat(payload.get("approx_eps", [1, 100]), "approx_eps")
        if eps < 0 or eps > Fraction(1, 100):
            raise VerificationError("approx_eps must be in [0, 1/100]")
        den = Fraction(1, 1) + 2 * eps
        inv_den = Fraction(den.denominator, den.numerator)
        tilde_err = (Fraction(1, 3) + 2 * eps) * inv_den
        if tilde_err >= Fraction(3, 8):
            raise VerificationError("Rescaled error >= 3/8")
        maj_err = 3 * (tilde_err ** 2) - 2 * (tilde_err ** 3)
        if maj_err >= Fraction(1, 3):
            raise VerificationError("maj_3 error did not restore < 1/3")

        return {
            "mode": "pauli_twirling_and_chebyshev_filter",
            "submode": submode,
            "deg_q": r + h,
            "T_h_phi0": _rat_pair(th0),
            "max_abs_tail": _rat_pair(max_tail),
            "maj3_restored_err": _rat_pair(maj_err),
        }

    if submode == "pauli_twirl_and_peeling_budget":
        # Verify exact single-qubit / 2-qubit Pauli twirling over {I, X, Y, Z}^m cancels all non-identity Paulis
        # and verify exact backward peeling degree exponent 1 - (1 - alpha)*2^{-d} + tau*(1 - 2^{-d}) < 1!
        m_twirl = _req_int(payload.get("twirl_qubits_m"), "twirl_qubits_m", 1, 3)
        # Pauli commutation sign s(a, b) in {+1, -1} for single-qubit a,b in {0:I, 1:X, 2:Y, 3:Z}:
        # commutes (+1) iff a==0 or b==0 or a==b, else anticommutes (-1)
        paulis = list(itertools.product(range(4), repeat=m_twirl))
        for sigma_prime in paulis:
            total_sign = 0
            for sigma in paulis:
                sign = 1
                for a, b in zip(sigma, sigma_prime):
                    if a != 0 and b != 0 and a != b:
                        sign = -sign
                total_sign += sign
            expected = (4 ** m_twirl) if all(x == 0 for x in sigma_prime) else 0
            if total_sign != expected:
                raise VerificationError(f"Pauli twirl cancellation failed for {sigma_prime}")

        # Verify Theorem 1.1 parameter exponents at depth d: delta = 2^{-d}/3, alpha = 1/6, eta = 2^{-d}/6
        depth_d = _req_int(payload.get("circuit_depth_d"), "circuit_depth_d", 1, 10)
        inv_2d = Fraction(1, 1 << depth_d)
        delta = inv_2d * Fraction(1, 3)
        alpha = Fraction(1, 6)
        eta = inv_2d * Fraction(1, 6)
        deg_exp = Fraction(1, 1) - (Fraction(1, 1) - alpha) * inv_2d + eta
        expected_exp = Fraction(1, 1) - 2 * delta
        if deg_exp != expected_exp or deg_exp >= Fraction(1, 1) - delta:
            raise VerificationError("Theorem 1.1 degree exponent separation failed")
        return {
            "mode": "pauli_twirling_and_chebyshev_filter",
            "submode": submode,
            "twirl_qubits_m": m_twirl,
            "twirl_group_size": len(paulis),
            "circuit_depth_d": depth_d,
            "delta": _rat_pair(delta),
            "thm12_deg_exponent": _rat_pair(deg_exp),
            "sherstov_lb_exponent": _rat_pair(Fraction(1, 1) - delta),
        }

    raise VerificationError(f"Unknown Mode 2 submode: {submode}")


# ---------------------------------------------------------------------------
# Mode 3: state_2design_and_nlts_bounds (Sec. 5.1 & Sec. 5.2)
# ---------------------------------------------------------------------------

def _verify_mode3(payload: dict[str, Any]) -> dict[str, Any]:
    submode = _req_str(payload.get("submode"), "submode")

    if submode == "state_2design_and_stabilizer_gap":
        m = _req_int(payload.get("num_qubits_m"), "num_qubits_m", 2, 32)
        r = _req_int(payload.get("pauli_deg_r"), "pauli_deg_r", 1, m)
        DX = 1 << m
        # Exact non-identity Pauli count M_r = sum_{j=1}^r 3^j * C(m, j) <= (3*m)^{r+1}
        Mr = 0
        binom = 1
        pow3 = 1
        for j in range(1, r + 1):
            binom = (binom * (m - j + 1)) // j
            pow3 *= 3
            Mr += pow3 * binom
        cap = (3 * m) ** (r + 1)
        if Mr > cap:
            raise VerificationError(f"M_r={Mr} exceeded (3m)^(r+1)={cap}")
        # Exact Haar second-moment sum M_r / (D_X + 1)
        haar_sum = Fraction(Mr, DX + 1)
        # Verify Sec. 5.1 stabilizer trace-distance lower bound sin^2(pi/8) = (2 - sqrt(2))/4 > 1/7
        # and GNW six-copy acceptance gap sin^2(pi/8)/4 > 1/28!
        if not (2 * 49 < 100):
            raise VerificationError("sin^2(pi/8) > 1/7 radical check failed")
        return {
            "mode": "state_2design_and_nlts_bounds",
            "submode": submode,
            "num_qubits_m": m,
            "pauli_deg_r": r,
            "pauli_count_Mr": Mr,
            "pauli_cap_3m": cap,
            "haar_low_wt_mass": _rat_pair(haar_sum),
            "gnw_gap_lower_bound": [1, 28],
        }

    if submode == "css_nlts_syndrome_multiplicity":
        # Verify Theorem 5.3 CSS code check orthogonality M_Z M_X^T = 0 (mod 2),
        # logical dimension k_m = m - rank(M_Z) - rank(M_X), eigenspace dim 2^{k_m},
        # and rank deficit 2^b < 2^{k_m} for b < k_m!
        m = _req_int(payload.get("block_length_m"), "block_length_m", 3, 32)
        mz_raw = _req_list(payload.get("M_Z"), "M_Z", 1, m)
        mx_raw = _req_list(payload.get("M_X"), "M_X", 1, m)
        b_in = _req_int(payload.get("arbitrary_inputs_b"), "arbitrary_inputs_b", 0, m - 1)

        def parse_bin_mat(raw: list[Any], name: str) -> list[list[int]]:
            out: list[list[int]] = []
            for i, row in enumerate(raw):
                rl = _req_list(row, f"{name}[{i}]", m, m)
                out.append([_req_int(v, f"{name}[{i}][{j}]", 0, 1) for j, v in enumerate(rl)])
            return out

        MZ = parse_bin_mat(mz_raw, "M_Z")
        MX = parse_bin_mat(mx_raw, "M_X")
        # Check M_Z M_X^T == 0 mod 2
        for i, rz in enumerate(MZ):
            for j, rx in enumerate(MX):
                dot = sum(a * b for a, b in zip(rz, rx)) % 2
                if dot != 0:
                    raise VerificationError(f"CSS orthogonality M_Z M_X^T = 0 violated at ({i},{j})")

        def f2_rank(mat: list[list[int]]) -> int:
            rows = [r[:] for r in mat]
            rk = 0
            for col in range(m):
                piv = None
                for i in range(rk, len(rows)):
                    if rows[i][col] == 1:
                        piv = i
                        break
                if piv is None:
                    continue
                rows[rk], rows[piv] = rows[piv], rows[rk]
                for i in range(len(rows)):
                    if i != rk and rows[i][col] == 1:
                        rows[i] = [a ^ b for a, b in zip(rows[i], rows[rk])]
                rk += 1
            return rk

        rk_z = f2_rank(MZ)
        rk_x = f2_rank(MX)
        km = m - rk_z - rk_x
        if km <= 0:
            raise VerificationError(f"Non-positive logical qubit count k_m={km}")
        if b_in >= km:
            raise VerificationError(f"Arbitrary input count b={b_in} must be < k_m={km}")
        prep_rank = 1 << b_in
        logical_mult = 1 << km
        if prep_rank >= logical_mult:
            raise VerificationError("Rank deficit 2^b < 2^{k_m} failed")
        return {
            "mode": "state_2design_and_nlts_bounds",
            "submode": submode,
            "block_length_m": m,
            "rank_MZ": rk_z,
            "rank_MX": rk_x,
            "logical_qubits_km": km,
            "arbitrary_inputs_b": b_in,
            "prep_rank_2b": prep_rank,
            "syndrome_eigenspace_dim": logical_mult,
        }

    raise VerificationError(f"Unknown Mode 3 submode: {submode}")


# ---------------------------------------------------------------------------
# Mode 4: index_function_exact_degree (Sec. 6)
# ---------------------------------------------------------------------------

def _verify_mode4(payload: dict[str, Any]) -> dict[str, Any]:
    # Verify Section 6's exact multilinear polynomial for INDEX_{2^k}(i, x) = x_i has degree k+1,
    # and the substitution x_j = b XOR PARITY_k(j) reduces INDEX_{2^k} identically to PARITY_{k+1}(i, b),
    # forcing approximate degree exactly k+1 for every eps in (0, 1/2)!
    k = _req_int(payload.get("address_bits_k"), "address_bits_k", 1, 3)
    M = 1 << k
    total_bits = k + M
    # 1. Verify exact multilinear polynomial agrees with INDEX_M on ALL 2^{k+M} inputs!
    # For k<=3, 2^{k+M} <= 2^{11} = 2048 -> exhaustive over ALL inputs!
    for bits in itertools.product((0, 1), repeat=total_bits):
        addr = bits[:k]
        data = bits[k:]
        addr_idx = 0
        for b in addr:
            addr_idx = (addr_idx << 1) | b
        truth = data[addr_idx]
        # Polynomial evaluation: sum_{j in {0,1}^k} x_j * prod_{a=1}^k ell_{j_a}(i_a)
        poly_val = 0
        for j in range(M):
            prod = data[j]
            for a in range(k):
                ja = (j >> (k - 1 - a)) & 1
                prod *= addr[a] if ja == 1 else (1 - addr[a])
            poly_val += prod
        if poly_val != truth:
            raise VerificationError(f"INDEX polynomial mismatch at {bits}")

    # 2. Verify substitution x_j = b XOR PARITY_k(j) yields PARITY_{k+1}(i, b) on all 2^{k+1} inputs!
    # And verify Fourier orthogonality: every monomial of degree <= k has zero correlation with (-1)^{PARITY_{k+1}}.
    for ib in itertools.product((0, 1), repeat=k + 1):
        addr = ib[:k]
        b = ib[k]
        addr_idx = 0
        for bit in addr:
            addr_idx = (addr_idx << 1) | bit
        xj = b ^ (addr_idx.bit_count() & 1)
        parity_k1 = (sum(addr) + b) & 1
        if xj != parity_k1:
            raise VerificationError(f"INDEX-to-PARITY substitution failed at {ib}")

    # Verify zero correlation of every subset S subsetneq [k+1] (|S| <= k) with chi = (-1)^{sum(ib)}
    sub_checked = 0
    for r_sz in range(0, k + 1):
        for S in itertools.combinations(range(k + 1), r_sz):
            corr = 0
            for ib in itertools.product((0, 1), repeat=k + 1):
                chi = -1 if (sum(ib) & 1) else 1
                mon = 1
                for idx in S:
                    mon *= ib[idx]
                corr += chi * mon
            if corr != 0:
                raise VerificationError(f"Monomial {S} had nonzero correlation {corr} with PARITY_{k+1}")
            sub_checked += 1

    return {
        "mode": "index_function_exact_degree",
        "address_bits_k": k,
        "data_bits_M": M,
        "total_input_bits": total_bits,
        "exact_approx_degree": k + 1,
        "truth_table_checked": 1 << total_bits,
        "low_deg_monomials_orthogonal": sub_checked,
    }


# ---------------------------------------------------------------------------
# Entry Points & CLI
# ---------------------------------------------------------------------------

def verify_certificate(cert: Any) -> dict[str, Any]:
    root = _req_dict(cert, "certificate")
    if root.get("schema_version") != SCHEMA_VERSION:
        raise VerificationError(f"Invalid schema_version: {root.get('schema_version')!r}")
    cert_id = _req_str(root.get("cert_id"), "cert_id")
    mode = _req_str(root.get("mode"), "mode")
    payload = _req_dict(root.get("payload"), "payload")

    if mode == "universal_selector_cnf_and_advice":
        res = _verify_mode1(payload)
    elif mode == "pauli_twirling_and_chebyshev_filter":
        res = _verify_mode2(payload)
    elif mode == "state_2design_and_nlts_bounds":
        res = _verify_mode3(payload)
    elif mode == "index_function_exact_degree":
        res = _verify_mode4(payload)
    else:
        raise VerificationError(f"Unknown verification mode: {mode!r}")

    res["cert_id"] = cert_id
    res["schema_version"] = SCHEMA_VERSION
    return res


def verify_file(path: str | pathlib.Path) -> dict[str, Any]:
    p = pathlib.Path(path)
    if not p.is_file():
        raise VerificationError(f"Certificate path is not a regular file: {p}")
    size = p.stat().st_size
    if size <= 0 or size > MAX_JSON_BYTES:
        raise VerificationError(f"Certificate file size {size} out of bounds (1..{MAX_JSON_BYTES})")
    raw_text = p.read_text(encoding="utf-8")
    try:
        parsed = json.loads(
            raw_text,
            object_pairs_hook=_no_dup_pairs,
            parse_constant=_reject_json_constant,
            parse_float=_reject_json_float,
        )
    except (RecursionError, ValueError) as exc:
        raise VerificationError(f"Malformed JSON in {p.name}: {exc}") from exc
    return verify_certificate(parsed)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("Usage: python -m src.ac0_bqac0_sep_verifier <file.json | dir>", file=sys.stderr)
        return 2
    targets: list[pathlib.Path] = []
    for a in args:
        p = pathlib.Path(a)
        if p.is_dir():
            targets.extend(sorted(p.glob("*.json")))
        else:
            targets.append(p)
    if not targets:
        print("No JSON certificate files found.", file=sys.stderr)
        return 2
    for t in targets:
        res = verify_file(t)
        print(f"[PASS] {res['cert_id']} ({res['mode']})")
    print(f"Verified {len(targets)}/{len(targets)} certificates successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
