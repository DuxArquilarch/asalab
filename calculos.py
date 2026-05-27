import numpy as np
from database import DATABASE
from aerodynamic_report import calcular_atmosfera_isa

# Constantes físicas
g      = 9.81
# Constantes atmosféricas (R_AR, GAMMA, MU_0, T_0, S_SUTH) importadas via aerodynamic_report


def correcao_asat(forma, AR):
    if forma == "Elíptica":
        return 1.0, 1.0
    elif forma == "Delta":
        e_delta = float(np.clip(0.82 * (1 - 0.02 * AR), 0.60, 0.88))
        return e_delta, 0.90
    else:
        return None, 1.0


def eficiencia_oswald(AR):
    e = 1.78 * (1 - 0.045 * AR**0.68) - 0.64
    return float(np.clip(e, 0.60, 0.95))


def interpolar_coeficientes(re_alvo, dados_perfil):
    res_sorted = sorted(dados_perfil.keys())
    valores = np.array([dados_perfil[re] for re in res_sorted], dtype=float)

    # Interpola/extrapola em log(Re). Antes, valores fora da faixa tabulada
    # eram travados no primeiro/ultimo ponto, mascarando o efeito da temperatura.
    if len(res_sorted) == 1:
        raw = valores[0]
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
        v0, v1 = valores[i0], valores[i1]
        raw = v0 + (x - x0) * (v1 - v0) / (x1 - x0)

    raw = np.array(raw, dtype=float)
    if raw.size == 3:
        raw = np.append(raw, [-0.05, 0.25])

    raw[0] = np.clip(raw[0], 0.02, 0.14)   # a0 [1/grau]
    raw[1] = np.clip(raw[1], -25.0, 8.0)   # alpha L=0 [graus]
    raw[2] = np.clip(raw[2], 0.003, 0.25)  # CD0
    raw[3] = np.clip(raw[3], -0.60, 0.20)  # Cm0
    raw[4] = np.clip(raw[4], 0.0, 1.5)     # xcp/c
    return raw


def correcao_prandtl_glauert(a0_2d, v, v_som=340.0):
    Ma = v / v_som
    if Ma >= 0.7:
        print(f"  [AVISO] Ma = {Ma:.2f} >= 0.7 -- correção P-G não é precisa.")
    beta = np.sqrt(max(1.0 - Ma**2, 0.01))
    return a0_2d / beta, Ma


def ponto_transicao(v, c, rho, mu):
    RE_TRANS = 5e5
    x_tr = RE_TRANS * mu / (rho * v)
    return float(np.clip(x_tr / c * 100, 0.0, 100.0))


def calcular_cm_xcp(alphas, cl_asa, cm0_2d, xcp0_2d, AR, e_oswald):
    cd_ind = (cl_asa**2) / (np.pi * AR * e_oswald)
    cm_asa = cm0_2d - 0.05 * cl_asa - 0.12 * cd_ind
    with np.errstate(divide="ignore", invalid="ignore"):
        xcp_asa = np.where(
            np.abs(cl_asa) > 0.05,
            np.clip(0.25 - cm_asa / cl_asa, 0.0, 1.5),
            xcp0_2d,
        )
    return cm_asa, xcp_asa


# ---------------------------------------------------------------------------
# Cálculo ISA padrão (com altitude e temperatura)
# ---------------------------------------------------------------------------
def calcular_asa(v, c, b, peso_kg, perfis_sel, asat_sel, altitude_m=0, temp_C=15.0):
    # Usa aerodynamic_report.calcular_atmosfera_isa() para propriedades realistas
    atm = calcular_atmosfera_isa(altitude_m, temp_C)
    rho   = atm["rho"]
    mu    = atm["mu"]
    V_SOM = atm["v_som"]

    S       = b * c
    AR      = b**2 / S
    re_real = (rho * v * c) / mu
    cl_req  = (2.0 * peso_kg * g) / (rho * v**2 * S)

    e_base   = eficiencia_oswald(AR)
    e_override, kappa = correcao_asat(asat_sel, AR)
    e_oswald = e_override if e_override is not None else e_base

    x_tr_pct = ponto_transicao(v, c, rho, mu)
    alphas   = np.linspace(-6, 16, 150)
    Ma_info  = v / V_SOM

    print(f"\n  Re = {re_real:.0f}  |  AR = {AR:.2f}  |  e_Oswald = {e_oswald:.3f}")
    print(f"  CL_req = {cl_req:.4f}  |  AsaT: {asat_sel}  |  κ = {kappa:.2f}")
    print(f"  Ma = {Ma_info:.3f}  |  Transição lam->turb: {x_tr_pct:.1f}% da corda")
    print(f"  Atmosfera: h={altitude_m:.0f}m  T={temp_C:.1f}°C  ρ={rho:.4f} kg/m³  μ={mu*1e5:.3f}×10⁻⁵ Pa·s  a={V_SOM:.1f} m/s")

    resultados = {}
    for perfil in perfis_sel:
        coefs = interpolar_coeficientes(re_real, DATABASE[perfil])
        a0_2d_raw, aL0, cd0, cm0_2d, xcp0_2d = coefs
        a0_2d, Ma = correcao_prandtl_glauert(a0_2d_raw, v, V_SOM)

        if asat_sel == "Delta" and AR < 3.0:
            a_asa_delta = np.pi * AR / 2.0
            blend  = AR / 3.0
            a_llt  = a0_2d / (1.0 + (57.3 * a0_2d) / (np.pi * e_oswald * AR))
            a_asa  = (1 - blend) * a_asa_delta + blend * a_llt
        else:
            a_asa = a0_2d / (1.0 + (57.3 * a0_2d) / (np.pi * e_oswald * AR))

        a_asa  *= kappa
        cl_asa  = a_asa * (alphas - aL0)
        cd_tot  = cd0 + (cl_asa**2) / (np.pi * AR * e_oswald)
        eff     = np.where(cl_asa > 0, cl_asa / np.maximum(cd_tot, 0.001), 0.0)
        cl_star = np.sqrt(np.pi * AR * e_oswald * cd0)
        ld_max  = cl_star / (2.0 * cd0)
        alpha_stall = ((1.2 + 0.12 * AR) / a_asa) + aL0

        cm_asa, xcp_asa = calcular_cm_xcp(alphas, cl_asa, cm0_2d, xcp0_2d, AR, e_oswald)

        resultados[perfil] = {
            "cl_asa": cl_asa, "cd_tot": cd_tot, "eff": eff,
            "ld_max": ld_max, "alpha_stall": alpha_stall,
            "a0_2d": a0_2d, "a0_2d_raw": a0_2d_raw, "Ma": Ma,
            "aL0": aL0, "cd0": cd0, "cm0_2d": cm0_2d,
            "xcp0_2d": xcp0_2d, "cm_asa": cm_asa, "xcp_asa": xcp_asa,
        }

    return {
        "v": v, "c": c, "b": b, "peso_kg": peso_kg,
        "S": S, "AR": AR, "re_real": re_real, "cl_req": cl_req,
        "e_oswald": e_oswald, "kappa": kappa, "x_tr_pct": x_tr_pct,
        "Ma_info": Ma_info, "alphas": alphas, "asat_sel": asat_sel,
        "perfis_sel": perfis_sel, "resultados": resultados,
        "rho": rho, "V_SOM": V_SOM, "g": g,
        "altitude_m": altitude_m, "temp_C": temp_C,
        "mu": mu, "P_Pa": atm["P_Pa"], "T_K": atm["T_K"],
    }


# ---------------------------------------------------------------------------
# Multi-temperatura DESCONTINUADO — substituído por Sadraey+LLT
# As funções sutherland_viscosidade, propriedades_por_temperatura,
# calcular_asa_por_temperatura e calcular_asa_multi_temp foram movidas
# para aerodynamic_report.py (stubs de compatibilidade).
# ---------------------------------------------------------------------------
