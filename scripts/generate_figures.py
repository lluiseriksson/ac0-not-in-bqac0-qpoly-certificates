"""Generate the 3 publication-grade figures for paper82-ac0-not-in-bqac0-qpoly-certificates from live exact outputs."""

from __future__ import annotations

import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ac0_bqac0_sep_verifier import verify_file

CERTS_DIR = ROOT / "certificates"
FIG_DIR = ROOT / "paper" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9.5,
    "axes.titlesize": 10.5,
    "axes.labelsize": 9.5,
    "legend.fontsize": 7.6,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "figure.dpi": 240,
})


def _f(pair: list[int]) -> float:
    return pair[0] / pair[1]


def fig1_peeling_exponent_and_chebyshev() -> None:
    """Figure 1: (a) Exact Thm 1.1 degree exponent separation vs depth d; (b) Live Chebyshev filter tail suppression."""
    r06 = verify_file(CERTS_DIR / "C06_chebyshev_filter_R8_r1_h4.json")
    r07 = verify_file(CERTS_DIR / "C07_chebyshev_filter_R12_r2_h6.json")
    r08 = verify_file(CERTS_DIR / "C08_chebyshev_filter_R16_r2_h8.json")
    r09 = verify_file(CERTS_DIR / "C09_pauli_twirl_m2_depth2.json")
    r10 = verify_file(CERTS_DIR / "C10_pauli_twirl_m3_depth4.json")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.6, 3.6))

    ds = [1, 2, 3, 4, 5, 6]
    deg_ub = [1.0 - (2.0 / 3.0) * (2.0 ** (-d)) for d in ds]
    sherstov_lb = [1.0 - (1.0 / 3.0) * (2.0 ** (-d)) for d in ds]
    ax1.plot(ds, sherstov_lb, marker="s", color="#b2182b", lw=2.0, label=r"Sherstov $\mathrm{AC}^0$ lower bound $1 - \delta(d)$")
    ax1.plot(ds, deg_ub, marker="o", color="#2166ac", lw=2.0, label=r"Thm. 1.2 $\mathrm{BQAC}^0/\mathrm{qpoly}$ cap $1 - 2\delta(d)$")
    ax1.fill_between(ds, deg_ub, sherstov_lb, color="#fddbc7", alpha=0.5, label=r"Exact separation gap $\delta(d) = 2^{-d}/3$")
    ax1.scatter([2, 4], [_f(r09["thm12_deg_exponent"]), _f(r10["thm12_deg_exponent"])],
                color="#1b7837", s=65, zorder=6, label="Live certified C09 ($d=2$), C10 ($d=4$)")
    ax1.set_xticks(ds)
    ax1.set_ylim(0.55, 1.08)
    ax1.set_xlabel("Quantum circuit depth $d$")
    ax1.set_ylabel("Sublinear degree exponent")
    ax1.set_title(r"(a) Exact Degree-Exponent Separation ($\delta = 2^{-d}/3$)")
    ax1.legend(loc="lower right", frameon=True, framealpha=0.93, fontsize=7.1)
    ax1.grid(alpha=0.22)

    # Panel (b): Live Chebyshev filter max_abs_tail and maj_3 restored error
    labels = ["C06\n($R=8,h=4$)", "C07\n($R=12,h=6$)", "C08\n($R=16,h=8$)"]
    tails = [_f(r06["max_abs_tail"]), _f(r07["max_abs_tail"]), _f(r08["max_abs_tail"])]
    errs = [_f(r06["maj3_restored_err"]), _f(r07["maj3_restored_err"]), _f(r08["maj3_restored_err"])]
    x = list(range(3))
    w = 0.34
    b1 = ax2.bar([i - w / 2 for i in x], tails, width=w, color="#4393c3", label=r"Max Chebyshev tail $\max|q(j)|$")
    b2 = ax2.bar([i + w / 2 for i in x], errs, width=w, color="#1b7837", label=r"Cor. 1.3 $\mathrm{maj}_3$ restored error")
    ax2.axhline(1.0 / 3.0, color="#b2182b", lw=1.4, ls="--", label="Target error cap $1/3$")
    for idx_s, bars in enumerate((b1, b2)):
        for bar in bars:
            v = bar.get_height()
            if idx_s == 1:
                ax2.text(bar.get_x() + bar.get_width() / 2.0, v - 0.025, f"{v:.3f}",
                         ha="center", va="top", fontsize=7.6, color="white", fontweight="bold")
            else:
                ax2.text(bar.get_x() + bar.get_width() / 2.0, v + 0.02, f"{v:.3f}", ha="center", va="bottom", fontsize=7.6)
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.set_ylim(0.0, 1.02)
    ax2.set_ylabel("Exact rational value")
    ax2.set_title(r"(b) Live Chebyshev Filter Tails & $\mathrm{maj}_3$ Amplification")
    ax2.legend(loc="upper right", frameon=True, framealpha=0.93, fontsize=7.1)
    ax2.grid(axis="y", alpha=0.22)

    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig1_degree_separation_and_chebyshev.png")
    plt.close(fig)


def fig2_universal_cnf_and_index() -> None:
    """Figure 2: (a) Linear-size monotone universal selector CNF literal budget vs 3n cap; (b) Exact INDEX_{2^k} degree."""
    r01 = verify_file(CERTS_DIR / "C01_universal_cnf_n5_inactive.json")
    r02 = verify_file(CERTS_DIR / "C02_universal_cnf_n64_blocks.json")
    r03 = verify_file(CERTS_DIR / "C03_universal_cnf_n4096_deep.json")
    r15 = verify_file(CERTS_DIR / "C15_index_k2_deg3.json")
    r16 = verify_file(CERTS_DIR / "C16_index_k3_deg4.json")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.6, 3.55))

    # Panel (a): Normalized literal density L(H_n)/n <= 3 across C01, C02, C03
    cats = ["C01\n($n=5$)", "C02\n($n=64$)", "C03\n($n=4096$)"]
    dens = [
        r01["total_literals"] / r01["input_length_n"],
        r02["total_literals"] / r02["input_length_n"],
        r03["total_literals"] / r03["input_length_n"],
    ]
    cls_dens = [
        r01["total_clauses"] / r01["input_length_n"],
        r02["total_clauses"] / r02["input_length_n"],
        r03["total_clauses"] / r03["input_length_n"],
    ]
    x = list(range(3))
    w = 0.34
    b1 = ax1.bar([i - w / 2 for i in x], dens, width=w, color="#2166ac", label=r"Literal ratio $|H_n|/n \leq 3$")
    b2 = ax1.bar([i + w / 2 for i in x], cls_dens, width=w, color="#fd8d3c", label=r"Clause ratio $M(H_n)/n$")
    ax1.axhline(3.0, color="#b2182b", lw=1.5, ls="--", label="Linear-size budget $3n$ (Sec. 4.2)")
    for bars in (b1, b2):
        for bar in bars:
            v = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width() / 2.0, v + 0.08, f"{v:.2f}", ha="center", va="bottom", fontsize=7.6)
    ax1.set_xticks(x)
    ax1.set_xticklabels(cats)
    ax1.set_ylim(0.0, 3.85)
    ax1.set_ylabel("Count normalized by input length $n$")
    ax1.set_title("(a) Linear-Size Monotone Universal Selector CNF")
    ax1.legend(loc="upper left", frameon=True, framealpha=0.93, fontsize=7.2)
    ax1.grid(axis="y", alpha=0.22)

    # Panel (b): Exact approximate degree of INDEX_{2^k} (k+1) vs input length n = 2^k + k
    ks = [1, 2, 3, 4, 5, 6]
    ns = [2**k + k for k in ks]
    degs = [k + 1 for k in ks]
    ax2.plot(ks, ns, marker="s", color="#7570b3", lw=1.9, label=r"Total input length $n = 2^k + k$")
    ax2.plot(ks, degs, marker="o", color="#1b7837", lw=2.1, label=r"Exact approx. degree $\widetilde{\deg}(\mathrm{INDEX}_{2^k}) = k+1$")
    ax2.scatter([2, 3], [r15["exact_approx_degree"], r16["exact_approx_degree"]],
                color="#d95f02", s=75, zorder=6, label="Exhaustive truth-table C15 ($64$), C16 ($2048$)")
    ax2.set_yscale("log")
    ax2.set_xticks(ks)
    ax2.set_ylim(1.5, 160)
    ax2.set_xlabel("Address bit width $k$")
    ax2.set_ylabel("Exact integer count (log scale)")
    ax2.set_title(r"(b) Exponential Gap: $\mathrm{INDEX}_{2^k}$ Degree $k+1$ vs. $2^k+k$")
    ax2.legend(loc="upper left", frameon=True, framealpha=0.93, fontsize=7.1)
    ax2.grid(True, which="both", alpha=0.2)

    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig2_universal_cnf_and_index.png")
    plt.close(fig)


def fig3_state_2design_and_nlts() -> None:
    """Figure 3: (a) State 2-design low-weight Pauli mass decay (Thm 5.1); (b) NLTS CSS logical multiplicity gap (Thm 5.3)."""
    r11 = verify_file(CERTS_DIR / "C11_state_2design_m16_r3.json")
    r12 = verify_file(CERTS_DIR / "C12_state_2design_m24_r4.json")
    r13 = verify_file(CERTS_DIR / "C13_css_steane_7_1_3.json")
    r14 = verify_file(CERTS_DIR / "C14_css_doubled_steane_14_2.json")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.6, 3.55))

    # Panel (a): Low-weight Pauli mass M_r / (2^m + 1) vs qubit count m at r=3,4
    ms = [12, 16, 20, 24, 28]
    def comb(n: int, k: int) -> int:
        res = 1
        for i in range(1, k + 1):
            res = res * (n - i + 1) // i
        return res
    mass_r3 = [sum(comb(m, j) * (3**j) for j in range(1, 4)) / (2**m + 1) for m in ms]
    mass_r4 = [sum(comb(m, j) * (3**j) for j in range(1, 5)) / (2**m + 1) for m in ms]
    ax1.semilogy(ms, mass_r3, marker="o", color="#2166ac", lw=2.0, label=r"Degree $r=3$ Haar mass $M_3/(2^m+1)$")
    ax1.semilogy(ms, mass_r4, marker="s", color="#d95f02", lw=2.0, label=r"Degree $r=4$ Haar mass $M_4/(2^m+1)$")
    ax1.scatter([16, 24], [_f(r11["haar_low_wt_mass"]), _f(r12["haar_low_wt_mass"])],
                color="#1b7837", s=85, zorder=6, label="Live certified C11 ($m=16$), C12 ($m=24$)")
    ax1.set_xticks(ms)
    ax1.set_ylim(1e-5, 2e1)
    ax1.set_xlabel("State register qubits $m$")
    ax1.set_ylabel("Exact low-weight Pauli mass (log)")
    ax1.set_title("(a) State 2-Design Low-Weight Pauli Decay (Thm. 5.1)")
    ax1.legend(loc="upper right", frameon=True, framealpha=0.93, fontsize=7.1)
    ax1.grid(True, which="both", alpha=0.2)

    # Panel (b): NLTS logical multiplicity 2^{k_m} vs prep rank 2^b across C13 (Steane) and C14 (Doubled Steane)
    cats = ["C13: [[7,1,3]]\nSteane ($b=0, k_m=1$)", "C14: [[14,2,3]]\nDoubled ($b=1, k_m=2$)"]
    prep_r = [r13["prep_rank_2b"], r14["prep_rank_2b"]]
    eig_d = [r13["syndrome_eigenspace_dim"], r14["syndrome_eigenspace_dim"]]
    x = list(range(2))
    w = 0.32
    b1 = ax2.bar([i - w / 2 for i in x], prep_r, width=w, color="#fc8d59", label=r"Ancilla prep rank $2^b$")
    b2 = ax2.bar([i + w / 2 for i in x], eig_d, width=w, color="#1b7837", label=r"Syndrome eigenspace dim $2^{k_m}$")
    for bars in (b1, b2):
        for bar in bars:
            v = int(bar.get_height())
            ax2.text(bar.get_x() + bar.get_width() / 2.0, v + 0.12, str(v), ha="center", va="bottom", fontsize=8.0)
    ax2.set_xticks(x)
    ax2.set_xticklabels(cats)
    ax2.set_ylim(0, 5.4)
    ax2.set_ylabel("Exact subspace dimension")
    ax2.set_title(r"(b) CSS Logical Multiplicity Obstruction $2^b < 2^{k_m}$")
    ax2.legend(loc="upper left", frameon=True, framealpha=0.93, fontsize=7.4)
    ax2.grid(axis="y", alpha=0.22)

    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig3_state_2design_and_nlts.png")
    plt.close(fig)


def main() -> int:
    fig1_peeling_exponent_and_chebyshev()
    fig2_universal_cnf_and_index()
    fig3_state_2design_and_nlts()
    print(f"Generated 3 figures in {FIG_DIR}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
