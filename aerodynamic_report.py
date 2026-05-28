"""
Dark Wing Project — MÓDULO DE RELATÓRIO AERODINÂMICO
Sadraey (2013) + LLT (Lifting Line Theory) + ISA/Sutherland

Substitui os antigos módulos:
  • atmosfera.py        → funções ISA + Sutherland incorporadas
  • analise_multi_temp  → análise paramétrica via Sadraey+LLT

Exporta:
  • calcular_atmosfera_isa()  — compatibilidade com calculos.py
  • calcular_rho_simples()    — compatibilidade com gui.py
  • generate_report()         — relatório texto Sadraey+LLT
  • plotar_analise_sadraey()  — visualizações salvas como imagens (substitui heatmaps)
  • extrair_dados_perfil()    — integração com database.py
"""

import os
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO: pasta Reports (auto-criada se ausente ou deletada)
# ═══════════════════════════════════════════════════════════════════════════════
_BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(_BASE_DIR, "Reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _save_path(filename):
    """Retorna caminho completo na pasta Reports, criando-a se necessário."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return os.path.join(OUTPUT_DIR, filename)


# ═══════════════════════════════════════════════════════════════════════════════
# PARTE 1: ATMOSFERA (ISA + Sutherland) — migrado de atmosfera.py
# ═══════════════════════════════════════════════════════════════════════════════

R_AIR = 287.05
GAMMA = 1.4
G_STD = 9.80665
T0_ISA = 288.15
P0_ISA = 101325.0
L_RATE = 0.0065

MU_0 = 1.716e-5
T_0_SUTH = 273.15
S_SUTH = 110.4


def calcular_atmosfera_isa(altitude_m, temp_C=None):
    """Calculate atmospheric properties using ISA model."""
    h = float(altitude_m)
    T_isa_K = T0_ISA - L_RATE * h
    T_isa_C = T_isa_K - 273.15

    if temp_C is not None:
        T_C = float(temp_C)
        T_K = T_C + 273.15
    else:
        T_C = T_isa_C
        T_K = T_isa_K

    if h <= 11000:
        P_Pa = P0_ISA * (1 - L_RATE * h / T0_ISA) ** (G_STD / (R_AIR * L_RATE))
    else:
        P_tropo = P0_ISA * (1 - L_RATE * 11000 / T0_ISA) ** (G_STD / (R_AIR * L_RATE))
        T_tropo = T0_ISA - L_RATE * 11000
        P_Pa = P_tropo * np.exp(-G_STD * (h - 11000) / (R_AIR * T_tropo))

    rho = P_Pa / (R_AIR * T_K)
    mu = MU_0 * (T_K / T_0_SUTH) ** 1.5 * (T_0_SUTH + S_SUTH) / (T_K + S_SUTH)
    v_som = np.sqrt(GAMMA * R_AIR * T_K)

    return {
        "h_m": h, "T_C": T_C, "T_K": T_K, "P_Pa": P_Pa,
        "rho": rho, "mu": mu, "v_som": v_som,
        "T_isa_C": T_isa_C, "delta_T": T_C - T_isa_C,
    }


def calcular_rho_simples(altitude_m, temp_C=15.0):
    """Simplified rho calculation for GUI display."""
    atm = calcular_atmosfera_isa(altitude_m, temp_C)
    return atm["rho"]


# ═══════════════════════════════════════════════════════════════════════════════
# PARTE 1b: INTEGRAÇÃO COM DATABASE — extração de dados do perfil
# ═══════════════════════════════════════════════════════════════════════════════

def extrair_dados_perfil(nome_perfil, re_alvo=100000):
    """
    Extrai dados aerodinâmicos do perfil a partir do database.py.
    """
    try:
        from database import DATABASE, CL_MAX_2D, CD0_PERFIL

        if nome_perfil not in DATABASE:
            print(f"  [AVISO] Perfil '{nome_perfil}' não encontrado no database. Usando defaults.")
            return _defaults_perfil()

        dados_re = DATABASE[nome_perfil]
        res_sorted = sorted(dados_re.keys())

        if len(res_sorted) == 1:
            coefs = np.array(dados_re[res_sorted[0]], dtype=float)
        else:
            x = np.log10(float(re_alvo))
            xs = np.log10(np.array(res_sorted, dtype=float))

            if x <= xs[0]:
                i0, i1 = 0, 1
            elif x >= xs[-1]:
                i0, i1 = len(xs) - 2, len(xs) - 1
            else:
                i1 = int(np.searchsorted(xs, x))
                i0 = i1 - 1

            x0, x1 = xs[i0], xs[i1]
            v0 = np.array(dados_re[res_sorted[i0]], dtype=float)
            v1 = np.array(dados_re[res_sorted[i1]], dtype=float)
            coefs = v0 + (x - x0) * (v1 - v0) / (x1 - x0)

        a0_2d_deg = float(coefs[0])
        a0_2d_rad = a0_2d_deg * 57.2958

        alpha0_af = float(coefs[1])
        cd0_af = float(coefs[2])
        cm0_af = float(coefs[3])
        xcp0_af = float(coefs[4])

        clmax_af = CL_MAX_2D.get(nome_perfil, 1.65)
        cd0_database = CD0_PERFIL.get(nome_perfil, cd0_af)

        return {
            "cla_af": a0_2d_rad,
            "alpha0_af": alpha0_af,
            "clmax_af": clmax_af,
            "cd0_af": cd0_database,
            "cm0_af": cm0_af,
            "xcp0_af": xcp0_af,
            "a0_2d_deg": a0_2d_deg,
            "re_interp": re_alvo,
            "fonte": f"database.py (Re={res_sorted[0]}–{res_sorted[-1]})"
        }

    except Exception as e:
        print(f"  [AVISO] Erro ao extrair dados do perfil: {e}")
        return _defaults_perfil()


def _defaults_perfil():
    """Valores default quando perfil não está no database."""
    return {
        "cla_af": 5.65,
        "alpha0_af": -4.0,
        "clmax_af": 1.65,
        "cd0_af": 0.012,
        "cm0_af": -0.10,
        "xcp0_af": 0.30,
        "a0_2d_deg": 0.10,
        "re_interp": 100000,
        "fonte": "valores default"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PARTE 2: SADRAEY + LLT — Metodologia principal
# ═══════════════════════════════════════════════════════════════════════════════

def eficiencia_oswald_sadraey(RA):
    """Eficiência de Oswald via aproximação de Sadraey (2013)."""
    e = 1.78 * (1 - 0.045 * RA**0.68) - 0.64
    return float(np.clip(e, 0.60, 0.95))


def delta_glauert(RA):
    """Fator de correção δ da distribuição de sustentação (Glauert)."""
    return 0.0175 * (RA - 1.0) / RA


def e_oswald_glauert(RA):
    """e de Oswald corrigido por δ (distribuição elíptica perturbada)."""
    delta = delta_glauert(RA)
    e = 1.0 / (1.0 + delta)
    return float(np.clip(e, 0.60, 1.0))


def wing_3d_slope(Cla_2d_rad, RA, e_ow):
    """Inclinação 3D da curva de sustentação (Prandtl LLLT)."""
    return Cla_2d_rad / (1.0 + (Cla_2d_rad / (np.pi * RA * e_ow)))


def sadraey_cl_targets(WTO, Vc, Vs, rho_c, rho_0, S):
    """Coeficientes alvo pelo método de Sadraey (2013)."""
    CLc   = (2 * WTO) / (rho_c * Vc**2 * S)
    CLcw  = CLc / 0.95
    Clc   = CLcw / 0.90
    CLmax = (2 * WTO) / (rho_0 * Vs**2 * S)
    CLmaxw = CLmax / 0.95
    Clmax = CLmaxw / 0.90
    return CLc, CLcw, Clc, CLmax, CLmaxw, Clmax


def llt_geometry(RA, S_wing, WTO, Vc, rho_c):
    """Parâmetros LLT para asa elíptica (Sadraey)."""
    b = np.sqrt(RA * S_wing)
    c = S_wing / b
    delta = delta_glauert(RA)
    e_ow = e_oswald_glauert(RA)
    CLcw = (2 * WTO) / (rho_c * Vc**2 * S_wing) / 0.95
    CDiwC = CLcw**2 / (np.pi * RA * e_ow)
    return b, c, delta, e_ow, CLcw, CDiwC


def area_minima_sadraey(WTO, Vc, rho_c, Clc_airfoil):
    """Área mínima teórica para satisfazer Clc ≤ Clc_aerofólio."""
    return (2 * WTO) / (rho_c * Vc**2 * Clc_airfoil * 0.95 * 0.90)


def area_minima_estol(WTO, Vs, rho_0, Clmax_airfoil):
    """Área mínima para satisfazer Clmax ≤ Clmax_aerofólio."""
    return (2 * WTO) / (rho_0 * Vs**2 * Clmax_airfoil * 0.95 * 0.90)


def varredura_geometrias(WTO, Vc, Vs, rho_c, rho_0, Clmax_af, RA_min=3.0, RA_max=12.0, RA_step=0.5):
    """Varredura de geometrias possíveis via LLT."""
    S_estol = area_minima_estol(WTO, Vs, rho_0, Clmax_af)
    RA_values = np.arange(RA_min, RA_max + RA_step/2, RA_step)
    resultados = []
    for RA in RA_values:
        b, c, delta, e_ow, CLcw, CDiwC = llt_geometry(RA, S_estol, WTO, Vc, rho_c)
        resultados.append({
            "RA": RA, "b": b, "c": c, "S": S_estol,
            "delta": delta, "e": e_ow, "CLcw": CLcw, "CDiwC": CDiwC
        })
    return resultados


def varredura_altitude(WTO, Vc, Vs, S, h_max=2000, h_step=100):
    """Varredura de altitude 0→h_max (ISA padrão)."""
    resultados = []
    for h in np.arange(0, h_max + h_step/2, h_step):
        atm = calcular_atmosfera_isa(h)
        rho_h = atm["rho"]
        CLc = (2 * WTO) / (rho_h * Vc**2 * S)
        CLcw = CLc / 0.95
        Clc = CLcw / 0.90
        CLmax = (2 * WTO) / (rho_h * Vs**2 * S)
        CLmaxw = CLmax / 0.95
        Clmax = CLmaxw / 0.90
        resultados.append({
            "h": h, "rho": rho_h, "CLc": CLc, "CLcw": CLcw,
            "Clc": Clc, "CLmax": CLmax, "CLmaxw": CLmaxw, "Clmax": Clmax
        })
    return resultados


def polar_asa(CD0, RA, e, CL_range=(-0.2, 2.1, 0.1)):
    """Polar CD vs CL: CD = CD0 + CL²/(π·RA·e)."""
    CLs = np.arange(*CL_range)
    denom = np.pi * RA * e
    CDi = CLs**2 / denom
    CD = CD0 + CDi
    LD = np.where(CD > 0, CLs / CD, 0.0)
    CL_opt = np.sqrt(CD0 * denom)
    CD_opt = 2 * CD0
    LD_max = CL_opt / CD_opt if CD_opt > 0 else 0
    return CLs, CDi, CD, LD, CL_opt, CD_opt, LD_max


def varredura_aoa_3d(alpha0_af, Cla_3d_deg, cd0_af, RA, e, alpha_range=(-20, 21, 1)):
    """Varredura de ângulo de ataque — asa 3D (LLT)."""
    alphas = np.arange(*alpha_range)
    denom = np.pi * RA * e
    CL_3d = Cla_3d_deg * (alphas - alpha0_af)
    CDi = CL_3d**2 / denom
    CD_tot = cd0_af + CDi
    LD = np.where(CD_tot > 0, CL_3d / CD_tot, 0.0)
    return alphas, CL_3d, CDi, CD_tot, LD


# ═══════════════════════════════════════════════════════════════════════════════
# PARTE 2b: DOWNWASH E ARRASTO — Sadraey (2013) Cap. 12
# ═══════════════════════════════════════════════════════════════════════════════

def calcular_downwash(Cla_3d_rad, RA, e_ow):
    """
    Downwash gradient dε/dα e ângulo de downwash ε.

    Sadraey (2013) Eq. 12.xx:
      dε/dα = (2 · CLα_3D) / (π · RA)          [adimensional]

    Para qualquer α (ou CL), ε = (dε/dα) · (α − α₀) [rad].
    Retorna o gradiente e a função ε(α_deg).
    """
    deda = (2.0 * Cla_3d_rad) / (np.pi * RA)   # [1/rad] → [rad/rad]
    return deda


def calcular_drag_breakdown(WTO, Vc, S, RA, e_ow, cd0_af, rho_c, Cla_3d_rad, alpha0_af):
    """
    Decomposição completa do arrasto em cruzeiro — Sadraey (2013).

    Componentes:
      D_parasita  = CD0 · q · S                (arrasto de perfil / parasita)
      D_induzido  = CDi · q · S  =  CL²/(π·AR·e) · q · S
      D_total     = D_parasita + D_induzido

    Downwash:
      dε/dα       (gradiente adimensional)
      ε_cruise    = dε/dα · αi_cruise           onde αi ≈ CL/(π·AR)  [rad]

    Parâmetros adimensionais:
      k  = 1/(π · AR · e)          (fator de arrasto induzido)
      CD_min  = CD0                (arrasto mínimo — polar parabólica)
      CL*     = sqrt(CD0 · π·AR·e) (CL ótimo)
      CD*     = 2·CD0              (CD no ponto ótimo)
      L/Dmax  = CL*/CD*
    """
    q = 0.5 * rho_c * Vc**2          # pressão dinâmica [Pa]
    CLc = (2 * WTO) / (rho_c * Vc**2 * S)   # CL de cruzeiro real

    k = 1.0 / (np.pi * RA * e_ow)
    CDi_c = k * CLc**2
    CD_total_c = cd0_af + CDi_c

    D_parasita = cd0_af * q * S
    D_induzido = CDi_c * q * S
    D_total    = D_parasita + D_induzido
    L_cruise   = WTO                  # equilíbrio nível — L = W

    LD_c = CLc / CD_total_c if CD_total_c > 0 else 0.0

    # Downwash
    deda = calcular_downwash(Cla_3d_rad, RA, e_ow)          # [rad/rad]
    alpha_i_c = CLc / (np.pi * RA)                          # ângulo induzido [rad]
    epsilon_c = deda * alpha_i_c                             # downwash em cruzeiro [rad]

    # Ângulo de ataque geométrico em cruzeiro (LLT)
    # CL = CLα_3D · (α - α0)  →  α = CL/CLα_3D + α0
    alpha_c_deg = (CLc / Cla_3d_rad) * (180.0 / np.pi) + alpha0_af

    # Ponto ótimo (L/D max)
    CL_opt = np.sqrt(cd0_af * np.pi * RA * e_ow)
    CD_opt = 2.0 * cd0_af
    LD_max = CL_opt / CD_opt if CD_opt > 0 else 0.0

    # Varredura CDi vs alpha para tabela
    alphas = np.arange(-10, 21, 1, dtype=float)
    CL_sw  = Cla_3d_rad * (alphas - alpha0_af) * (np.pi / 180.0)
    CDi_sw = k * CL_sw**2
    eps_sw = deda * CL_sw / (np.pi * RA)   # downwash [rad] em cada α

    return {
        "q":           q,
        "CLc":         CLc,
        "CDi_c":       CDi_c,
        "CD_total_c":  CD_total_c,
        "D_parasita":  D_parasita,
        "D_induzido":  D_induzido,
        "D_total":     D_total,
        "L_cruise":    L_cruise,
        "LD_c":        LD_c,
        "k":           k,
        "deda":        deda,              # [rad/rad]
        "deda_deg":    deda,              # mesmo valor — ε/α ambos adimensionais
        "alpha_i_c":   np.degrees(alpha_i_c),
        "epsilon_c":   np.degrees(epsilon_c),
        "alpha_c_deg": alpha_c_deg,
        "CL_opt":      CL_opt,
        "CD_opt":      CD_opt,
        "LD_max":      LD_max,
        "alphas":      alphas,
        "CL_sw":       CL_sw,
        "CDi_sw":      CDi_sw,
        "eps_sw":      np.degrees(eps_sw),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PARTE 3: RELATÓRIO TEXTO (Sadraey + LLT)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_report(cfg, output_filename="aerodynamic_calculations.txt"):
    """
    Gera relatório aerodinâmico completo baseado em Sadraey (2013) + LLT.
    """
    g = 9.81  # noqa — don't use as loop var below
    WTO = cfg.get("WTO_N", cfg.get("peso_kg", 5.0) * g)
    Vc = cfg.get("Vc", cfg.get("v", 15.0) * 0.80)
    Vs = cfg.get("Vs", cfg.get("v", 15.0) * 0.50)
    b = cfg.get("b", 3.0)
    c = cfg.get("c", 0.6)
    S = b * c
    RA = b**2 / S if S > 0 else 0

    altitude_m = cfg.get("altitude_m", 0)
    atm_cruise = calcular_atmosfera_isa(altitude_m)
    atm_sl = calcular_atmosfera_isa(0)
    rho_c = atm_cruise["rho"]
    rho_0 = atm_sl["rho"]

    perfil_nome = cfg.get("perfil", cfg.get("perfis_sel", ["N/A"])[0])
    re_alvo = cfg.get("re_real", 100000)
    dados_perfil = extrair_dados_perfil(perfil_nome, re_alvo)

    cla_af = dados_perfil["cla_af"]
    alpha0_af = dados_perfil["alpha0_af"]
    clmax_af = dados_perfil["clmax_af"]
    cd0_af = dados_perfil["cd0_af"]
    cm0_af = dados_perfil["cm0_af"]
    xcp0_af = dados_perfil["xcp0_af"]
    fonte_dados = dados_perfil["fonte"]

    e_ow = e_oswald_glauert(RA)
    delta = delta_glauert(RA)

    CLc, CLcw, Clc, CLmax, CLmaxw, Clmax = sadraey_cl_targets(WTO, Vc, Vs, rho_c, rho_0, S)

    Cla_3d_rad = wing_3d_slope(cla_af, RA, e_ow)
    Cla_3d_deg = Cla_3d_rad / 57.2958

    alpha_cruise = 4.0
    Clc_cruise_est = cla_af * (alpha_cruise - alpha0_af) * np.pi / 180
    S_min_cruise = area_minima_sadraey(WTO, Vc, rho_c, max(Clc_cruise_est, 0.1))
    S_min_estol = area_minima_estol(WTO, Vs, rho_0, clmax_af)

    # geo_var só é calculada se o usuário habilitou a aba GEO (RA) na GUI.
    geo_llt = cfg.get("geo_llt", False)
    geo_var = varredura_geometrias(WTO, Vc, Vs, rho_c, rho_0, clmax_af) if geo_llt else []
    alt_var = varredura_altitude(WTO, Vc, Vs, S, h_max=2000)
    alphas, CL_3d, CDi_3d, CD_tot_3d, LD_3d = varredura_aoa_3d(alpha0_af, Cla_3d_deg, cd0_af, RA, e_ow)
    CLs, CDi_p, CD_p, LD_p, CL_opt, CD_opt, LD_max = polar_asa(cd0_af, RA, e_ow)
    dw = calcular_drag_breakdown(WTO, Vc, S, RA, e_ow, cd0_af, rho_c, Cla_3d_rad, alpha0_af)

    W = 120
    SEP = "=" * W
    SEP2 = "-" * W

    lines = []

    def section(title):
        lines.append(SEP)
        lines.append(f"  {title}")
        lines.append(SEP)

    lines.append(SEP)
    lines.append("  RELATÓRIO AERODINÂMICO — Sadraey (2013) + LLT + ISA")
    lines.append(f"  Dark Wing Project | Perfil: {perfil_nome} | Re: {re_alvo:.0f}")
    lines.append(f"  Dados do perfil: {fonte_dados}")
    lines.append(SEP)
    lines.append("")

    section("1. PARÂMETROS DE ENTRADA")
    lines.append(f"  WTO (Peso total)          : {WTO:.2f} N  ({WTO/g:.2f} kg)")
    lines.append(f"  Vc  (Vel. cruzeiro)       : {Vc:.2f} m/s")
    lines.append(f"  Vs  (Vel. estol)          : {Vs:.2f} m/s")
    lines.append(f"  b   (Envergadura)         : {b:.3f} m")
    lines.append(f"  c   (Corda)               : {c:.3f} m")
    lines.append(f"  S   (Área)                : {S:.4f} m²")
    lines.append(f"  RA  (Alongamento)         : {RA:.3f}")
    lines.append(f"  h   (Altitude cruzeiro)   : {altitude_m:.0f} m")
    lines.append(f"  ρc  (Densidade h={altitude_m:.0f}m)  : {rho_c:.5f} kg/m³")
    lines.append(f"  ρ0  (Densidade SL)        : {rho_0:.5f} kg/m³")
    lines.append("")
    lines.append("  Dados do aerofólio (database.py):")
    lines.append(f"    Clα (inclinação 2D)     : {cla_af:.3f} 1/rad  ({dados_perfil['a0_2d_deg']:.4f} 1/°)")
    lines.append(f"    α₀  (CL=0)              : {alpha0_af:.2f}°")
    lines.append(f"    Clmax                   : {clmax_af:.3f}")
    lines.append(f"    Cd0 (perfil)            : {cd0_af:.5f}")
    lines.append(f"    Cm0                     : {cm0_af:.4f}")
    lines.append(f"    Xcp/c                   : {xcp0_af:.3f}")
    lines.append("")

    section("2. COEFICIENTES ALVO — MÉTODO DE SADRAEY")
    lines.append(f"  {'Parâmetro':<25} {'Equação':<45} {'Valor':>10}")
    lines.append(SEP2[:82])
    lines.append(f"  {'CLc  (aeronave)':<25} {'2·WTO/(ρc·Vc²·S)':<45} {CLc:>10.4f}")
    lines.append(f"  {'CLcw (asa)':<25} {'CLc / 0,95':<45} {CLcw:>10.4f}")
    lines.append(f"  {'Clc  (aerofólio)':<25} {'CLcw / 0,90':<45} {Clc:>10.4f}")
    lines.append(f"  {'CLmax (aeronave)':<25} {'2·WTO/(ρ0·Vs²·S)':<45} {CLmax:>10.4f}")
    lines.append(f"  {'CLmaxw (asa)':<25} {'CLmax / 0,95':<45} {CLmaxw:>10.4f}")
    lines.append(f"  {'Clmax (aerofólio)':<25} {'CLmaxw / 0,90':<45} {Clmax:>10.4f}")
    lines.append("")
    lines.append(f"  Área mínima (cruzeiro)    : {S_min_cruise:.4f} m²  (Clc_est={Clc_cruise_est:.3f})")
    lines.append(f"  Área mínima (estol)       : {S_min_estol:.4f} m²")
    lines.append(f"  Área adotada              : {S:.4f} m²")
    if S < S_min_estol:
        lines.append(f"  ⚠ ALERTA: S < S_min_estol → Estol em Vs={Vs:.1f}m/s NÃO é viável!")
        lines.append(f"             Requer S ≥ {S_min_estol:.4f} m²  ou  Vs ≥ {np.sqrt(2*WTO/(rho_0*S*clmax_af*0.95*0.90)):.1f} m/s")
    elif S < S_min_cruise:
        lines.append(f"  ⚠ ALERTA: S < S_min_cruise → Cruzeiro pode requerer α alto")
    else:
        lines.append(f"  ✓ S adotado satisfaz ambas as restrições")
    lines.append("")

    section("3. GEOMETRIAS POSSÍVEIS — LLT (Sadraey)")
    if cfg.get("geo_llt", False):
        hdr = f"  {'RA':<6} | {'b (m)':<8} | {'c (m)':<8} | {'S (m²)':<8} | {'CLcw':<8} | {'δ':<10} | {'e':<8} | {'CDiwC':<10}"
        lines.append(hdr)
        lines.append("  " + "-" * (len(hdr) - 2))
        for geo in geo_var:
            marker = "  ← ADOTADA" if abs(geo["RA"] - RA) < 0.3 else ""
            lines.append(
                f"  {geo['RA']:<6.1f} | {geo['b']:<8.4f} | {geo['c']:<8.4f} | {geo['S']:<8.4f} | "
                f"{geo['CLcw']:<8.4f} | {geo['delta']:<10.6f} | {geo['e']:<8.4f} | {geo['CDiwC']:<10.6f}{marker}"
            )
        lines.append("")
        lines.append(f"  Geometria adotada:")
        lines.append(f"    δ    = {delta:.6f}")
        lines.append(f"    e    = {e_ow:.4f}")
        lines.append(f"    Clα 3D = {Cla_3d_rad:.4f} 1/rad = {Cla_3d_deg:.5f} 1/°")
        lines.append("")
    else:
        lines.append("  [Desativado] Varredura de geometrias LLT não solicitada.")
        lines.append("  Ative a aba GEO (RA) na GUI para gerar esta seção.")
        lines.append("")

    section("4. VARREDURA DE ALTITUDE — 0→2000 m (ISA)")
    lines.append(f"  {'h (m)':<8} | {'ρ (kg/m³)':<12} | {'CLc':<8} | {'CLcw':<8} | {'Clc':<8} | {'CLmax':<8} | {'CLmaxw':<9} | {'Clmax':<10}")
    lines.append("  " + "-" * 90)
    for a in alt_var:
        lines.append(
            f"  {a['h']:<8.0f} | {a['rho']:<12.5f} | {a['CLc']:<8.4f} | {a['CLcw']:<8.4f} | "
            f"{a['Clc']:<8.4f} | {a['CLmax']:<8.4f} | {a['CLmaxw']:<9.4f} | {a['Clmax']:<10.4f}"
        )
    lines.append("")

    section("5. VARREDURA DE AOA — ASA 3D (LLT)")
    lines.append(f"  {'α (°)':<7} | {'CL':<9} | {'CDi':<10} | {'CD_total':<10} | {'L/D':<8}")
    lines.append("  " + "-" * 52)
    for i in range(len(alphas)):
        lines.append(
            f"  {alphas[i]:<7.0f} | {CL_3d[i]:<9.4f} | {CDi_3d[i]:<10.6f} | {CD_tot_3d[i]:<10.6f} | {LD_3d[i]:<8.2f}"
        )
    lines.append("")

    section("6. POLAR DA ASA — CD vs CL")
    lines.append(f"  CD = {cd0_af:.5f} + CL² / {np.pi*RA*e_ow:.4f}")
    lines.append("")
    lines.append(f"  {'CL':<8} | {'CDi':<10} | {'CD':<10} | {'L/D':<8}")
    lines.append("  " + "-" * 40)
    for i in range(len(CLs)):
        lines.append(f"  {CLs[i]:<8.2f} | {CDi_p[i]:<10.6f} | {CD_p[i]:<10.6f} | {LD_p[i]:<8.2f}")
    lines.append("")
    lines.append(f"  L/D máximo (teórico): {LD_max:.2f}  em CL*={CL_opt:.4f}, CD*={CD_opt:.6f}")
    lines.append("")

    section("7. DOWNWASH E DECOMPOSIÇÃO DO ARRASTO — Sadraey (2013)")

    lines.append("  7a. GRADIENTE DE DOWNWASH (dε/dα)")
    lines.append(f"  {'Parâmetro':<40} {'Equação':<35} {'Valor':>12}")
    lines.append("  " + "-" * 90)
    lines.append(f"  {'k  (fator arrasto induzido)':<40} {'1/(π·RA·e)':<35} {dw['k']:>12.6f}")
    lines.append(f"  {'dε/dα  (gradiente downwash)':<40} {'2·CLα_3D/(π·RA)':<35} {dw['deda']:>12.6f}  [rad/rad]")
    lines.append(f"  {'dε/dα  (idem em °/°)':<40} {'(mesmo valor adimensional)':<35} {dw['deda']:>12.6f}  [°/°]")
    lines.append("")

    lines.append("  7b. CONDIÇÕES DE CRUZEIRO")
    lines.append(f"  {'Parâmetro':<40} {'Valor':>12}  {'Unidade'}")
    lines.append("  " + "-" * 70)
    lines.append(f"  {'q  (pressão dinâmica)':<40} {dw['q']:>12.4f}  Pa")
    lines.append(f"  {'CLc  (CL de cruzeiro)':<40} {dw['CLc']:>12.4f}  —")
    lines.append(f"  {'α  (ângulo de ataque geométrico)':<40} {dw['alpha_c_deg']:>12.4f}  °")
    lines.append(f"  {'αi (ângulo induzido)':<40} {dw['alpha_i_c']:>12.4f}  °")
    lines.append(f"  {'ε  (downwash em cruzeiro)':<40} {dw['epsilon_c']:>12.4f}  °")
    lines.append(f"  {'CDi  (arrasto induzido)':<40} {dw['CDi_c']:>12.6f}  —")
    lines.append(f"  {'CD0  (arrasto parasita perfil)':<40} {cd0_af:>12.6f}  —")
    lines.append(f"  {'CD_total  (cruzeiro)':<40} {dw['CD_total_c']:>12.6f}  —")
    lines.append(f"  {'L/D  (cruzeiro)':<40} {dw['LD_c']:>12.4f}  —")
    lines.append("")

    lines.append("  7c. FORÇAS DE ARRASTO EM CRUZEIRO")
    lines.append(f"  {'Componente':<40} {'Força (N)':>12}  {'% do total':>10}")
    lines.append("  " + "-" * 70)
    pct_par = 100 * dw['D_parasita'] / dw['D_total'] if dw['D_total'] > 0 else 0
    pct_ind = 100 * dw['D_induzido'] / dw['D_total'] if dw['D_total'] > 0 else 0
    lines.append(f"  {'D_parasita  (CD0·q·S)':<40} {dw['D_parasita']:>12.4f}  {pct_par:>9.1f}%")
    lines.append(f"  {'D_induzido  (CDi·q·S)':<40} {dw['D_induzido']:>12.4f}  {pct_ind:>9.1f}%")
    lines.append(f"  {'D_total':<40} {dw['D_total']:>12.4f}  {'100.0':>9}%")
    lines.append(f"  {'L_cruise  (= WTO, equilíbrio)':<40} {dw['L_cruise']:>12.4f}  N")
    lines.append("")

    lines.append("  7d. PONTO ÓTIMO  (L/D máximo — polar parabólica)")
    lines.append(f"  {'CL*  = sqrt(CD0·π·RA·e)':<40} {dw['CL_opt']:>12.4f}  —")
    lines.append(f"  {'CD*  = 2·CD0':<40} {dw['CD_opt']:>12.6f}  —")
    lines.append(f"  {'(L/D)max = CL*/CD*':<40} {dw['LD_max']:>12.4f}  —")
    lines.append(f"  {'CDi* = CD0  (50% induzido)':<40} {cd0_af:>12.6f}  —")
    lines.append("")

    lines.append(f"  7e. VARREDURA α: DOWNWASH ε  e  CDi  (asa 3D, LLT)")
    lines.append(f"  {'α (°)':<7} | {'CL':<9} | {'CDi':<10} | {'αi (°)':<10} | {'ε (°)':<10} | {'L/D':<8}")
    lines.append("  " + "-" * 65)
    for i in range(len(dw['alphas'])):
        al = dw['alphas'][i]
        cl = dw['CL_sw'][i]
        cdi = dw['CDi_sw'][i]
        eps = dw['eps_sw'][i]
        ai  = np.degrees(cl / (np.pi * RA)) if RA > 0 else 0.0
        cd_tot_i = cd0_af + cdi
        ld_i = cl / cd_tot_i if abs(cd_tot_i) > 1e-9 else 0.0
        lines.append(
            f"  {al:<7.0f} | {cl:<9.4f} | {cdi:<10.6f} | {ai:<10.4f} | {eps:<10.4f} | {ld_i:<8.2f}"
        )
    lines.append("")

    lines.append(SEP)
    lines.append("  Fim do relatório.")
    lines.append(SEP)

    full_path = _save_path(output_filename)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  [Report] Relatório salvo em '{full_path}'")
    return full_path


# ═══════════════════════════════════════════════════════════════════════════════
# PARTE 4: VISUALIZAÇÕES (salvas como imagens PNG no diretório local)
# ═══════════════════════════════════════════════════════════════════════════════

def plotar_analise_sadraey(cfg):
    """
    Gera figuras Plotly com análise Sadraey+LLT e salva como imagens PNG.
    """
    GRAV = 9.81
    WTO = cfg.get("WTO_N", cfg.get("peso_kg", 5.0) * GRAV)
    Vc = cfg.get("Vc", cfg.get("v", 15.0) * 0.80)
    Vs = cfg.get("Vs", cfg.get("v", 15.0) * 0.50)
    b = cfg.get("b", 3.0)
    c = cfg.get("c", 0.6)
    S = b * c
    RA = b**2 / S if S > 0 else 0

    altitude_m = cfg.get("altitude_m", 0)
    atm_cruise = calcular_atmosfera_isa(altitude_m)
    atm_sl = calcular_atmosfera_isa(0)
    rho_c = atm_cruise["rho"]
    rho_0 = atm_sl["rho"]

    perfil_nome = cfg.get("perfil", cfg.get("perfis_sel", ["N/A"])[0])
    re_alvo = cfg.get("re_real", 100000)
    dados_perfil = extrair_dados_perfil(perfil_nome, re_alvo)

    cla_af = dados_perfil["cla_af"]
    alpha0_af = dados_perfil["alpha0_af"]
    clmax_af = dados_perfil["clmax_af"]
    cd0_af = dados_perfil["cd0_af"]

    e_ow = e_oswald_glauert(RA)
    Cla_3d_rad = wing_3d_slope(cla_af, RA, e_ow)
    Cla_3d_deg = Cla_3d_rad / 57.2958

    # ── FIGURA 1: Análise Paramétrica ─────────────────────────────
    print("  [Sadraey] Gerando Figura 1: Análise Paramétrica...")

    RA_range = np.arange(3.0, 12.5, 0.25)
    alpha_cruise = 4.0
    Clc_cruise_est = cla_af * (alpha_cruise - alpha0_af) * np.pi / 180
    S_cruise = [area_minima_sadraey(WTO, Vc, rho_c, max(Clc_cruise_est, 0.1)) for _ in RA_range]
    S_estol = [area_minima_estol(WTO, Vs, rho_0, clmax_af) for _ in RA_range]

    fig1 = make_subplots(
        rows=2, cols=2,
        vertical_spacing=0.12, horizontal_spacing=0.10,
        subplot_titles=(
            "<b>Área Mínima vs Alongamento</b>",
            "<b>Eficiência Oswald vs RA</b>",
            "<b>Varredura de Altitude — CLc</b>",
            "<b>Varredura de Altitude — CLmax</b>",
        ),
    )

    fig1.add_trace(go.Scatter(x=RA_range, y=S_cruise, name="Cruzeiro (Sadraey)",
                               line=dict(color="#1f77b4", width=2)), row=1, col=1)
    fig1.add_trace(go.Scatter(x=RA_range, y=S_estol, name="Estol (Sadraey)",
                               line=dict(color="#d62728", width=2, dash="dash")), row=1, col=1)
    fig1.add_hline(y=S, line_dash="dot", line_color="black", line_width=1.5,
                   annotation_text=f"S adotado={S:.3f} m²", row=1, col=1)

    e_vals = [e_oswald_glauert(ra) for ra in RA_range]
    fig1.add_trace(go.Scatter(x=RA_range, y=e_vals, name="e (Glauert)",
                               line=dict(color="#2ca02c", width=2), showlegend=False), row=1, col=2)
    fig1.add_hline(y=e_ow, line_dash="dot", line_color="black", line_width=1.5,
                   annotation_text=f"e={e_ow:.3f}", row=1, col=2)

    alt_var = varredura_altitude(WTO, Vc, Vs, S, h_max=3000)
    hs = [a["h"] for a in alt_var]
    CLcs = [a["CLc"] for a in alt_var]
    fig1.add_trace(go.Scatter(x=hs, y=CLcs, name="CLc", line=dict(color="#1f77b4", width=2),
                               showlegend=False), row=2, col=1)
    fig1.add_hline(y=1.0, line_dash="dash", line_color="gray", line_width=1, row=2, col=1)

    CLmaxs = [a["CLmax"] for a in alt_var]
    fig1.add_trace(go.Scatter(x=hs, y=CLmaxs, name="CLmax", line=dict(color="#d62728", width=2),
                               showlegend=False), row=2, col=2)
    fig1.add_hline(y=1.0, line_dash="dash", line_color="gray", line_width=1, row=2, col=2)

    fig1.update_xaxes(title_text="Alongamento RA", row=1, col=1)
    fig1.update_xaxes(title_text="Alongamento RA", row=1, col=2)
    fig1.update_xaxes(title_text="Altitude [m]", row=2, col=1)
    fig1.update_xaxes(title_text="Altitude [m]", row=2, col=2)
    fig1.update_yaxes(title_text="Área mínima [m²]", row=1, col=1)
    fig1.update_yaxes(title_text="e_Oswald", row=1, col=2)
    fig1.update_yaxes(title_text="CLc", row=2, col=1)
    fig1.update_yaxes(title_text="CLmax", row=2, col=2)

    fig1.update_layout(
        height=900, width=1300, template="plotly_white",
        title=dict(
            text=f"Dark Wing Project | Análise Sadraey+LLT | Perfil: {perfil_nome} | "
                 f"W={WTO/GRAV:.1f}kg | Vc={Vc:.1f}m/s | Vs={Vs:.1f}m/s | S={S:.3f}m² | RA={RA:.2f}",
            x=0.5, font=dict(size=14)),
        margin=dict(t=100, b=80, l=80, r=60),
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    # SAVE AS IMAGE INSTEAD OF SHOW
    fig1_path = _save_path(f"sadraey_fig1_{perfil_nome.replace(' ', '_')}.png")
    fig1.write_image(fig1_path, scale=2)
    print(f"  [Sadraey] Figura 1 salva em: {fig1_path}")

    # ── FIGURA 2: Polar + AOA + L/D ──────────────────────────────
    print("  [Sadraey] Gerando Figura 2: Polar e Performance...")

    alphas, CL_3d, CDi_3d, CD_tot_3d, LD_3d = varredura_aoa_3d(alpha0_af, Cla_3d_deg, cd0_af, RA, e_ow)
    CLs, CDi_p, CD_p, LD_p, CL_opt, CD_opt, LD_max = polar_asa(cd0_af, RA, e_ow)

    fig2 = make_subplots(
        rows=2, cols=2,
        vertical_spacing=0.12, horizontal_spacing=0.10,
        subplot_titles=(
            "<b>Polar CD vs CL</b>",
            "<b>CL vs α (Asa 3D)</b>",
            "<b>L/D vs α</b>",
            "<b>CDi vs CL²</b>",
        ),
    )

    fig2.add_trace(go.Scatter(x=CD_p, y=CLs, name="Polar", mode="lines",
                               line=dict(color="#1f77b4", width=2)), row=1, col=1)
    fig2.add_trace(go.Scatter(x=[CD_opt], y=[CL_opt], name=f"L/Dmax ({LD_max:.1f})",
                               mode="markers", marker=dict(color="red", size=10)), row=1, col=1)

    fig2.add_trace(go.Scatter(x=alphas, y=CL_3d, name="CL(α)", mode="lines",
                               line=dict(color="#2ca02c", width=2), showlegend=False), row=1, col=2)
    fig2.add_hline(y=0, line_dash="dot", line_color="gray", line_width=1, row=1, col=2)

    fig2.add_trace(go.Scatter(x=alphas, y=LD_3d, name="L/D(α)", mode="lines",
                               line=dict(color="#ff7f0e", width=2), showlegend=False), row=2, col=1)
    fig2.add_annotation(x=alphas[np.argmax(LD_3d)], y=np.max(LD_3d),
                       text=f"L/Dmax={np.max(LD_3d):.1f}", showarrow=True, arrowhead=2,
                       font=dict(size=10), row=2, col=1)

    fig2.add_trace(go.Scatter(x=CLs**2, y=CDi_p, name="CDi(CL²)", mode="lines",
                               line=dict(color="#9467bd", width=2), showlegend=False), row=2, col=2)

    fig2.update_xaxes(title_text="CD", row=1, col=1)
    fig2.update_xaxes(title_text="α [°]", row=1, col=2)
    fig2.update_xaxes(title_text="α [°]", row=2, col=1)
    fig2.update_xaxes(title_text="CL²", row=2, col=2)
    fig2.update_yaxes(title_text="CL", row=1, col=1)
    fig2.update_yaxes(title_text="CL", row=1, col=2)
    fig2.update_yaxes(title_text="L/D", row=2, col=1)
    fig2.update_yaxes(title_text="CDi", row=2, col=2)

    fig2.update_layout(
        height=900, width=1300, template="plotly_white",
        title=dict(
            text=f"Dark Wing Project | Polar & Performance | e={e_ow:.3f} | CD0={cd0_af:.5f} | "
                 f"Clα_3D={Cla_3d_deg:.5f} 1/° | Perfil: {perfil_nome}",
            x=0.5, font=dict(size=14)),
        margin=dict(t=100, b=80, l=80, r=60),
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    # SAVE AS IMAGE INSTEAD OF SHOW
    fig2_path = _save_path(f"sadraey_fig2_{perfil_nome.replace(' ', '_')}.png")
    fig2.write_image(fig2_path, scale=2)
    print(f"  [Sadraey] Figura 2 salva em: {fig2_path}")

    # ── FIGURA 3: Varredura de Geometrias (tabela) ────
    # Só gerada quando o usuário habilita explicitamente a aba GEO (RA) na GUI.
    # O flag chega via cfg["geo_llt"]; ausente = False (retrocompatível).
    if not cfg.get("geo_llt", False):
        print("  [Sadraey] Figura 3 (Geometrias LLT) ignorada — aba GEO (RA) desativada.")
        print("  [Sadraey] Análise concluída. Figuras 1 e 2 salvas localmente.")
        return

    print("  [Sadraey] Gerando Figura 3: Geometrias LLT...")

    geo_var = varredura_geometrias(WTO, Vc, Vs, rho_c, rho_0, clmax_af, RA_min=3.0, RA_max=12.0)

    fig3 = go.Figure(data=[go.Table(
        header=dict(
            values=["RA", "b [m]", "c [m]", "S [m²]", "CLcw", "δ", "e", "CDiwC"],
            fill_color="#161b22", align="center", font=dict(color="white", size=11),
            line_color="#30363d", line_width=1
        ),
        cells=dict(
            values=[
                [f"{g['RA']:.1f}" for g in geo_var],
                [f"{g['b']:.3f}" for g in geo_var],
                [f"{g['c']:.3f}" for g in geo_var],
                [f"{g['S']:.4f}" for g in geo_var],
                [f"{g['CLcw']:.4f}" for g in geo_var],
                [f"{g['delta']:.6f}" for g in geo_var],
                [f"{g['e']:.4f}" for g in geo_var],
                [f"{g['CDiwC']:.6f}" for g in geo_var],
            ],
            fill_color=[["#f0f0f0" if i % 2 == 0 else "white" for i in range(len(geo_var))]],
            align="center", font=dict(size=10), line_color="#30363d", line_width=0.5,
            height=25
        )
    )])

    idx_adotado = int(np.argmin([abs(g["RA"] - RA) for g in geo_var]))

    fig3.update_layout(
        height=600, width=1100, template="plotly_white",
        title=dict(
            text=f"Dark Wing Project | Geometrias LLT | W={WTO/GRAV:.1f}kg | Vc={Vc:.1f}m/s | Vs={Vs:.1f}m/s | "
                 f"RA adotado={RA:.2f} (linha {idx_adotado+1}) | Perfil: {perfil_nome}",
            x=0.5, font=dict(size=13)),
        margin=dict(t=80, b=40, l=40, r=40),
    )

    # SAVE AS IMAGE INSTEAD OF SHOW
    fig3_path = _save_path(f"sadraey_fig3_{perfil_nome.replace(' ', '_')}.png")
    fig3.write_image(fig3_path, scale=2)
    print(f"  [Sadraey] Figura 3 salva em: {fig3_path}")
    print("  [Sadraey] Análise concluída. Todas as figuras salvas localmente.")


# ═══════════════════════════════════════════════════════════════════════════════
# PARTE 5: COMPATIBILIDADE RETROATIVA
# ═══════════════════════════════════════════════════════════════════════════════

def plotar_multi_temp(resultado, cfg):
    """Stub de compatibilidade."""
    print("  [AVISO] plotar_multi_temp() foi substituído por análise Sadraey+LLT.")
    print("  [AVISO] Chamando plotar_analise_sadraey()...")
    plotar_analise_sadraey(cfg)


def calcular_asa_multi_temp(v, c, b, peso_kg, perfis_sel, asat_sel,
                            temp_min=15.0, temp_max=30.0, temp_step=1.0, P_Pa=101325.0):
    """Stub de compatibilidade."""
    print("  [AVISO] calcular_asa_multi_temp() foi descontinuado.")
    print("  [AVISO] Use a análise Sadraey+LLT para análise paramétrica.")
    return {"temperaturas": [], "dados": {}, "deprecated": True}


# ═══════════════════════════════════════════════════════════════════════════════
# REFERÊNCIAS
# ═══════════════════════════════════════════════════════════════════════════════
# Sadraey, M. Aircraft Design: A Systems Engineering Approach. Wiley, 2013.
# White, F.M. Fluid Mechanics, 8ª Ed. McGraw-Hill, 2016. §8.4 (LLT)
# Glauert, H. The Elements of Aerofoil and Airscrew Theory, 1926.
# ═══════════════════════════════════════════════════════════════════════════════
