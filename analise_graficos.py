# ================================================================= #
# AsalabXYZ — MÓDULO 3: ANÁLISE E GRÁFICOS                          #
# Física: Frank M. White, Fluid Mechanics, 8ª Ed.                   #
# ================================================================= #

import re
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from database import DATABASE, AsaT
from calculos import calcular_asa


# ================================================================= #
# GEOMETRIA DO PERFIL (visualização — White §8.1)                    #
# ================================================================= #

def gerar_coord_naca(nome):
    """Coordenadas superior/inferior do perfil (analítica, White §8.1)."""
    x = np.linspace(0, 1, 101)

    def thickness(t_frac):
        return 5 * t_frac * (
            0.2969 * np.sqrt(x) - 0.1260 * x
            - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4
        )

    nome_u = nome.upper()

    # ── NACA 5 dígitos ────────────────────────────────────────────
    if "23012" in nome_u:
        r, k1 = 0.2025, 15.957
        yc = np.where(x < r,
                      k1 / 6 * (x**3 - 3*r*x**2 + r**2*(3-r)*x),
                      k1 * r**3 / 6 * (1 - x))
        yt = thickness(0.12)
    elif "23015" in nome_u:
        r, k1 = 0.2025, 15.957
        yc = np.where(x < r,
                      k1 / 6 * (x**3 - 3*r*x**2 + r**2*(3-r)*x),
                      k1 * r**3 / 6 * (1 - x))
        yt = thickness(0.15)

    # ── NACA 6 dígitos (série 63 / 65) ────────────────────────────
    elif "63-2" in nome_u or "632" in nome_u:
        # Linha de curvatura: série 6 usa a=1 mean line (aprox. como 4-dígitos leve)
        m, p = 0.02, 0.35
        yc = np.where(x < p, m/p**2*(2*p*x - x**2),
                      m/(1-p)**2*((1-2*p) + 2*p*x - x**2))
        yt = thickness(0.15)
    elif "65-2" in nome_u or "652" in nome_u:
        m, p = 0.015, 0.40
        yc = np.where(x < p, m/p**2*(2*p*x - x**2),
                      m/(1-p)**2*((1-2*p) + 2*p*x - x**2))
        yt = thickness(0.10)

    # ── NACA 4 dígitos ────────────────────────────────────────────
    elif "4412" in nome_u:
        m, p = 0.04, 0.4
        yc = np.where(x < p, m/p**2*(2*p*x - x**2),
                      m/(1-p)**2*((1-2*p) + 2*p*x - x**2))
        yt = thickness(0.12)
    elif "6412" in nome_u:
        m, p = 0.06, 0.4
        yc = np.where(x < p, m/p**2*(2*p*x - x**2),
                      m/(1-p)**2*((1-2*p) + 2*p*x - x**2))
        yt = thickness(0.12)
    elif "1223" in nome_u:
        m, p = 0.11, 0.2
        yc = np.where(x < p, m/p**2*(2*p*x - x**2),
                      m/(1-p)**2*((1-2*p) + 2*p*x - x**2))
        yt = thickness(0.23)

    # ── Fallback / CH10 ───────────────────────────────────────────
    else:
        m, p = 0.05, 0.5
        yc = np.where(x < p, m/p**2*(2*p*x - x**2),
                      m/(1-p)**2*((1-2*p) + 2*p*x - x**2))
        yt = thickness(0.15)

    return x, yc + yt, yc - yt


def gerar_silhueta_asat(forma, b, c):
    """Coordenadas (x, y) da silhueta em planta da AsaT."""
    if forma == "Retangular":
        xs = [0, b / 2, b / 2, 0, 0]
        ys = [0, 0,      c,    c, 0]
    elif forma == "Elíptica":
        theta = np.linspace(0, np.pi, 120)
        xs = list((b / 2) * np.sin(theta)) + [0]
        ys = list(c * np.cos(theta) / 2 + c / 2) + [c / 2]
    else:  # Delta
        xs = [0, b / 2, 0, 0]
        ys = [0, c / 2, c, 0]
    return xs, ys


# ================================================================= #
# ENTRADA DO USUÁRIO                                                 #
# ================================================================= #

def coletar_inputs():
    """Exibe menus e coleta os parâmetros do usuário."""
    lista_perfis = list(DATABASE.keys())

    print("\n" + "=" * 65)
    print("   ASALAB XYZ — SIMULADOR AERODINÂMICO INTEGRADO")
    print("   Física: Frank M. White, Fluid Mechanics 8ª Ed.")
    print("=" * 65)

    print("\nPerfis disponíveis:")
    for i, p in enumerate(lista_perfis, 1):
        if any(d in p for d in ["23012", "23015"]):
            fam = "5-dígitos"
        elif any(d in p for d in ["63-", "65-", "63_", "65_"]):
            fam = "6-dígitos"
        else:
            fam = "4-dígitos"
        print(f"  {i}- {p:30s}  ({fam})")

    print("\nTipos de Asa (AsaT):")
    for k, nome in AsaT.items():
        print(f"  {k}- {nome}")

    print()
    in1 = input("1- Velocidade [m/s]  Corda [m]  Envergadura [m]  Peso [kg]: ")
    nums1 = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", in1)]
    v, c, b, peso_kg = nums1[0], nums1[1], nums1[2], nums1[3]

    in2 = input("2- Número dos 2 aerofólios: ")
    numeros = [int(n) for n in re.findall(r"\d+", in2)]
    perfis_sel = [lista_perfis[numeros[0] - 1], lista_perfis[numeros[1] - 1]]

    in3 = input("3- Tipo de Asa (1=Retangular / 2=Elíptica / 3=Delta): ").strip()
    asat_sel = AsaT.get(in3, "Retangular")
    print(f"   → AsaT selecionada: {asat_sel}")

    return v, c, b, peso_kg, perfis_sel, asat_sel


# ================================================================= #
# GERAÇÃO DOS GRÁFICOS                                               #
# Layout 3×2:                                                        #
#   Linha 1: CL | CD | L/D                                           #
#   Linha 2: Cm | XCp | Silhueta AsaT                               #
# ================================================================= #

def plotar_resultados(dados):
    """Recebe o dict de calculos.calcular_asa() e exibe todos os gráficos."""
    cores = ["#01021A", "#EF553B"]

    v        = dados["v"]
    c        = dados["c"]
    b        = dados["b"]
    peso_kg  = dados["peso_kg"]
    S        = dados["S"]
    AR       = dados["AR"]
    re_real  = dados["re_real"]
    cl_req   = dados["cl_req"]
    e_oswald = dados["e_oswald"]
    kappa    = dados["kappa"]
    x_tr_pct = dados["x_tr_pct"]
    Ma_info  = dados["Ma_info"]
    alphas   = dados["alphas"]
    asat_sel = dados["asat_sel"]
    perfis_sel = dados["perfis_sel"]
    resultados = dados["resultados"]

    # ── Layout: 2 linhas × 3 colunas ─────────────────────────────
    fig = make_subplots(
        rows=2, cols=3,
        vertical_spacing=0.18,
        horizontal_spacing=0.10,
        subplot_titles=(
            "<b>Sustentação (CL)</b>",
            "<b>Arrasto (CD)</b>",
            "<b>Eficiência (L/D)</b>",
            "<b>Coeficiente de Pressão (Cm) — White §8.1</b>",
            "<b>Coeficiente de Pressão (XCp) — White §8.1</b>",
            f"<b>AsaT — {asat_sel}</b>",
        ),
    )

    # ── Rodapé ───────────────────────────────────────────────────
    footer = (
        f"<b>Peso: {peso_kg} kg | CL_req: {cl_req:.4f} | Re: {re_real:.0f} | "
        f"Ma: {Ma_info:.3f} | AsaT: {asat_sel} (κ={kappa:.2f})</b><br>"
        f"<b>Envergadura: {b:.2f} m | Corda: {c:.2f} m | S: {S:.3f} m² | "
        f"AR: {AR:.2f} | e_Oswald: {e_oswald:.3f}</b><br>"
        f"<b>Transição lam→turb: {x_tr_pct:.1f}% da corda "
        f"(critério de Michel, White §7.4)</b><br>"
    )

    for idx, perfil in enumerate(perfis_sel):
        r = resultados[perfil]
        cl_asa      = r["cl_asa"]
        cd_tot      = r["cd_tot"]
        eff         = r["eff"]
        ld_max      = r["ld_max"]
        alpha_stall = r["alpha_stall"]
        a0_2d       = r["a0_2d"]
        a0_2d_raw   = r["a0_2d_raw"]
        cm_asa      = r["cm_asa"]
        xcp_asa     = r["xcp_asa"]
        cm0_2d      = r["cm0_2d"]

        footer += (
            f"<b>{perfil}:</b> "
            f"(L/D)_max={ld_max:.2f} analít. / {np.max(eff):.2f} numérico "
            f"(α={alphas[np.argmax(eff)]:.1f}°) | "
            f"α_estol≈{alpha_stall:.1f}° | "
            f"PG: a0={a0_2d:.4f} (raw={a0_2d_raw:.4f}) | "
            f"Cm0={cm0_2d:.4f}<br>"
        )

        cor = cores[idx]
        dash_stall = dict(color=cor, width=1.2, dash="dashdot")

        # ── Linha 1: CL, CD, L/D ─────────────────────────────────
        fig.add_trace(go.Scatter(
            x=alphas, y=cl_asa, name=perfil,
            line=dict(color=cor, width=3)), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=alphas, y=cd_tot, showlegend=False,
            line=dict(color=cor, width=3)), row=1, col=2)

        fig.add_trace(go.Scatter(
            x=alphas, y=eff, showlegend=False,
            line=dict(color=cor, width=3, dash="dot")), row=1, col=3)

        # Linha de estol no CL
        fig.add_trace(go.Scatter(
            x=[alpha_stall, alpha_stall], y=[-0.5, 2.0],
            mode="lines", showlegend=False,
            line=dash_stall), row=1, col=1)

        # ── Linha 2: Cm ──────────────────────────────────────────
        fig.add_trace(go.Scatter(
            x=alphas, y=cm_asa,
            name=f"{perfil} Cm", showlegend=False,
            line=dict(color=cor, width=3)), row=2, col=1)

        # Linha de Cm=0 (referência de neutralidade)
        fig.add_trace(go.Scatter(
            x=[-6, 16], y=[0, 0],
            mode="lines", showlegend=False,
            line=dict(color="gray", width=1, dash="dot")), row=2, col=1)

        # Linha de estol no Cm
        fig.add_trace(go.Scatter(
            x=[alpha_stall, alpha_stall], y=[-0.5, 0.3],
            mode="lines", showlegend=False,
            line=dash_stall), row=2, col=1)

        # ── Linha 2: XCp ─────────────────────────────────────────
        # Clipar apenas região de voo útil (CL > 0)
        xcp_plot = np.where(cl_asa > 0.05, xcp_asa, np.nan)
        fig.add_trace(go.Scatter(
            x=alphas, y=xcp_plot,
            name=f"{perfil} XCp", showlegend=False,
            line=dict(color=cor, width=3)), row=2, col=2)

        # Linha de referência: bordo de ataque (XCp=0) e BA traseiro (1)
        for yref, label in [(0.25, "c/4"), (0.50, "c/2")]:
            fig.add_trace(go.Scatter(
                x=[-6, 16], y=[yref, yref],
                mode="lines", showlegend=False,
                line=dict(color="lightgray", width=1, dash="dot")), row=2, col=2)

    # ── CL requerido ──────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=[-6, 16], y=[cl_req, cl_req],
        mode="lines", name="CL req.",
        line=dict(color="black", dash="dash", width=1.5)), row=1, col=1)

    # ── Silhueta AsaT ─────────────────────────────────────────────
    xs_pf, ys_pf = gerar_silhueta_asat(asat_sel, b, c)
    fig.add_trace(go.Scatter(
        x=xs_pf, y=ys_pf, fill="toself",
        fillcolor="rgba(30,80,180,0.25)",
        line=dict(color="navy", width=2),
        showlegend=False, name=asat_sel), row=2, col=3)
    fig.add_annotation(
        x=b / 4, y=c * 1.08,
        text=f"b={b:.2f} m | c={c:.2f} m | AR={AR:.2f}",
        showarrow=False, font=dict(size=10), row=2, col=3)

    # ── Anotação (L/D)_max ────────────────────────────────────────
    last_eff = resultados[perfis_sel[-1]]["eff"]
    fig.add_annotation(
        xref="x3", yref="y3",
        x=alphas[np.argmax(last_eff)], y=np.max(last_eff),
        text="(L/D)_max", showarrow=True, arrowhead=2, font=dict(size=11))

    # ── Layout final ──────────────────────────────────────────────
    fig.update_layout(
        height=1100, width=1400,
        template="plotly_white",
        margin=dict(t=100, b=340, l=80, r=80),
        title=dict(
            text=(
                f"AsalabXYZ | AsaT: <b>{asat_sel}</b> | "
                "<i>Fluid Mechanics — White 8ª Ed.</i>"
            ),
            x=0.5, font=dict(size=16),
        ),
    )

    # Anotação rodapé
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.5, y=-0.30, text=footer,
        showarrow=False, align="left",
        bgcolor="rgba(255,255,255,0.9)",
        bordercolor="black", borderwidth=1, borderpad=12)

    # ── Eixos ─────────────────────────────────────────────────────
    for col in [1, 2, 3]:
        fig.update_xaxes(title_text="α [°]", row=1, col=col)
        fig.update_xaxes(title_text="α [°]", row=2, col=col)

    fig.update_yaxes(title_text="CL",            row=1, col=1)
    fig.update_yaxes(title_text="CD",            row=1, col=2)
    fig.update_yaxes(title_text="L/D",           row=1, col=3)
    fig.update_yaxes(title_text="Cm ",   row=2, col=1)
    fig.update_yaxes(title_text="XCp (x/c)",     row=2, col=2, autorange="reversed")
    fig.update_xaxes(title_text="y — semi-envergadura [m]", row=2, col=3)
    fig.update_yaxes(title_text="x — corda [m]",            row=2, col=3)

    fig.show()


# ================================================================= #
# PONTO DE ENTRADA                                                   #
# ================================================================= #

def simular_asa_aerodinamica():
    try:
        v, c, b, peso_kg, perfis_sel, asat_sel = coletar_inputs()
        dados = calcular_asa(v, c, b, peso_kg, perfis_sel, asat_sel)
        plotar_resultados(dados)
    except Exception as err:
        print(f"[ERRO]: {err}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    simular_asa_aerodinamica()


# ================================================================= #
# REFERÊNCIAS                                                        #
# ─ White, F. M. Fluid Mechanics, 8ª Ed. McGraw-Hill, 2016.         #
#   §8.1   Geometria NACA + centro de pressão (XCp = 0.25 − Cm/CL) #
#   §8.3   Polar parabólica, Oswald                                  #
#   §8.4   Lifting Line — Cm da asa finita                           #
# ================================================================= #
