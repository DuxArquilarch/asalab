# ================================================================= #
# Dark Wing Project — MÓDULO: CÁLCULOS GEOMÉTRICOS / RA             #
# ================================================================= #

import numpy as np

# ----------------------------------------------------------------- #
# AIRFOIL LIST — kept in sync with database.DATABASE                 #
# Updated at runtime by cli.py / gui.py after any DB change.        #
# ----------------------------------------------------------------- #
AIRFOILS_AVAILABLE = []   # populated by _refresh_airfoils()

def _refresh_airfoils():
    """Re-read DATABASE keys and update AIRFOILS_AVAILABLE in place."""
    global AIRFOILS_AVAILABLE
    try:
        import importlib, sys
        mod = sys.modules.get("database") or importlib.import_module("database")
        AIRFOILS_AVAILABLE[:] = list(mod.DATABASE.keys())
    except Exception:
        pass

_refresh_airfoils()


# ----------------------------------------------------------------- #
# GEOMETRY (White §8.1)                                              #
# ----------------------------------------------------------------- #

#Tab visualizer
def gerar_coord_naca(nome):
    """Returns (x, y_upper, y_lower) for the given airfoil name.
    Handles standard NACA 4-digit strings and sets dynamic defaults for custom curves.
    """
    x = np.linspace(0, 1, 101)

    def thickness(t):
        return 5 * t * (
            0.2969 * np.sqrt(x)
            - 0.1260 * x
            - 0.3516 * x ** 2
            + 0.2843 * x ** 3
            - 0.1015 * x ** 4
        )

    def camber_4digit(m, p):
        yc = np.zeros_like(x)
        if p == 0:
            return yc
        idx = x <= p
        yc[idx] = (m / p**2) * (2 * p * x[idx] - x[idx]**2)
        yc[~idx] = (m / (1 - p)**2) * ((1 - 2 * p) + 2 * p * x[~idx] - x[~idx]**2)
        return yc

    # --- Airfoil Geometry Extraction Logic ---
    nome_upper = nome.upper()
    digits = "".join(filter(str.isdigit, nome_upper))
    
    if "NACA" in nome_upper and len(digits) >= 4:
        # Standard NACA 4-Digit Parser
        m = int(digits[0]) / 100.0
        p = int(digits[1]) / 10.0 if int(digits[1]) > 0 else 0.5
        t = int(digits[2:4]) / 100.0
    elif "SELIG" in nome_upper or "S1223" in nome_upper:
        # Parameters closely matching the ultra-high camber Selig 1223
        m, p, t = 0.081, 0.35, 0.121
    elif "MH" in nome_upper:
        # Parameters representing thin, low-camber speed profiles (e.g., MH 32)
        m, p, t = 0.024, 0.41, 0.087
    elif "CH10" in nome_upper:
        # High lift heavy cargo profile adaptation
        m, p, t = 0.075, 0.30, 0.120
    else:
        # General safe fallback for other custom profiles in your database
        m, p, t = 0.04, 0.4, 0.12

    yc = camber_4digit(m, p)
    yt = thickness(t)

    return x, yc + yt, yc - yt


# ----------------------------------------------------------------- #
# WING PLANFORM                                                      #
# ----------------------------------------------------------------- #

def gerar_silhueta_asat(forma, b, c):
    """Returns (xs, ys) for wing planform (semi-span)."""
    if forma == "Retangular":
        return [0, b / 2, b / 2, 0, 0], [0, 0, c, c, 0]
    elif forma == "Elíptica":
        th = np.linspace(0, np.pi, 120)
        return (list((b / 2) * np.sin(th)) + [0],
                list(c * np.cos(th) / 2 + c / 2) + [c / 2])
    else:  # Delta
        return [0, b / 2, 0, 0], [0, c / 2, c, 0]


# ----------------------------------------------------------------- #
# COMPATIBILIDADE RETROATIVA: RA e S                                #
# ----------------------------------------------------------------- #

def geometria_de_ra_e_s(perfil_nome, forma, b, c):
    """
    Retorna métricas da asa calculadas geometricamente (White Cap 8).
    Utilizado como verificação cruzada com os métodos estatísticos.
    """
    # Área da semi-asa via trapézio composto da planta baixa
    xs, ys = gerar_silhueta_asat(forma, b, c)
    S_semi = float(np.trapz(ys[:len(ys)//2], xs[:len(xs)//2]))
    S = S_semi * 2.0
    AR = (b ** 2) / S if S > 0 else 0.0

    # Volume do aerofólio adimensionalizado
    x, yu, yl = gerar_coord_naca(perfil_nome)
    vol_perfil_adim = float(np.trapz(yu - yl, x))

    return {
        "S_geometrico": S,
        "AR_geometrico": AR,
        "vol_adim_perfil": vol_perfil_adim
    }