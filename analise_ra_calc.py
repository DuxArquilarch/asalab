# ================================================================= #
# Dark Wing Project — MÓDULO: CÁLCULOS GEOMÉTRICOS / RA                    #
#                                                                    #
# Separado de analise_graficos.py.                                  #
# Contém: geometria de perfis NACA, silhueta da asa,               #
#         e derivação de c/b a partir de RA e S.                    #
# ================================================================= #

import numpy as np


# ----------------------------------------------------------------- #
# GEOMETRIA DO PERFIL (White §8.1)                                  #
# ----------------------------------------------------------------- #

def gerar_coord_naca(nome):
    """Retorna (x, y_upper, y_lower) para o perfil NACA dado."""
    x = np.linspace(0, 1, 101)

    def thickness(t):
        return 5 * t * (
            0.2969 * np.sqrt(x)
            - 0.1260 * x
            - 0.3516 * x ** 2
            + 0.2843 * x ** 3
            - 0.1015 * x ** 4
        )

    u = nome.upper()
    if "23012" in u:
        r, k1 = 0.2025, 15.957
        yc = np.where(x < r,
                      k1 / 6 * (x ** 3 - 3 * r * x ** 2 + r ** 2 * (3 - r) * x),
                      k1 * r ** 3 / 6 * (1 - x))
        yt = thickness(0.12)
    elif "23015" in u:
        r, k1 = 0.2025, 15.957
        yc = np.where(x < r,
                      k1 / 6 * (x ** 3 - 3 * r * x ** 2 + r ** 2 * (3 - r) * x),
                      k1 * r ** 3 / 6 * (1 - x))
        yt = thickness(0.15)
    elif "63-2" in u or "632" in u:
        m, p = 0.02, 0.35
        yc = np.where(x < p,
                      m / p ** 2 * (2 * p * x - x ** 2),
                      m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x - x ** 2))
        yt = thickness(0.15)
    elif "65-2" in u or "652" in u:
        m, p = 0.015, 0.40
        yc = np.where(x < p,
                      m / p ** 2 * (2 * p * x - x ** 2),
                      m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x - x ** 2))
        yt = thickness(0.10)
    elif "4412" in u:
        m, p = 0.04, 0.4
        yc = np.where(x < p,
                      m / p ** 2 * (2 * p * x - x ** 2),
                      m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x - x ** 2))
        yt = thickness(0.12)
    elif "6412" in u:
        m, p = 0.06, 0.4
        yc = np.where(x < p,
                      m / p ** 2 * (2 * p * x - x ** 2),
                      m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x - x ** 2))
        yt = thickness(0.12)
    elif "1223" in u:
        m, p = 0.11, 0.2
        yc = np.where(x < p,
                      m / p ** 2 * (2 * p * x - x ** 2),
                      m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x - x ** 2))
        yt = thickness(0.23)
    else:
        m, p = 0.05, 0.5
        yc = np.where(x < p,
                      m / p ** 2 * (2 * p * x - x ** 2),
                      m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x - x ** 2))
        yt = thickness(0.15)

    return x, yc + yt, yc - yt


# ----------------------------------------------------------------- #
# SILHUETA DA ASA                                                    #
# ----------------------------------------------------------------- #

def gerar_silhueta_asat(forma, b, c):
    """Retorna (xs, ys) para plotar silhueta da asa (semi-envergadura)."""
    if forma == "Retangular":
        return [0, b / 2, b / 2, 0, 0], [0, 0, c, c, 0]
    elif forma == "Elíptica":
        th = np.linspace(0, np.pi, 120)
        return (list((b / 2) * np.sin(th)) + [0],
                list(c * np.cos(th) / 2 + c / 2) + [c / 2])
    else:  # Delta
        return [0, b / 2, 0, 0], [0, c / 2, c, 0]


# ----------------------------------------------------------------- #
# DERIVAÇÃO GEOMÉTRICA A PARTIR DE RA + S (usado pela aba GEO)      #
# ----------------------------------------------------------------- #

def geometria_de_ra_e_s(ra: float, s: float):
    """
    Dado RA = b²/S e área S, devolve corda c e envergadura b.

    Returns
    -------
    dict com 'b', 'c', 'AR', 'S'
    """
    if ra <= 0 or s <= 0:
        raise ValueError("RA e S devem ser positivos.")
    b = float(np.sqrt(ra * s))
    c = float(s / b)
    return {"b": b, "c": c, "AR": ra, "S": s}
