# ================================================================= #
# AsalabXYZ — CLI MENU (dinâmico, lê database.py automaticamente)  #
#                                                                    #
# Uso:  python cli.py                                               #
# ================================================================= #

import re
from database import DATABASE, AsaT, AsaT_DESC, MATERIAIS, CL_MAX_2D, CD0_PERFIL
from calculos import calcular_asa
from analise_graficos import plotar_resultados


# ================================================================= #
# HELPERS DE ESTILO                                                  #
# ================================================================= #
def _L(char="─", n=65):
    print(char * n)

def _cab(t):
    _L("═")
    print(f"   {t}")
    _L("═")

def _sec(t):
    print()
    _L()
    print(f"  {t}")
    _L()

def _ex(t):
    print(f"      Exemplo: {t}")


# ================================================================= #
# EXIBIÇÃO DINÂMICA (lê database em tempo real)                      #
# ================================================================= #
def exibir_perfis():
    lista = list(DATABASE.keys())
    _sec("PERFIS DISPONÍVEIS")
    print(f"  {'Nº':<4} {'Perfil':<32} {'Família':<12} {'CLmax':>6}  {'CD0':>8}")
    _L(" ", 68)
    for i, p in enumerate(lista, 1):
        fam = ("5-dígitos" if any(d in p for d in ["23012", "23015"])
               else "6-dígitos" if any(d in p for d in ["63-", "65-"])
               else "MH" if p.startswith("MH ")
               else "4-dígitos / Outro")
        clm = CL_MAX_2D.get(p, "—")
        cd0 = CD0_PERFIL.get(p, "—")
        clm_s = f"{clm:.3f}" if isinstance(clm, float) else str(clm)
        cd0_s = f"{cd0:.5f}" if isinstance(cd0, float) else str(cd0)
        print(f"  {i:<4} {p:<32} {fam:<12} {clm_s:>6}  {cd0_s:>8}")
    return lista


def exibir_asat():
    _sec("TIPOS DE ASA (AsaT)")
    for k, nome in AsaT.items():
        desc = AsaT_DESC.get(nome, "")
        print(f"  [{k}]  {nome:<14} — {desc}")


def exibir_materiais():
    _sec("MATERIAIS RC  (Módulo 4 — Sadraey Cap. 6)")
    nomes = list(MATERIAIS.keys())
    for i, n in enumerate(nomes, 1):
        m = MATERIAIS[n]
        print(f"  [{i:>2}]  {n:<37}  {m['densidade_kg_m3']:>5} kg/m³  "
              f"e={m['espessura_mm']} mm  ΔCd0={m['cd0_rugosidade']:.4f}")
    return nomes


# ================================================================= #
# COLETA DE INPUTS                                                   #
# ================================================================= #
def coletar_inputs():
    lista_perfis = exibir_perfis()
    exibir_asat()

    _sec("PARÂMETROS DE VOO")
    print("  Velocidade [m/s]  |  Corda [m]  |  Envergadura [m]  |  Peso total [kg]")
    _ex("15  0.6  3.0  28")
    in1 = input("  → ")
    n1 = [float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", in1)]
    if len(n1) < 4:
        raise ValueError("Informe 4 valores: velocidade, corda, envergadura, peso.")
    v, c, b, peso_kg = n1[0], n1[1], n1[2], n1[3]

    _sec("SELEÇÃO DE AEROFÓLIOS  (1–3 perfis)")
    _ex("1 5 8   ou   3   ou   2 7")
    in2 = input("  → ")
    numeros = [int(x) for x in re.findall(r"\d+", in2)]
    if not (1 <= len(numeros) <= 3):
        raise ValueError("Selecione entre 1 e 3 perfis.")
    for n in numeros:
        if not (1 <= n <= len(lista_perfis)):
            raise ValueError(f"Número {n} inválido.")
    seen = []
    for n in numeros:
        if n not in seen:
            seen.append(n)
    if len(seen) < len(numeros):
        print("  [AVISO] Duplicatas removidas.")
    perfis_sel = [lista_perfis[n - 1] for n in seen]
    print(f"\n  Perfis selecionados: {', '.join(perfis_sel)}")

    _sec("TIPO DE ASA")
    in3 = input("  [1/2/3] → ").strip()
    asat_sel = AsaT.get(in3, "Retangular")
    print(f"  → {asat_sel}")

    _sec("ANÁLISE DE MATERIAIS / PESO / STALL  (Módulo 4 — Sadraey 2013)")
    print("  Incluir tabelas de material/peso/stall nos gráficos? [s/n]")
    ativar = input("  → ").strip().lower() in ("s", "sim", "y", "yes", "")

    cfg_mat = None
    if ativar:
        lista_mat = exibir_materiais()
        print("\n  MODO:")
        print("    [1]  Análise completa  — 1 perfil + 1 material")
        print("         (4 tabelas: Peso | Stall+Desempenho | CD0 | Alertas)")
        print("    [2]  Comparar materiais — todos os materiais, perfil principal")
        print("    [3]  Comparar aerofólios — todos os perfis, 1 material")
        modo = input("  → ").strip() or "1"

        _sec("PARÂMETROS DA MISSÃO RC")
        print(f"  Velocidade cruzeiro [m/s]  (padrão: {v * 0.80:.1f}):")
        raw_vc = input("  → ").strip()
        v_cruise = float(raw_vc) if raw_vc else v * 0.80

        print(f"  Payload útil [kg]  (padrão: {peso_kg * 0.50:.1f}):")
        raw_pl = input("  → ").strip()
        payload = float(raw_pl) if raw_pl else peso_kg * 0.50

        print("  Trem de pouso fixo? [s/n]  (padrão: s):")
        com_trem = input("  → ").strip().lower() not in ("n", "nao", "não")

        cfg_mat = {
            "modo": modo,
            "v_cruise": v_cruise,
            "payload": payload,
            "v_max": v,
            "com_trem": com_trem,
            "lista_mat": lista_mat,
            "perfil_principal": perfis_sel[0],
        }

        if modo in ("1", ""):
            print(f"\n  Material (1–{len(lista_mat)}):")
            im = int(input("  → ").strip() or "1") - 1
            cfg_mat["material"] = lista_mat[max(0, min(im, len(lista_mat) - 1))]
        elif modo == "3":
            print(f"\n  Material (1–{len(lista_mat)}):")
            im = int(input("  → ").strip() or "1") - 1
            cfg_mat["material"] = lista_mat[max(0, min(im, len(lista_mat) - 1))]

    _sec("RESUMO")
    S_p = b * c
    AR_p = b ** 2 / S_p
    print(f"  V={v} m/s  c={c} m  b={b} m  W={peso_kg} kg")
    print(f"  S={S_p:.3f} m²  AR={AR_p:.2f}")
    print(f"  Perfis: {', '.join(perfis_sel)}  |  Asa: {asat_sel}")
    if cfg_mat:
        mat_n = cfg_mat.get("material", "todos")
        print(f"  Módulo 4: modo={cfg_mat['modo']} | material={mat_n} | "
              f"payload={cfg_mat['payload']:.1f} kg | V_cruise={cfg_mat['v_cruise']:.1f} m/s")
    _L()
    return v, c, b, peso_kg, perfis_sel, asat_sel, cfg_mat


# ================================================================= #
# PONTO DE ENTRADA                                                   #
# ================================================================= #
def main_cli():
    try:
        v, c, b, peso_kg, perfis_sel, asat_sel, cfg_mat = coletar_inputs()
        dados = calcular_asa(v, c, b, peso_kg, perfis_sel, asat_sel)
        plotar_resultados(dados, cfg_mat)
    except Exception as err:
        print(f"\n[ERRO]: {err}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main_cli()