# ================================================================= #
# AsalabXYZ — MÓDULO 2: CÁLCULOS AERODINÂMICOS                      #
# Física: Frank M. White, Fluid Mechanics, 8ª Ed.                   #
# ================================================================= #

import numpy as np
from database import DATABASE, AsaT


# ================================================================= #
# CORREÇÃO PELO TIPO DE ASA (AsaT)                                   #
# ================================================================= #

def correcao_asat(forma, AR):
    """
    Retorna (e_override, kappa) segundo o tipo de asa (AsaT).

    Retangular (White §8.3): e_Oswald padrão; κ = 1.0
    Elíptica (White §8.4):   e = 1.0; κ = 1.0
    Delta (White §8.8):      e empírico ≈ 0.80–0.85; κ = 0.90
    """
    if forma == "Elíptica":
        return 1.0, 1.0
    elif forma == "Delta":
        e_delta = float(np.clip(0.82 * (1 - 0.02 * AR), 0.60, 0.88))
        return e_delta, 0.90
    else:  # Retangular
        return None, 1.0


# ================================================================= #
# FUNÇÕES DE APOIO                                                   #
# ================================================================= #

def interpolar_coeficientes(re_alvo, dados_perfil):
    """Interpolação linear de (a0_2d, αL0, Cd0). White §7.1."""
    res_sorted = sorted(dados_perfil.keys())
    if re_alvo <= res_sorted[0]:
        return np.array(dados_perfil[res_sorted[0]], dtype=float)
    if re_alvo >= res_sorted[-1]:
        return np.array(dados_perfil[res_sorted[-1]], dtype=float)
    for i in range(len(res_sorted) - 1):
        re0, re1 = res_sorted[i], res_sorted[i + 1]
        if re0 <= re_alvo <= re1:
            v0 = np.array(dados_perfil[re0], dtype=float)
            v1 = np.array(dados_perfil[re1], dtype=float)
            return v0 + (re_alvo - re0) * (v1 - v0) / (re1 - re0)


def eficiencia_oswald(AR):
    """e ≈ 1.78·(1 − 0.045·AR^0.68) − 0.64  (White §8.3 / Raymer)."""
    e = 1.78 * (1 - 0.045 * AR**0.68) - 0.64
    return float(np.clip(e, 0.60, 0.95))


def correcao_prandtl_glauert(a0_2d, v, v_som=340.0):
    """a0_corr = a0 / √(1 − Ma²)  (White §8.7)."""
    Ma = v / v_som
    if Ma >= 0.7:
        print(f"  [AVISO] Ma = {Ma:.2f} ≥ 0.7 — correção P-G não é precisa.")
    beta = np.sqrt(max(1.0 - Ma**2, 0.01))
    return a0_2d / beta, Ma


def ponto_transicao(v, c, rho, mu):
    """Transição lam→turb pelo critério de Michel (White §7.4)."""
    RE_TRANS = 5e5
    x_tr = RE_TRANS * mu / (rho * v)
    return float(np.clip(x_tr / c * 100, 0.0, 100.0))


def campo_velocidade_biot_savart(xp, yp, offset, gamma_0):
    """v_ind = Γ / (2π·r)  — vórtice pontual 2-D (White §8.6)."""
    xc = offset + 0.25
    r = np.sqrt((xp - xc)**2 + yp**2) + 0.02
    v_ind = gamma_0 / (2.0 * np.pi * r)
    dist = v_ind * 0.006 * np.sign(yp) * np.where(
        ((xp - offset) > -0.15) & ((xp - offset) < 1.2), 1.0, 0.0)
    return dist


# ================================================================= #
# CÁLCULO PRINCIPAL POR PERFIL                                       #
# ================================================================= #

def calcular_perfil(perfil, alphas, re_real, asat_sel, e_oswald, kappa, v, V_SOM, cl_req=None):
    """
    Executa todos os cálculos aerodinâmicos para um perfil.

    Retorna dict com: cl_asa, cd_tot, eff, ld_max, alpha_stall,
                      a0_2d, a0_2d_raw, Ma, aL0, cd0
    """
    a0_2d_raw, aL0, cd0 = interpolar_coeficientes(re_real, DATABASE[perfil])
    a0_2d, Ma = correcao_prandtl_glauert(a0_2d_raw, v, V_SOM)

    # Lifting Line / VLM delta (White §8.4, §8.8)
    if asat_sel == "Delta" and (alphas[-1] - alphas[0]) >= 0:
        AR_est = e_oswald  # placeholder — AR real é passado via e_oswald já calculado
    # Calcula a_asa (inclinação de sustentação da asa finita)
    a_llt = a0_2d / (1.0 + (57.3 * a0_2d) / (np.pi * e_oswald * 1.0))  # AR interno

    cl_asa  = a_llt * kappa * (alphas - aL0)
    cd_tot  = cd0 + (cl_asa**2) / (np.pi * e_oswald)   # π·AR·e já embutido via e_oswald
    eff     = np.where(cl_asa > 0, cl_asa / np.maximum(cd_tot, 0.001), 0.0)
    cl_star = np.sqrt(np.pi * e_oswald * cd0)
    ld_max  = cl_star / (2.0 * cd0)
    alpha_stall = ((1.2 + 0.12) / (a_llt * kappa)) + aL0

    return {
        "cl_asa":       cl_asa,
        "cd_tot":       cd_tot,
        "eff":          eff,
        "ld_max":       ld_max,
        "alpha_stall":  alpha_stall,
        "a0_2d":        a0_2d,
        "a0_2d_raw":    a0_2d_raw,
        "Ma":           Ma,
        "aL0":          aL0,
        "cd0":          cd0,
    }


def calcular_asa(v, c, b, peso_kg, perfis_sel, asat_sel):
    """
    Ponto de entrada: calcula todos os parâmetros da asa.
    Retorna dict pronto para ser consumido pelo módulo de análise/gráficos.
    """
    # ── Constantes físicas (White §1.6, §1.7) ─────────────────────
    g     = 9.81
    rho   = 1.225
    mu    = 1.849e-5
    V_SOM = 340.0

    # ── Geometria (White §8.2) ─────────────────────────────────────
    S  = b * c
    AR = b**2 / S

    # ── Reynolds (White §7.1) ──────────────────────────────────────
    re_real = (rho * v * c) / mu

    # ── CL de cruzeiro (White §8.3) ───────────────────────────────
    cl_req = (2.0 * peso_kg * g) / (rho * v**2 * S)

    # ── Oswald base + correção AsaT ───────────────────────────────
    e_base = eficiencia_oswald(AR)
    e_override, kappa = correcao_asat(asat_sel, AR)
    e_oswald = e_override if e_override is not None else e_base

    # ── Transição (White §7.4) ────────────────────────────────────
    x_tr_pct = ponto_transicao(v, c, rho, mu)

    alphas  = np.linspace(-6, 16, 150)
    Ma_info = v / V_SOM

    print(f"\n  Re = {re_real:.0f}  |  AR = {AR:.2f}  |  e_Oswald = {e_oswald:.3f}")
    print(f"  CL_req = {cl_req:.4f}  |  AsaT: {asat_sel}  |  κ = {kappa:.2f}")
    print(f"  Ma = {Ma_info:.3f}  |  Transição lam→turb: {x_tr_pct:.1f}% da corda")

    # ── Cálculo por perfil ────────────────────────────────────────
    resultados = {}
    for perfil in perfis_sel:
        a0_2d_raw, aL0, cd0 = interpolar_coeficientes(re_real, DATABASE[perfil])
        a0_2d, Ma = correcao_prandtl_glauert(a0_2d_raw, v, V_SOM)

        if asat_sel == "Delta" and AR < 3.0:
            a_asa_delta = np.pi * AR / 2.0
            blend = AR / 3.0
            a_llt = a0_2d / (1.0 + (57.3 * a0_2d) / (np.pi * e_oswald * AR))
            a_asa = (1 - blend) * a_asa_delta + blend * a_llt
        else:
            a_asa = a0_2d / (1.0 + (57.3 * a0_2d) / (np.pi * e_oswald * AR))

        a_asa   *= kappa
        cl_asa   = a_asa * (alphas - aL0)
        cd_tot   = cd0 + (cl_asa**2) / (np.pi * AR * e_oswald)
        eff      = np.where(cl_asa > 0, cl_asa / np.maximum(cd_tot, 0.001), 0.0)
        cl_star  = np.sqrt(np.pi * AR * e_oswald * cd0)
        ld_max   = cl_star / (2.0 * cd0)
        alpha_stall = ((1.2 + 0.12 * AR) / a_asa) + aL0

        resultados[perfil] = {
            "cl_asa":      cl_asa,
            "cd_tot":      cd_tot,
            "eff":         eff,
            "ld_max":      ld_max,
            "alpha_stall": alpha_stall,
            "a0_2d":       a0_2d,
            "a0_2d_raw":   a0_2d_raw,
            "Ma":          Ma,
            "aL0":         aL0,
            "cd0":         cd0,
        }

    return {
        "v": v, "c": c, "b": b, "peso_kg": peso_kg,
        "S": S, "AR": AR,
        "re_real": re_real,
        "cl_req": cl_req,
        "e_oswald": e_oswald,
        "kappa": kappa,
        "x_tr_pct": x_tr_pct,
        "Ma_info": Ma_info,
        "alphas": alphas,
        "asat_sel": asat_sel,
        "perfis_sel": perfis_sel,
        "resultados": resultados,
        # constantes físicas repassadas para uso nos gráficos
        "rho": rho, "V_SOM": V_SOM, "g": 9.81,
    }


# ================================================================= #
# REFERÊNCIAS                                                        #
# ─ White, F. M. Fluid Mechanics, 8ª Ed. McGraw-Hill, 2016.         #
#   §7.1   Número de Reynolds                                        #
#   §7.4   Transição laminar→turbulento (critério de Michel)         #
#   §8.3   Polar parabólica, arrasto induzido, fator de Oswald       #
#   §8.4   Lifting Line de Prandtl — CL_α de asa finita             #
#   §8.6   Teoria do vórtice sustentador — Biot-Savart              #
#   §8.7   Correção de Prandtl-Glauert (compressibilidade)          #
#   §8.8   Asas delta — modelo VLM de baixo AR                      #
# ─ Raymer, D. Aircraft Design: A Conceptual Approach, 5ª Ed., 2012. #
# ================================================================= #
