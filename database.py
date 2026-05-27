# ================================================================= #
# Dark Wing Project — MÓDULO 1: DATABASE AERODINÂMICO                       #
# Física: Frank M. White, Fluid Mechanics, 8ª Ed.                   #
# ================================================================= #

import numpy as np

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
        30000:  (0.0765, -2.48, 0.0381, -0.1650, 0.405),   
        50000:  (0.0821, -3.80, 0.0753, -0.1810, 0.520),   
        100000: (0.0538, -14.78, 0.05561, -0.1820, 0.510), 
        150000: (0.1115, -5.75, 0.0152, -0.2050, 0.354),  
        200000: (0.0899, -13.02, 0.01646, -0.1750, 0.490), 
        250000: (0.1130, -6.31, 0.0128, -0.2130, 0.352),   
        300000: (0.1141, -6.44, 0.0121, -0.2150, 0.351),   
        350000: (0.1144, -6.50, 0.0116, -0.2170, 0.350),   
        400000: (0.1147, -6.55, 0.0112, -0.2180, 0.349),   
        450000: (0.1150, -6.59, 0.0108, -0.2190, 0.349),  
        500000: (0.0808, -14.97, 0.01029, -0.1720, 0.480), 
        600000: (0.1155, -6.65, 0.0101, -0.2210, 0.348),   
        650000: (0.1157, -6.67, 0.0099, -0.2220, 0.348),   
    },
     "NACA6409 9%": {
        50000:  (0.098, -5.5, 0.018, -0.145, 0.25),
        100000: (0.103, -5.3, 0.015, -0.147, 0.25),
        200000: (0.108, -5.2, 0.012, -0.149, 0.25),
        500000: (0.112, -5.0, 0.009, -0.150, 0.25),
    },
    # ── NACA Blended ──────────────────────────────────────────────
    "NACA 6909_54.79%_6412": {
        50000:  (0.0677, -3.37, 0.0429, -0.100, 0.31),
        100000: (0.1040, -3.50, 0.0197, -0.102, 0.31),
        200000: (0.0910, -5.50, 0.0111, -0.108, 0.30),
        500000: (0.0864, -6.01, 0.0077, -0.110, 0.30),
    },
    # ── NACA 5 dígitos ────────────────────────────────────────────

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
    # ── Martin Hepperle (MH) ──────────────────────────────────────
    "MH 32": {
        50000:  (0.082, -2.8, 0.028, -0.040, 0.28),
        100000: (0.093, -2.9, 0.018, -0.042, 0.28),
        200000: (0.100, -3.0, 0.012, -0.043, 0.27),
        500000: (0.104, -3.0, 0.008, -0.044, 0.27),
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

AsaT_DESC = {
    "Retangular": "e_Oswald padrão | κ=1.00",
    "Elíptica":   "e=1.00 (ideal) | κ=1.00",
    "Delta":      "e empírico | κ=0.90",
}

# ================================================================= #
# 3 — BANCO DE MATERIAIS RC (Sadraey Cap. 6; White §7.3)             #
# Unificado a partir de materiais_peso_stall.py                      #
# ================================================================= #
MATERIAIS = {
    # ── MADEIRAS ──────────────────────────────────────────────────
    "Balsa Leve": {
        "densidade_kg_m3":  100,
        "espessura_mm":     3.0,
        "fator_construcao": 0.30,
        "cd0_rugosidade":   0.0002,
        "descricao": "Balsa de baixa densidade (<120 kg/m³). Ideal para asas "
                     "leves até ~2 kg. Revestimento com Monokote ou fibra 25 g/m².",
    },
    "Balsa Média": {
        "densidade_kg_m3":  160,
        "espessura_mm":     4.0,
        "fator_construcao": 0.35,
        "cd0_rugosidade":   0.0003,
        "descricao": "Balsa densidade média (120–200 kg/m³). Bom equilíbrio "
                     "resistência/peso para fuselagens RC.",
    },
    "Balsa Densa": {
        "densidade_kg_m3":  220,
        "espessura_mm":     5.0,
        "fator_construcao": 0.40,
        "cd0_rugosidade":   0.0004,
        "descricao": "Balsa pesada (>200 kg/m³). Usada em regiões de carga "
                     "concentrada (engate de trem, raiz da asa).",
    },
    "Compensado Bétula 3mm": {
        "densidade_kg_m3":  650,
        "espessura_mm":     3.0,
        "fator_construcao": 0.20,
        "cd0_rugosidade":   0.0008,
        "descricao": "Compensado de bétula (birch ply). Alta resistência ao "
                     "cisalhamento. Usado em nervuras e fundos de fuselagem.",
    },
    "Compensado Leve 1.5mm": {
        "densidade_kg_m3":  500,
        "espessura_mm":     1.5,
        "fator_construcao": 0.18,
        "cd0_rugosidade":   0.0006,
        "descricao": "Compensado fino para coberturas estruturais leves.",
    },
    # ── ESPUMAS ───────────────────────────────────────────────────
    "Depron 6mm": {
        "densidade_kg_m3":  33,
        "espessura_mm":     6.0,
        "fator_construcao": 1.00,
        "cd0_rugosidade":   0.0005,
        "descricao": "Espuma expandida de poliestireno extrudado. Muito leve, "
                     "fácil de cortar a laser. Usado em fuselagens e asas de parkflyer.",
    },
    "Depron 3mm": {
        "densidade_kg_m3":  33,
        "espessura_mm":     3.0,
        "fator_construcao": 1.00,
        "cd0_rugosidade":   0.0005,
        "descricao": "Depron fino para aeronaves de sala (indoor) e mini-RC.",
    },
    "EPP (Polipropileno Expandido)": {
        "densidade_kg_m3":  25,
        "espessura_mm":     8.0,
        "fator_construcao": 1.00,
        "cd0_rugosidade":   0.0010,
        "descricao": "Espuma flexível resistente ao impacto. Ideal para asas de "
                     "treinador e acrobáticos. Não quebra em colisões.",
    },
    "EPS (Isopor estrutural)": {
        "densidade_kg_m3":  20,
        "espessura_mm":    10.0,
        "fator_construcao": 1.00,
        "cd0_rugosidade":   0.0015,
        "descricao": "Poliestireno expandido de alta densidade. Usado em "
                     "fuselagens moldadas (foam-board style).",
    },
    # ── COMPÓSITOS ────────────────────────────────────────────────
    "Fibra de Vidro 160g/m²": {
        "densidade_kg_m3":  1800,
        "espessura_mm":     0.20,
        "fator_construcao": 1.00,
        "cd0_rugosidade":   0.0001,
        "descricao": "Laminado de fibra de vidro tecido plano 160 g/m². "
                     "Usado como revestimento sobre núcleo de balsa ou espuma. "
                     "Aumenta rigidez torsional da asa.",
    },
    "Fibra de Carbono 200g/m²": {
        "densidade_kg_m3":  1600,
        "espessura_mm":     0.25,
        "fator_construcao": 1.00,
        "cd0_rugosidade":   0.0001,
        "descricao": "CFRP tecido 3K, 200 g/m². Módulo elástico ~70 GPa. "
                     "Usado em longarinas, tubos de cauda e nervuras de carga.",
    },
    # ── PLÁSTICOS / IMPRESSÃO 3D ──────────────────────────────────
    "PLA (FDM 20% infill)": {
        "densidade_kg_m3":  250,
        "espessura_mm":     2.0,
        "fator_construcao": 1.00,
        "cd0_rugosidade":   0.0012,
        "descricao": "Impressão 3D FDM em PLA com 20% de preenchimento. "
                     "Usado em suportes, trens de pouso e empenagem.",
    },
    "PETG (FDM 30% infill)": {
        "densidade_kg_m3":  360,
        "espessura_mm":     2.5,
        "fator_construcao": 1.00,
        "cd0_rugosidade":   0.0010,
        "descricao": "PETG FDM 30% infill. Mais flexível que PLA, maior "
                     "resistência ao impacto. Bom para carenagens.",
    },
}

# ================================================================= #
# 4 — CL_MAX E CD0 POR AEROFÓLIO (Abbott & von Doenhoff; Sadraey)   #
# ================================================================= #
CL_MAX_2D = {
    "NACA 4412":             1.65,
    "SELIG 1223":            2.10,
    "NACA 6412":             1.70,
    "CH10_S1210_30":         1.99,
    "NACA 6909_54.79%_6412": 1.60,
    "NACA6409 9%":           1.48,
    "NACA 23015":            1.50,
    "NACA 63-215":           1.45,
    "MH 32":                 1.30,
}

CD0_PERFIL = {
    "NACA 4412":             0.009,
    "SELIG 1223":            0.018,
    "NACA 6412":             0.010,
    "CH10_S1210_30":         0.012,
    "NACA 6909_54.79%_6412": 0.009,
    "NACA6409 9%":           0.012,
    "NACA 23015":            0.009,
    "NACA 63-215":           0.007,
    "MH 32":                 0.010,
}

# ================================================================= #
# REFERÊNCIAS                                                        #
# ─ White, F. M. Fluid Mechanics, 8ª Ed. McGraw-Hill, 2016.         #
#   §7.3   Rugosidade superficial — CD0                             #
#   §8.1   Geometria NACA 4, 5 e 6 dígitos                          #
#   §8.3   Polar parabólica, e_Oswald                               #
# ─ Abbott, I.H.; von Doenhoff, A.E. Theory of Wing Sections, 1959. #
# ─ Sadraey, M. Aircraft Design. Wiley, 2013. Cap. 6 (materiais)   #
# ─ XFLR5 v6 — Analysis Tool for Airfoils, Wings and Planes         #
# ─ Hepperle, M. MH-Aerotools Airfoil Database (mh-aerotools.de)   #
#   MH 32 — 8.7 % t/c, 2.4 % camber @ 44 % c                      #
# ================================================================= #