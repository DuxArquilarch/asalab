# ================================================================= #
# AsalabXYZ — MÓDULO 4: MATERIAIS, PESO ESTRUTURAL E ANÁLISE        #
# DE PERDA PARA AERONAVES RC                                         #
#                                                                    #
# Referências principais:                                            #
#   Sadraey, M. Aircraft Design: A Systems Engineering Approach.     #
#     Wiley, 2013. Cap. 5 (aerodinâmica), Cap. 6 (peso),            #
#     §4.5 (stall), §3.5–3.6 (arrasto parasita).                    #
#   White, F.M. Fluid Mechanics, 8ª Ed. McGraw-Hill, 2016.          #
#     §8.3 (polar parabólica), §8.4 (Lifting Line).                 #
#   Raymer, D. Aircraft Design: A Conceptual Approach, 5ª Ed., 2012.#
# ================================================================= #

import numpy as np

# ── Importa as tabelas unificadas do database ──────────────────────
from database import MATERIAIS, CL_MAX_2D, CD0_PERFIL


# ================================================================= #
# CONSTANTES FÍSICAS                                                 #
# ================================================================= #
RHO   = 1.225    # kg/m³  — densidade do ar ISA ao nível do mar
G     = 9.81     # m/s²
MU    = 1.849e-5 # Pa·s   — viscosidade dinâmica do ar (White §1.7)


# ================================================================= #
# SEÇÃO 1 — BANCO DE MATERIAIS RC (agora em database.py)             #
# ─────────────────────────────────────────────────────────────────  #
# Cada material possui:                                              #
#   densidade_kg_m3  : kg/m³ (massa volumétrica)                    #
#   espessura_mm     : espessura típica da chapa/placa em mm         #
#   fator_construcao : fração da área S efetivamente preenchida      #
#                      (1.0 = chapa sólida, ~0.35 = nervuras+longarinas) #
#   cd0_rugosidade   : acréscimo de Cd0 pela rugosidade superficial  #
#                      (Sadraey §3.5, White §7.3)                    #
#   descricao        : texto livre                                   #
# ================================================================= #

# (MATERIAIS, CL_MAX_2D e CD0_PERFIL agora residem em database.py)

# ================================================================= #
# SEÇÃO 3 — FRAÇÕES DE PESO (Sadraey Cap. 6, Tabela 6.3)            #
# Adaptadas para RC < 50 kg com materiais variados                  #
# Fração = W_componente / MTOW                                      #
# ================================================================= #

FRACOES_BASE = {
    # Componente              : fração_madeira   fração_espuma   fração_composito
    # Estrutura da asa        : nervuras+longarinas+revestimento
    "asa":                     (0.135,            0.095,          0.085),
    # Fuselagem (corpo principal)
    "fuselagem":               (0.090,            0.070,          0.065),
    # Empenagem H + V (cauda)
    "empenagem":               (0.038,            0.028,          0.022),
    # Trem de pouso fixo (hastes + rodas + suporte)
    "trem_pouso":              (0.052,            0.048,          0.042),
    # Sistema propulsivo (motor + ESC + hélice)
    "propulsao":               (0.075,            0.075,          0.075),
    # Bateria LiPo
    "bateria":                 (0.095,            0.095,          0.095),
    # Servos + linkages + cabos
    "servos":                  (0.028,            0.028,          0.025),
    # Receptor + aviônica básica
    "avionica":                (0.012,            0.012,          0.010),
}

# Mapa: material → categoria de fração
def _categoria_material(nome_material: str) -> int:
    """
    Retorna índice da coluna de fração:
      0 = madeira, 1 = espuma/plástico, 2 = compósito
    """
    n = nome_material.lower()
    if any(k in n for k in ["fibra", "carbono", "cfrp", "glass"]):
        return 2
    if any(k in n for k in ["depron", "epp", "eps", "pla", "petg", "espuma"]):
        return 1
    return 0  # madeiras (balsa, compensado)


def fracoes_peso(nome_material: str) -> dict:
    """Retorna dict componente → fração de MTOW para o material dado."""
    idx = _categoria_material(nome_material)
    return {comp: vals[idx] for comp, vals in FRACOES_BASE.items()}


def fracao_estrutura_total(nome_material: str) -> float:
    return sum(fracoes_peso(nome_material).values())


# ================================================================= #
# SEÇÃO 4 — ESTIMATIVA DE MTOW E COMPONENTES                        #
# Sadraey Eq. 6.1: MTOW = W_payload / (1 - f_estrutura)            #
# ================================================================= #

def estimar_mtow(payload_kg: float, nome_material: str) -> float:
    f = fracao_estrutura_total(nome_material)
    return payload_kg / max(1.0 - f, 0.01)


def estimar_componentes(payload_kg: float, nome_material: str) -> dict:
    mtow   = estimar_mtow(payload_kg, nome_material)
    fracoes = fracoes_peso(nome_material)
    result = {comp: mtow * f for comp, f in fracoes.items()}
    result["payload"]        = payload_kg
    result["_mtow"]          = mtow
    result["_peso_vazio"]    = mtow - payload_kg
    result["_frac_estrutura"]= fracao_estrutura_total(nome_material)
    return result


# ================================================================= #
# SEÇÃO 5 — PESO DA ASA POR GEOMETRIA + MATERIAL                    #
# Cálculo físico direto: massa = ρ_mat × vol_efetivo                #
# vol_efetivo = S × e_mm/1000 × fator_construcao                   #
# ================================================================= #

def peso_asa_material(S: float, nome_material: str) -> float:
    """
    Peso físico estimado da asa (kg) com base na geometria e material.
    Serve como verificação cruzada com o método de fração (Sadraey).
    """
    mat  = MATERIAIS[nome_material]
    vol  = S * (mat["espessura_mm"] / 1000.0) * mat["fator_construcao"]
    return mat["densidade_kg_m3"] * vol


# ================================================================= #
# SEÇÃO 6 — CD0 TOTAL DA AERONAVE (Sadraey §3.5–3.6)               #
#                                                                    #
# CD0_total = CD0_perfil + CD0_fus + CD0_trem + CD0_empenagem       #
#           + CD0_rugosidade_material + CD0_interferencia            #
#                                                                    #
# Coeficientes de arrasto parasita por componente:                   #
#   Fuselagem caixa   : CD0_fus  = f_fus × (S_fus_frontal / S)      #
#   Trem fixo exposto : CD0_trem = CD_roda × (A_roda / S)           #
#   Empenagem         : CD0_emp  = 0.005 (Sadraey Tab. 3.7)         #
#   Interferência     : CD0_int  = 0.004 (Sadraey §3.6)             #
# ================================================================= #

def cd0_total(perfil: str, nome_material: str,
              S: float, c: float, b: float,
              com_trem: bool = True) -> dict:
    """
    Retorna dict com CD0 de cada componente e o total.
    Sadraey §3.5 Eq. 3.61; White §7.3.
    """
    # CD0 do perfil (asa limpa)
    cd0_perf = CD0_PERFIL.get(perfil, 0.010)

    # Rugosidade do material
    cd0_rug  = MATERIAIS[nome_material]["cd0_rugosidade"]

    # Fuselagem caixa: arrasto de forma elevado (corpo não-aerodinâmico)
    # Área frontal estimada: seção quadrada de lado ≈ 0.15×c
    lado_fus   = 0.15 * c          # m — estimativa caixa compacta
    S_fus_front = lado_fus**2      # m²
    Cf_fus     = 1.05              # coef. de forma caixa (Sadraey Tab. 3.5)
    cd0_fus    = Cf_fus * S_fus_front / S

    # Trem de pouso fixo (rodas expostas)
    # CD_roda ≈ 0.40 para roda circular (Sadraey §3.6, White §7.6)
    cd0_trem = 0.0
    if com_trem:
        d_roda   = 0.06            # diâmetro típico roda RC: 6 cm
        A_roda   = np.pi * (d_roda / 2)**2  # área frontal (1 roda)
        n_rodas  = 3               # 2 principais + 1 nariz
        cd0_trem = 0.40 * n_rodas * A_roda / S

    # Empenagem
    cd0_emp  = 0.005               # Sadraey Tab. 3.7

    # Interferência asa-fuselagem (junções)
    cd0_int  = 0.004               # Sadraey §3.6

    total = cd0_perf + cd0_rug + cd0_fus + cd0_trem + cd0_emp + cd0_int

    return {
        "cd0_perfil":      cd0_perf,
        "cd0_rugosidade":  cd0_rug,
        "cd0_fuselagem":   cd0_fus,
        "cd0_trem":        cd0_trem,
        "cd0_empenagem":   cd0_emp,
        "cd0_interferencia": cd0_int,
        "cd0_total":       total,
    }


# ================================================================= #
# SEÇÃO 7 — CL_MAX DA ASA FINITA (Sadraey §4.5 Eq. 4.28)           #
# CL_max_3D = 0.90 × CL_max_2D × k_AR × k_sweep × eta_flap         #
# k_AR: penalidade para AR < 6 (Sadraey Tabela 4.5)                 #
# k_sweep: sem enflechamento → 1.0                                   #
# eta_flap: sem flap → 1.0; com flap simples → 1.25                 #
# ================================================================= #

def cl_max_asa_finita(perfil: str, AR: float,
                      k_sweep: float = 1.0,
                      eta_flap: float = 1.0) -> float:
    cl2d  = CL_MAX_2D.get(perfil, 1.50)
    k_AR  = 1.0 - 0.5 * max(0.0, (6.0 - AR)) / 6.0
    return 0.90 * cl2d * k_AR * k_sweep * eta_flap


# ================================================================= #
# SEÇÃO 8 — VELOCIDADE DE STALL (Sadraey §4.5 Eq. 4.24)            #
# V_stall = sqrt(2·W·g / (ρ·S·CL_max))                             #
# ================================================================= #

def velocidade_stall(W_kg: float, S: float, CL_max: float) -> float:
    return float(np.sqrt(2.0 * W_kg * G / max(RHO * S * CL_max, 1e-6)))


# ================================================================= #
# SEÇÃO 9 — POLAR PARABÓLICA E DESEMPENHO                           #
# Sadraey Cap. 5; White §8.3                                        #
# ================================================================= #

def eficiencia_oswald(AR: float) -> float:
    """Raymer / White §8.3."""
    e = 1.78 * (1.0 - 0.045 * AR**0.68) - 0.64
    return float(np.clip(e, 0.60, 0.95))


def polar_e_desempenho(W_kg: float, S: float, AR: float,
                       velocidades: np.ndarray,
                       perfil: str, nome_material: str,
                       c: float, b: float,
                       com_trem: bool = True) -> dict:
    """
    Calcula CL, CD, L/D, Arrasto, Potência necessária
    para um vetor de velocidades.
    Sadraey Cap. 5; White §8.3.
    """
    e_oswald = eficiencia_oswald(AR)
    cd0_dict = cd0_total(perfil, nome_material, S, c, b, com_trem)
    CD0      = cd0_dict["cd0_total"]

    CL   = (2.0 * W_kg * G) / (RHO * velocidades**2 * S)
    CD_i = CL**2 / (np.pi * AR * e_oswald)
    CD   = CD0 + CD_i
    LD   = np.where(CD > 0, CL / CD, 0.0)
    D    = 0.5 * RHO * velocidades**2 * S * CD
    P    = D * velocidades  # Watts

    # Velocidade de máxima eficiência (Sadraey §5.4)
    CL_LD_max  = np.sqrt(np.pi * AR * e_oswald * CD0)
    V_LD_max   = float(np.sqrt(2.0 * W_kg * G / (RHO * S * CL_LD_max)))

    return {
        "velocidades": velocidades,
        "CL": CL, "CD": CD, "CD_i": CD_i,
        "L/D": LD, "D_N": D, "P_W": P,
        "e_oswald": e_oswald,
        "CD0": CD0,
        "CD0_dict": cd0_dict,
        "CL_LD_max": CL_LD_max,
        "V_LD_max": V_LD_max,
        "LD_max": float(np.max(LD[velocidades >= V_LD_max * 0.5])),
    }


# ================================================================= #
# SEÇÃO 10 — RELATÓRIO COMPLETO POR PERFIL + MATERIAL               #
# ================================================================= #

def _linha(char="─", n=70): print(char * n)
def _titulo(t): _linha("═"); print(f"   {t}"); _linha("═")
def _sec(t):    print(); _linha(); print(f"  ▶  {t}"); _linha()


def relatorio_completo(
    perfil:        str,
    nome_material: str,
    c:             float,
    b:             float,
    payload_kg:    float,
    v_max:         float,
    v_cruise:      float,
    com_trem:      bool = True,
    eta_flap:      float = 1.0,
):
    """
    Gera relatório completo de:
      1. Geometria
      2. Material selecionado
      3. Estimativa de peso (MTOW, componentes, peso físico da asa)
      4. CL_max e V_stall (Sadraey §4.5)
      5. Margens de segurança (Sadraey §4.5)
      6. CL requerido em cruzeiro e V_max
      7. Polar parabólica: CD0 por componente
      8. Desempenho: L/D, arrasto, potência
      9. Diagnósticos e alertas
    """

    # ── Geometria ────────────────────────────────────────────────
    S   = b * c
    AR  = b**2 / S
    Re  = RHO * v_cruise * c / MU

    # ── Peso ─────────────────────────────────────────────────────
    comps   = estimar_componentes(payload_kg, nome_material)
    mtow    = comps["_mtow"]
    W_vazio = comps["_peso_vazio"]
    f_est   = comps["_frac_estrutura"]
    W_asa_fisico = peso_asa_material(S, nome_material)

    # ── Aerodinâmica ─────────────────────────────────────────────
    cl_max_3d = cl_max_asa_finita(perfil, AR, eta_flap=eta_flap)
    v_stall   = velocidade_stall(mtow, S, cl_max_3d)
    margem_cruise = (v_cruise / v_stall) - 1.0
    margem_vmax   = (v_max   / v_stall) - 1.0

    cl_cruise = (2.0 * mtow * G) / (RHO * v_cruise**2 * S)
    cl_vmax   = (2.0 * mtow * G) / (RHO * v_max**2   * S)
    cl_max2d  = CL_MAX_2D.get(perfil, 1.50)

    # ── Polar e desempenho ───────────────────────────────────────
    vels = np.linspace(max(v_stall * 0.9, 5.0), v_max * 1.3, 80)
    perf = polar_e_desempenho(mtow, S, AR, vels, perfil,
                               nome_material, c, b, com_trem)
    cd0_d = perf["CD0_dict"]

    # Valores nos pontos de projeto
    def interp_vel(arr, v_alvo):
        return float(np.interp(v_alvo, vels, arr))

    LD_cruise = interp_vel(perf["L/D"], v_cruise)
    LD_vmax   = interp_vel(perf["L/D"], v_max)
    D_cruise  = interp_vel(perf["D_N"], v_cruise)
    D_vmax    = interp_vel(perf["D_N"], v_max)
    P_cruise  = interp_vel(perf["P_W"], v_cruise)
    P_vmax    = interp_vel(perf["P_W"], v_max)

    # ── Impressão ────────────────────────────────────────────────
    _titulo("AsalabXYZ — ANÁLISE RC: MATERIAIS · PESO · STALL")
    print("  Sadraey (2013) + White (2016) + Raymer (2012)")

    _sec("1. GEOMETRIA")
    print(f"  Perfil           : {perfil}")
    print(f"  Corda (c)        : {c:.3f} m")
    print(f"  Envergadura (b)  : {b:.3f} m")
    print(f"  Área alar (S)    : {S:.4f} m²")
    print(f"  Razão de aspecto : {AR:.2f}")
    print(f"  Re (cruzeiro)    : {Re:.0f}")

    _sec("2. MATERIAL SELECIONADO")
    mat = MATERIAIS[nome_material]
    print(f"  Material         : {nome_material}")
    print(f"  Densidade        : {mat['densidade_kg_m3']} kg/m³")
    print(f"  Espessura típica : {mat['espessura_mm']} mm")
    print(f"  Fator construção : {mat['fator_construcao']:.2f}")
    print(f"  ΔCd0 rugosidade  : {mat['cd0_rugosidade']:.4f}")
    print(f"  {mat['descricao']}")

    _sec("3. ESTIMATIVA DE PESO  [Sadraey Cap. 6, Eq. 6.1]")
    print(f"  Payload          : {payload_kg:.2f} kg")
    print(f"  Fração estrutural: {f_est*100:.1f}%")
    print(f"  MTOW estimado    : {mtow:.2f} kg")
    print(f"  Peso vazio (OEW) : {W_vazio:.2f} kg")
    print(f"  Peso físico asa* : {W_asa_fisico:.3f} kg  (* cálculo por volume)")
    print()
    print(f"  {'Componente':<35} {'Fração':>7}   {'Peso (kg)':>9}")
    _linha(" ", 58)
    for comp, peso in comps.items():
        if comp.startswith("_"): continue
        frac = fracoes_peso(nome_material).get(comp, 0.0)
        print(f"  {comp:<35} {frac*100:>6.1f}%   {peso:>9.3f}")
    _linha(" ", 58)
    print(f"  {'Estrutura vazia total':<35} {f_est*100:>6.1f}%   {W_vazio:>9.3f}")
    print(f"  {'MTOW':<35} {'100.0':>7}%   {mtow:>9.3f}")

    _sec("4. CL_MAX E VELOCIDADE DE STALL  [Sadraey §4.5 Eq. 4.24/4.28]")
    print(f"  CL_max 2D (perfil isolado) : {cl_max2d:.3f}")
    print(f"  CL_max 3D (asa finita AR={AR:.1f}): {cl_max_3d:.3f}")
    print(f"    [correção 3D = 0.90 × CL_max_2D × k_AR × η_flap]")
    print(f"  V_stall                    : {v_stall:.2f} m/s")

    _sec("5. MARGENS DE SEGURANÇA  [Sadraey §4.5 — mínimo 30%]")
    def semaforo(m):
        if   m >= 0.30: return "✅ OK"
        elif m >= 0.15: return "⚠️  ATENÇÃO"
        else:           return "❌ CRÍTICO"

    print(f"  V_cruzeiro = {v_cruise:.1f} m/s  →  "
          f"margem = {margem_cruise*100:.1f}%  {semaforo(margem_cruise)}")
    print(f"  V_max      = {v_max:.1f} m/s  →  "
          f"margem = {margem_vmax*100:.1f}%  {semaforo(margem_vmax)}")
    print(f"  Sadraey recomenda: V_cruise ≥ 1.30 × V_stall = "
          f"{v_stall*1.30:.2f} m/s")

    _sec("6. CL REQUERIDO  [White §8.3]")
    print(f"  CL_req @ V_cruise={v_cruise:.1f} m/s : {cl_cruise:.4f}  "
          f"({cl_cruise/cl_max_3d*100:.1f}% do CL_max)")
    print(f"  CL_req @ V_max   ={v_max:.1f} m/s : {cl_vmax:.4f}  "
          f"({cl_vmax/cl_max_3d*100:.1f}% do CL_max)")

    _sec("7. DECOMPOSIÇÃO DE CD0  [Sadraey §3.5–3.6]")
    total_cd0 = cd0_d["cd0_total"]
    for chave, val in cd0_d.items():
        if chave in ("cd0_total",): continue
        pct = val / total_cd0 * 100 if total_cd0 > 0 else 0
        print(f"  {chave:<28}: {val:.5f}  ({pct:.1f}%)")
    _linha(" ", 52)
    print(f"  {'CD0 TOTAL':<28}: {total_cd0:.5f}")

    _sec("8. DESEMPENHO NOS PONTOS DE PROJETO  [Sadraey Cap. 5]")
    print(f"  {'Parâmetro':<30} {'Cruzeiro':>12} {'V_max':>12}")
    _linha(" ", 58)
    print(f"  {'Velocidade (m/s)':<30} {v_cruise:>12.1f} {v_max:>12.1f}")
    print(f"  {'CL requerido':<30} {cl_cruise:>12.4f} {cl_vmax:>12.4f}")
    print(f"  {'L/D':<30} {LD_cruise:>12.2f} {LD_vmax:>12.2f}")
    print(f"  {'Arrasto D (N)':<30} {D_cruise:>12.1f} {D_vmax:>12.1f}")
    print(f"  {'Potência necessária (W)':<30} {P_cruise:>12.1f} {P_vmax:>12.1f}")
    print()
    print(f"  V_(L/D)_max = {perf['V_LD_max']:.2f} m/s  →  "
          f"(L/D)_max = {perf['LD_max']:.2f}")
    print(f"  e_Oswald = {perf['e_oswald']:.3f}  |  "
          f"CD0_total = {perf['CD0']:.5f}")

    _sec("9. DIAGNÓSTICOS E ALERTAS")
    alertas = []

    if mtow > 25.0:
        alertas.append(f"❌ MTOW={mtow:.1f} kg > 25 kg — verificar regulamentação ANAC/DECEA.")
    if margem_cruise < 0.15:
        alertas.append(f"❌ Margem de stall em cruzeiro CRÍTICA ({margem_cruise*100:.0f}%).")
    elif margem_cruise < 0.30:
        alertas.append(f"⚠️  Margem de stall em cruzeiro baixa ({margem_cruise*100:.0f}%).")
    if cl_cruise > 0.9 * cl_max_3d:
        alertas.append("❌ CL_cruise > 90% do CL_max — risco iminente de stall em turbulência.")
    elif cl_cruise > 0.75 * cl_max_3d:
        alertas.append("⚠️  CL_cruise > 75% do CL_max — manobras limitadas.")
    if P_vmax > 400:
        alertas.append(f"⚠️  Potência em V_max = {P_vmax:.0f} W — verifique motor/bateria.")
    if W_asa_fisico > comps.get("asa", 0) * 1.5:
        alertas.append(
            f"⚠️  Peso físico da asa ({W_asa_fisico:.2f} kg) excede "
            f"estimativa por fração ({comps.get('asa',0):.2f} kg) em >50%."
        )
    if LD_cruise < 8.0:
        alertas.append(f"⚠️  L/D em cruzeiro = {LD_cruise:.1f} — eficiência baixa para carga útil alta.")

    if not alertas:
        alertas.append("✅ Nenhum alerta crítico. Projeto dentro dos parâmetros nominais.")

    for a in alertas:
        print(f"  {a}")

    _linha("═")
    print("  REFERÊNCIAS USADAS NESTE MÓDULO")
    _linha()
    print("  Sadraey §3.5–3.6  Arrasto parasita por componente")
    print("  Sadraey §4.5      CL_max, V_stall, margens de segurança")
    print("  Sadraey Cap. 6    Estimativa de peso por fração")
    print("  White  §7.3       Rugosidade superficial → Cd0")
    print("  White  §8.3       Polar parabólica, e_Oswald")
    print("  White  §8.4       Lifting Line — CL_max da asa finita")
    print("  Abbott & von Doenhoff — Theory of Wing Sections, 1959")
    _linha("═")

    return {
        "mtow": mtow, "W_vazio": W_vazio, "W_asa_fisico": W_asa_fisico,
        "v_stall": v_stall, "cl_max_3d": cl_max_3d,
        "margem_cruise": margem_cruise, "margem_vmax": margem_vmax,
        "cl_cruise": cl_cruise, "cl_vmax": cl_vmax,
        "LD_cruise": LD_cruise, "LD_vmax": LD_vmax,
        "P_cruise_W": P_cruise, "P_vmax_W": P_vmax,
        "D_cruise_N": D_cruise, "D_vmax_N": D_vmax,
        "perf": perf, "cd0_dict": cd0_d,
        "S": S, "AR": AR,
    }


# ================================================================= #
# SEÇÃO 11 — COMPARAÇÃO ENTRE MATERIAIS (mesmo perfil)              #
# ================================================================= #

def comparar_materiais(
    perfil:     str,
    materiais:  list,
    c:          float,
    b:          float,
    payload_kg: float,
    v_max:      float,
    v_cruise:   float,
    com_trem:   bool = True,
):
    """
    Imprime tabela comparativa de todos os materiais em `materiais`
    para o mesmo perfil e geometria.
    """
    S  = b * c
    AR = b**2 / S

    _titulo(f"COMPARAÇÃO DE MATERIAIS — Perfil: {perfil}  |  AR={AR:.1f}  |  "
            f"Payload={payload_kg} kg")

    cab = (f"  {'Material':<30} {'MTOW':>7} {'Wvazio':>7} "
           f"{'Vstall':>8} {'Mgcruise':>10} {'LDcruz':>7} "
           f"{'Pmax(W)':>8} {'CD0':>8}")
    print(cab)
    _linha(" ", len(cab) - 2)

    resultados = {}
    for mat in materiais:
        if mat not in MATERIAIS:
            print(f"  [AVISO] Material '{mat}' não encontrado. Pulando.")
            continue
        comps   = estimar_componentes(payload_kg, mat)
        mtow    = comps["_mtow"]
        W_vazio = comps["_peso_vazio"]
        cl_max3 = cl_max_asa_finita(perfil, AR)
        vstall  = velocidade_stall(mtow, S, cl_max3)
        mg_c    = (v_cruise / vstall) - 1.0
        perf    = polar_e_desempenho(mtow, S, AR,
                                     np.array([v_cruise, v_max]),
                                     perfil, mat, c, b, com_trem)
        ld_c  = float(perf["L/D"][0])
        p_max = float(perf["P_W"][1])
        cd0   = perf["CD0"]

        flag_mg = "✅" if mg_c >= 0.30 else ("⚠️" if mg_c >= 0.15 else "❌")

        print(f"  {mat:<30} {mtow:>6.1f}  {W_vazio:>6.1f}  "
              f"{vstall:>7.2f}  {mg_c*100:>8.1f}% {flag_mg}  "
              f"{ld_c:>6.1f}  {p_max:>8.0f}  {cd0:.5f}")

        resultados[mat] = {
            "mtow": mtow, "W_vazio": W_vazio, "v_stall": vstall,
            "margem_cruise": mg_c, "LD_cruise": ld_c, "P_vmax": p_max,
        }

    _linha()
    print("  Mgcruise = margem de stall em cruzeiro (≥30% recomendado, Sadraey §4.5)")
    return resultados


# ================================================================= #
# SEÇÃO 12 — COMPARAÇÃO ENTRE PERFIS (mesmo material)               #
# ================================================================= #

def comparar_perfis(
    perfis:        list,
    nome_material: str,
    c:             float,
    b:             float,
    payload_kg:    float,
    v_max:         float,
    v_cruise:      float,
    com_trem:      bool = True,
):
    """
    Tabela comparativa de perfis para o mesmo material.
    Integra com CL_MAX_2D e CD0_PERFIL internos.
    """
    S  = b * c
    AR = b**2 / S
    comps = estimar_componentes(payload_kg, nome_material)
    mtow  = comps["_mtow"]

    _titulo(f"COMPARAÇÃO DE AEROFÓLIOS — Material: {nome_material}  |  "
            f"MTOW={mtow:.1f} kg  |  AR={AR:.1f}")

    cab = (f"  {'Perfil':<28} {'CLmax2D':>8} {'CLmax3D':>8} "
           f"{'Vstall':>8} {'CLreq':>7} {'Mgcruise':>10} "
           f"{'LDmax':>7} {'CD0perf':>9}")
    print(cab)
    _linha(" ", len(cab) - 2)

    resultados = {}
    for perf in perfis:
        if perf not in CL_MAX_2D:
            print(f"  [AVISO] Perfil '{perf}' sem CL_max cadastrado. Pulando.")
            continue
        cl2d  = CL_MAX_2D[perf]
        cl3d  = cl_max_asa_finita(perf, AR)
        vs    = velocidade_stall(mtow, S, cl3d)
        cl_cr = (2.0 * mtow * G) / (RHO * v_cruise**2 * S)
        mg_c  = (v_cruise / vs) - 1.0
        e_osw = eficiencia_oswald(AR)
        cd0_p = CD0_PERFIL.get(perf, 0.010)
        cl_ld = np.sqrt(np.pi * AR * e_osw * cd0_p)
        ld_mx = cl_ld / (2.0 * cd0_p)

        flag  = "✅" if mg_c >= 0.30 else ("⚠️" if mg_c >= 0.15 else "❌")

        print(f"  {perf:<28} {cl2d:>8.3f} {cl3d:>8.3f} "
              f"{vs:>8.2f} {cl_cr:>7.4f} "
              f"{mg_c*100:>8.1f}% {flag}  "
              f"{ld_mx:>6.1f}  {cd0_p:>9.5f}")

        resultados[perf] = {
            "cl_max_2d": cl2d, "cl_max_3d": cl3d,
            "v_stall": vs, "cl_req_cruise": cl_cr,
            "margem_cruise": mg_c, "LD_max": ld_mx,
        }

    _linha()
    print("  CLreq = CL requerido em cruzeiro (fixo para todos os perfis, mesmo MTOW)")
    return resultados


# ================================================================= #
# SEÇÃO 13 — INTERFACE DE MENU                                       #
# ================================================================= #

def _menu_materiais():
    print("\n  MATERIAIS DISPONÍVEIS:")
    nomes = list(MATERIAIS.keys())
    for i, n in enumerate(nomes, 1):
        d = MATERIAIS[n]["densidade_kg_m3"]
        print(f"    [{i:>2}]  {n:<35}  {d} kg/m³")
    return nomes


def _menu_perfis_ext():
    """Lista perfis com CL_max cadastrado."""
    print("\n  AEROFÓLIOS DISPONÍVEIS (com CL_max e CD0):")
    nomes = list(CL_MAX_2D.keys())
    for i, n in enumerate(nomes, 1):
        print(f"    [{i:>2}]  {n:<35}  CLmax={CL_MAX_2D[n]:.2f}  CD0={CD0_PERFIL.get(n,0):.4f}")
    return nomes


def menu_interativo():
    """Menu de texto para análise RC interativa."""
    _titulo("AsalabXYZ — MÓDULO 4: MATERIAIS + PESO + STALL")

    # Parâmetros geométricos
    print("\n  Geometria e missão (valores padrão: 15 0.6 3.0 20 12)")
    print("  Entrada: v_max  corda  envergadura  payload  v_cruise")
    raw = input("  → ").strip() or "15 0.6 3.0 20 12"
    nums = [float(x) for x in raw.split()]
    v_max, c, b, payload, v_cruise = nums[0], nums[1], nums[2], nums[3], nums[4]

    # Trem de pouso
    print("\n  Incluir trem de pouso fixo? [s/n] (padrão: s)")
    com_trem = input("  → ").strip().lower() not in ("n", "nao", "não")

    # Seleção de modo
    print("\n  MODO:")
    print("    [1]  Análise completa (1 perfil + 1 material)")
    print("    [2]  Comparar materiais (1 perfil)")
    print("    [3]  Comparar aerofólios (1 material)")
    modo = input("  → ").strip() or "1"

    lista_perf = _menu_perfis_ext()
    lista_mat  = _menu_materiais()

    if modo == "1":
        print("\n  Número do perfil:")
        ip = int(input("  → ").strip() or "1") - 1
        print("\n  Número do material:")
        im = int(input("  → ").strip() or "1") - 1
        relatorio_completo(
            lista_perf[ip], lista_mat[im],
            c, b, payload, v_max, v_cruise, com_trem
        )

    elif modo == "2":
        print("\n  Número do perfil:")
        ip = int(input("  → ").strip() or "1") - 1
        print("\n  Números dos materiais (ex: 1 2 3):")
        ims = [int(x)-1 for x in input("  → ").strip().split()]
        mats = [lista_mat[i] for i in ims if 0 <= i < len(lista_mat)]
        comparar_materiais(lista_perf[ip], mats, c, b, payload, v_max, v_cruise, com_trem)

    elif modo == "3":
        print("\n  Números dos perfis (ex: 1 2 4):")
        ips = [int(x)-1 for x in input("  → ").strip().split()]
        perfis_sel = [lista_perf[i] for i in ips if 0 <= i < len(lista_perf)]
        print("\n  Número do material:")
        im = int(input("  → ").strip() or "1") - 1
        comparar_perfis(perfis_sel, lista_mat[im], c, b, payload, v_max, v_cruise, com_trem)

    else:
        print("  [ERRO] Modo inválido.")


# ================================================================= #
# PONTO DE ENTRADA                                                   #
# ================================================================= #

if __name__ == "__main__":
    menu_interativo()


# ================================================================= #
# REFERÊNCIAS                                                        #
# ─ Sadraey, M. Aircraft Design: A Systems Engineering Approach.    #
#   John Wiley & Sons, 2013.                                        #
#   §3.5–3.6  Arrasto parasita por componente (CD0)                 #
#   §4.5      CL_max, V_stall (Eq. 4.24, 4.28), margens de segur.  #
#   Cap. 6    Estimativa de peso por fração (Eq. 6.1, Tab. 6.3)     #
# ─ White, F.M. Fluid Mechanics, 8ª Ed. McGraw-Hill, 2016.          #
#   §7.3      Rugosidade superficial e CD0                           #
#   §8.3      Polar parabólica, fator de Oswald                     #
#   §8.4      Lifting Line — CL_max asa finita                      #
# ─ Raymer, D. Aircraft Design: A Conceptual Approach, 5ª Ed., 2012.#
# ─ Abbott, I.H.; von Doenhoff, A.E. Theory of Wing Sections, 1959. #
# ─ UIUC Airfoil Database — Selig et al.                            #
# ================================================================= #
