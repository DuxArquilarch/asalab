# ================================================================= #
# AsalabXYZ — MÓDULO 1: DATABASE AERODINÂMICO                       #
# Física: Frank M. White, Fluid Mechanics, 8ª Ed.                   #
# ================================================================= #

import os, glob
import numpy as np

# ================================================================= #
# 0 — LEITOR DE POLARES XFLR5 (.csv)                                #
# Retorna dict: Re_int → (a0_2d, αL0, Cd0, Cm_médio, XCp_médio)    #
# Colunas esperadas: alpha, CL, CD, CDp, Cm, ..., XCp               #
# ================================================================= #

def _parse_xflr5_csv(path: str):
    """
    Lê uma polar XFLR5 e devolve (Re_int, dados_array).
    dados_array: ndarray (N,6) → [alpha, CL, CD, Cm, XCp, Top_Xtr]
    """
    re_val = None
    header_found = False
    col_map = {}
    rows = []

    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()

            # Extrai Reynolds da linha de metadados
            if "Re =" in line and re_val is None:
                for tok in line.split():
                    try:
                        candidate = float(tok)
                        if 0.01 <= candidate <= 100:   # valor em ×10⁶
                            re_val = int(round(candidate * 1e6))
                    except ValueError:
                        pass

            # Linha de cabeçalho das colunas
            if line.lower().startswith("alpha") and not header_found:
                header_found = True
                cols = [c.strip().lower() for c in line.split(",")]
                for name in ("alpha", "cl", "cd", "cm", "xcp", "top xtr"):
                    if name in cols:
                        col_map[name] = cols.index(name)
                continue

            # Linhas de dados
            if header_found and line and line[0].lstrip("-").isdigit():
                vals = [float(v) for v in line.split(",")]
                try:
                    row = [
                        vals[col_map["alpha"]],
                        vals[col_map["cl"]],
                        vals[col_map["cd"]],
                        vals[col_map.get("cm",   3)],
                        vals[col_map.get("xcp",  len(vals)-1)],
                        vals[col_map.get("top xtr", 5)] if "top xtr" in col_map else np.nan,
                    ]
                    rows.append(row)
                except (IndexError, KeyError):
                    pass

    if re_val is None or not rows:
        return None, None

    return re_val, np.array(rows, dtype=float)


def _ajustar_coeficientes(arr):
    """
    A partir do array (N,6) extrai (a0_2d, αL0, Cd0, Cm_med, XCp_med).
    a0_2d: inclinação linear de CL vs alpha (grau → 1/rad já convertido).
    αL0:   ângulo de sustentação nula (interpolado em CL=0).
    Cd0:   Cd no ponto de CL mínimo (aprox. arrasto parasita).
    """
    alpha = arr[:, 0]
    CL    = arr[:, 1]
    CD    = arr[:, 2]
    Cm    = arr[:, 3]
    XCp   = arr[:, 4]

    # Regressão linear CL x alpha na faixa linear (CL 0.1..0.9)
    mask = (CL >= 0.1) & (CL <= 0.9)
    if mask.sum() >= 2:
        p = np.polyfit(alpha[mask], CL[mask], 1)   # p[0] em 1/°
        a0_deg = p[0]
        aL0 = -p[1] / p[0]
    else:
        a0_deg = 0.1
        aL0 = 0.0

    a0_2d = float(a0_deg * (np.pi / 180.0))  # → 1/rad, mas guardamos em /deg internamente
    # OBS: o resto do código usa a0 em 1/° (×57.3 quando necessário)
    # Para manter compatibilidade mantemos em 1/° como DATABASE original
    a0_stored = float(a0_deg)

    # αL0 via interpolação em CL = 0
    if np.any(CL <= 0) and np.any(CL >= 0):
        aL0 = float(np.interp(0.0, CL, alpha))
    else:
        aL0 = float(aL0)

    # Cd0 ≈ Cd no CL mais próximo de zero
    idx_min = np.argmin(np.abs(CL))
    cd0 = float(CD[idx_min])

    # Cm e XCp médios na faixa de voo (CL 0.2..0.8)
    mask2 = (CL >= 0.2) & (CL <= 0.8)
    cm_med  = float(np.mean(Cm[mask2]))  if mask2.sum() > 0 else float(np.mean(Cm))
    xcp_med = float(np.mean(XCp[mask2])) if mask2.sum() > 0 else float(np.mean(XCp))

    return a0_stored, aL0, cd0, cm_med, xcp_med


def carregar_polares_xflr5(pasta: str = "."):
    """
    Varre `pasta` em busca de CSVs XFLR5 e devolve dict:
      nome_perfil → { Re_int: (a0_2d, αL0, Cd0, Cm_med, XCp_med), ... }
    O nome do perfil é lido da linha 'Calculated polar for:'.
    """
    perfis = {}
    for path in sorted(glob.glob(os.path.join(pasta, "*.csv"))):
        # Tenta ler nome do perfil
        nome = None
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if "Calculated polar for:" in line:
                    nome = line.split("Calculated polar for:")[-1].strip()
                    break
        if nome is None:
            nome = os.path.splitext(os.path.basename(path))[0]

        re_val, arr = _parse_xflr5_csv(path)
        if re_val is None:
            continue

        coefs = _ajustar_coeficientes(arr)
        if nome not in perfis:
            perfis[nome] = {}
        perfis[nome][re_val] = coefs          # (a0, αL0, cd0, cm, xcp)

    return perfis


# ================================================================= #
# 1 — DATABASE AERODINÂMICO (valores de referência)                  #
# Tupla: (a0_2d [1/°], αL0 [°], Cd0, Cm_med, XCp_med)              #
# Cm_med e XCp_med adicionados; retrocompat: se ausentes = (0, 0.25)#
# ================================================================= #
DATABASE = {
    # ── NACA 4 dígitos ────────────────────────────────────────────
    "NACA 4412": {
        50000:  (0.085, -3.8, 0.025, -0.092, 0.32),
        100000: (0.092, -3.9, 0.018, -0.095, 0.31),
        200000: (0.102, -4.0, 0.012, -0.098, 0.30),
        500000: (0.105, -4.0, 0.009, -0.099, 0.30),
    },
    "SELIG 1223": {
        50000:  (0.090, -7.0, 0.045, -0.148, 0.38),
        100000: (0.100, -7.5, 0.030, -0.152, 0.37),
        200000: (0.110, -8.0, 0.022, -0.158, 0.36),
        500000: (0.112, -8.2, 0.017, -0.160, 0.36),
    },
    "NACA 6412": {
        50000:  (0.095, -5.8, 0.032, -0.120, 0.34),
        100000: (0.102, -6.0, 0.022, -0.124, 0.33),
        200000: (0.108, -6.1, 0.015, -0.127, 0.33),
        500000: (0.110, -6.2, 0.011, -0.128, 0.32),
    },
    "CH10_S1210_30": {
        50000:  (0.0821, -3.80,  0.0753, -0.181, 0.52),
        100000: (0.0538, -14.78, 0.05561,-0.182, 0.51),
        200000: (0.0899, -13.02, 0.01646,-0.175, 0.49),
        500000: (0.0808, -14.97, 0.01029,-0.172, 0.48),
    },
    # ── NACA Blended ──────────────────────────────────────────────
    "NACA 6909_54.79%_6412": {
        50000:  (0.0677, -3.37, 0.0429, -0.100, 0.31),
        100000: (0.1040, -3.50, 0.0197, -0.102, 0.31),
        200000: (0.0910, -5.50, 0.0111, -0.108, 0.30),
        500000: (0.0864, -6.01, 0.0077, -0.110, 0.30),
    },
    # ── NACA 5 dígitos ────────────────────────────────────────────
    "NACA 23012": {
        50000:  (0.088, -1.2, 0.022, -0.010, 0.26),
        100000: (0.096, -1.3, 0.016, -0.011, 0.26),
        200000: (0.104, -1.4, 0.011, -0.012, 0.25),
        500000: (0.108, -1.4, 0.008, -0.012, 0.25),
    },
    "NACA 23015": {
        50000:  (0.086, -1.0, 0.026, -0.008, 0.26),
        100000: (0.094, -1.1, 0.019, -0.009, 0.26),
        200000: (0.102, -1.2, 0.013, -0.010, 0.25),
        500000: (0.106, -1.2, 0.010, -0.011, 0.25),
    },
    # ── NACA 6 dígitos ────────────────────────────────────────────
    "NACA 63-215": {
        50000:  (0.0850, -1.1, 0.024, -0.042, 0.27),
        100000: (0.0920, -1.2, 0.018, -0.044, 0.27),
        200000: (0.1050, -1.3, 0.012, -0.046, 0.26),
        500000: (0.1180, -1.4, 0.009, -0.048, 0.26),
    },
    "NACA 65-210": {
        50000:  (0.0720, -0.9, 0.019, -0.038, 0.26),
        100000: (0.0840, -1.0, 0.014, -0.040, 0.26),
        200000: (0.0980, -1.2, 0.008, -0.042, 0.25),
        500000: (0.1220, -1.3, 0.005, -0.044, 0.25),
    },
}

# ================================================================= #
# 2 — TIPOS DE ASA (AsaT)                                            #
# ================================================================= #
AsaT = {
    "1": "Retangular",
    "2": "Elíptica",
    "3": "Delta",
}

# ================================================================= #
# REFERÊNCIAS                                                        #
# ─ White, F. M. Fluid Mechanics, 8ª Ed. McGraw-Hill, 2016.         #
#   §8.1   Geometria NACA 4, 5 e 6 dígitos                          #
# ─ Abbott, I.H.; von Doenhoff, A.E. Theory of Wing Sections, 1959. #
# ─ XFLR5 v6 — Analysis Tool for Airfoils, Wings and Planes         #
# ================================================================= #
