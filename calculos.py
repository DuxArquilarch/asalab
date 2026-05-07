import numpy as np
from database import DATABASE

# Constantes físicas
g      = 9.81
R_AR   = 287.05
GAMMA  = 1.4
MU_0   = 1.716e-5
T_0    = 273.15
S_SUTH = 110.4


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
    if re_alvo <= res_sorted[0]:
        raw = dados_perfil[res_sorted[0]]
    elif re_alvo >= res_sorted[-1]:
        raw = dados_perfil[res_sorted[-1]]
    else:
        for i in range(len(res_sorted) - 1):
            re0, re1 = res_sorted[i], res_sorted[i + 1]
            if re0 <= re_alvo <= re1:
                v0 = np.array(dados_perfil[re0], dtype=float)
                v1 = np.array(dados_perfil[re1], dtype=float)
                raw = v0 + (re_alvo - re0) * (v1 - v0) / (re1 - re0)
                break
    raw = np.array(raw, dtype=float)
    if raw.size == 3:
        raw = np.append(raw, [-0.05, 0.25])
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
# Cálculo ISA padrão
# ---------------------------------------------------------------------------
def calcular_asa(v, c, b, peso_kg, perfis_sel, asat_sel):
    rho   = 1.084
    mu    = 1.849e-5
    V_SOM = 340.0

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
    }


# ---------------------------------------------------------------------------
# Multi-temperatura (Lei de Sutherland)
# ---------------------------------------------------------------------------
def sutherland_viscosidade(T_K):
    return MU_0 * (T_K / T_0) ** 1.5 * (T_0 + S_SUTH) / (T_K + S_SUTH)


def propriedades_por_temperatura(T_C, P_Pa=101325.0):
    T_K = T_C + 273.15
    rho = P_Pa / (R_AR * T_K)
    mu  = sutherland_viscosidade(T_K)
    a   = np.sqrt(GAMMA * R_AR * T_K)
    return {"T_C": T_C, "T_K": T_K, "P_Pa": P_Pa, "rho": rho,
            "mu": mu, "v_som": a}


def calcular_asa_por_temperatura(v, c, b, peso_kg, perfis_sel, asat_sel, T_C, P_Pa=101325.0):
    prop  = propriedades_por_temperatura(T_C, P_Pa)
    rho   = prop["rho"]
    mu    = prop["mu"]
    V_SOM = prop["v_som"]

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
        "rho": rho, "V_SOM": V_SOM, "g": g, "T_C": T_C,
    }


def calcular_asa_multi_temp(v, c, b, peso_kg, perfis_sel, asat_sel,
                            temp_min=15.0, temp_max=30.0, temp_step=1.0, P_Pa=101325.0):
    temperaturas = np.arange(temp_min, temp_max + temp_step/2, temp_step)
    resultado = {"temperaturas": temperaturas, "dados": {}}
    for T in temperaturas:
        resultado["dados"][float(T)] = calcular_asa_por_temperatura(
            v, c, b, peso_kg, perfis_sel, asat_sel, T, P_Pa)
    return resultado