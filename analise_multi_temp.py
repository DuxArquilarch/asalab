"""
AsalabXYZ — analise_multi_temp.py
───────────────────────────────────
Análise multi-temperatura (Lei de Sutherland) + plotagem interativa.

Quando importado pela GUI expõe apenas plotar_multi_temp().
O bloco de demonstração roda apenas se executado diretamente.
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

# Força abertura no navegador padrão (não bloqueia em segundo plano)
pio.renderers.default = "browser"

from calculos import (
    calcular_asa_multi_temp,
    sutherland_viscosidade,
    propriedades_por_temperatura,
)


# ------------------------------------------------------------------
# Stubs / helpers para compatibilidade com o demo original
# ------------------------------------------------------------------
CONDICOES_PRESSAO = {
    "slISA": (15.0, 101325.0),
    "p30":   (30.0, 101325.0),
    "p25":   (25.0, 101325.0),
    "p20":   (20.0, 101325.0),
    "p15":   (15.0, 101325.0),
}

def propriedades_por_condicao(chave):
    T_C, P_Pa = CONDICOES_PRESSAO[chave]
    return propriedades_por_temperatura(T_C, P_Pa)

def imprimir_re_condicoes(v_lista, c_lista):
    print("\n  TABELA DE REYNOLDS (×10⁵)")
    print("  " + "─" * 60)
    header = "  {:>6} ".format("v\\c")
    for c in c_lista:
        header += f"{c:>10.2f}m"
    print(header)
    print("  " + "─" * 60)
    for v in v_lista:
        line = f"  {v:>6.1f} "
        for c in c_lista:
            rho = 1.225
            mu = 1.849e-5
            re = rho * v * c / mu
            line += f"{re/1e5:>10.2f}"
        print(line)
    print("  " + "─" * 60)

def imprimir_tabela_multi(tabela):
    pass


# ================================================================= #
# PLOTAGEM INTERATIVA (chamada pela GUI)
# ================================================================= #

def plotar_multi_temp(resultado, cfg):
    """
    Gera gráficos Plotly comparativos para análise multi-temperatura.
    """
    temperaturas = resultado["temperaturas"]
    perfis = cfg.get("perfis_sel", [])
    if not perfis:
        primeiro = next(iter(resultado["dados"].values()))
        perfis = list(primeiro["resultados"].keys())

    n_perfis = len(perfis)
    asat = cfg.get("asat_sel", "Retangular")

    # ── Pré-calcular propriedades por temperatura ──
    v_cfg     = cfg.get("v",       15.0)
    c_cfg     = cfg.get("c",       0.4)
    b_cfg     = cfg.get("b",       3.0)
    peso_cfg  = cfg.get("peso_kg", 20.0)
    try:
        v_cfg    = float(v_cfg)
        c_cfg    = float(c_cfg)
        b_cfg    = float(b_cfg)
        peso_cfg = float(peso_cfg)
    except (TypeError, ValueError):
        v_cfg, c_cfg, b_cfg, peso_cfg = 15.0, 0.4, 3.0, 20.0

    g_acc = 9.81

    # Propriedades por temperatura
    props_T = {}
    for T in temperaturas:
        props_T[float(T)] = propriedades_por_temperatura(float(T), 101325.0)

    # Paleta por perfil (consistente com Figura 2)
    cores_perfis = ["#01021A", "#EF553B", "#00CC96", "#AB63FA",
                    "#FFA15A", "#19D3F3", "#FF6692", "#B6E880"]
    markers_perfis = ["circle", "square", "diamond", "cross",
                      "triangle-up", "star", "hexagon", "pentagon"]
    dashes_perfis  = ["solid", "dot", "dash", "dashdot",
                      "longdash", "solid", "dot", "dash"]

    # ── Figura 1: Grandezas DIMENSIONAIS vs Temperatura ──
    # (estas realmente mudam — L[N], D[N], Re, q_din, L/D_max)
    print("  [Multi-Temp] Gerando Figura 1: Grandezas dimensionais vs Temperatura...")

    # Calcular para α de cruzeiro = α que dá CL_req em cada T
    # e também α_stall  para corda de referência (c_cfg)
    alpha_ref = np.linspace(-6, 16, 150)

    fig = make_subplots(
        rows=3, cols=2,
        vertical_spacing=0.11, horizontal_spacing=0.13,
        subplot_titles=(
            "<b>Força de Sustentação L [N] @ α_req vs Temperatura</b>",
            "<b>Força de Arrasto D [N] @ α_req vs Temperatura</b>",
            "<b>Pressão Dinâmica q [Pa] vs Temperatura</b>",
            "<b>Reynolds vs Temperatura</b>",
            "<b>Potência Necessária P [W] @ α_req vs Temperatura</b>",
            "<b>Razão Sustentação/Arrasto (L/D) @ α_req vs Temperatura</b>",
        )
    )

    for idx, perfil in enumerate(perfis):
        cor  = cores_perfis[idx % len(cores_perfis)]
        mk   = markers_perfis[idx % len(markers_perfis)]
        dash = dashes_perfis[idx % len(dashes_perfis)]

        L_vals, D_vals, q_vals, re_vals_p, P_vals, ld_vals = [], [], [], [], [], []

        for T in temperaturas:
            d    = resultado["dados"][float(T)]
            r    = d["resultados"][perfil]
            prop = props_T[float(T)]
            rho  = prop["rho"]
            mu   = prop["mu"]

            S    = b_cfg * c_cfg
            q    = 0.5 * rho * v_cfg**2
            re   = rho * v_cfg * c_cfg / mu

            # CL requerido nesta temperatura
            cl_req_T = (2.0 * peso_cfg * g_acc) / (rho * v_cfg**2 * S)

            # CL e CD no ponto de operação (interpola da curva)
            cl_curve = r["cl_asa"]
            cd_curve = r["cd_tot"]
            alphas_c = d["alphas"]

            # Ponto de operação: α onde CL ≈ CL_req
            idx_op = int(np.argmin(np.abs(cl_curve - cl_req_T)))
            cl_op  = float(cl_curve[idx_op])
            cd_op  = float(cd_curve[idx_op])

            L_N  = q * S * cl_op
            D_N  = q * S * cd_op
            P_W  = D_N * v_cfg          # potência = arrasto × velocidade
            ld_op = cl_op / max(cd_op, 1e-6)

            L_vals.append(L_N)
            D_vals.append(D_N)
            q_vals.append(q)
            re_vals_p.append(re)
            P_vals.append(P_W)
            ld_vals.append(ld_op)

        common = dict(
            x=temperaturas, mode="lines+markers",
            name=perfil, legendgroup=perfil,
            line=dict(color=cor, width=2.3, dash=dash),
            marker=dict(symbol=mk, size=7, color=cor),
        )

        fig.add_trace(go.Scatter(**common, showlegend=True,
            y=L_vals,
            hovertemplate=(f"<b>{perfil}</b><br>T=%{{x:.1f}}°C<br>"
                           f"L=%{{y:.2f}} N<extra></extra>"),
        ), row=1, col=1)

        fig.add_trace(go.Scatter(**common, showlegend=False,
            y=D_vals,
            hovertemplate=(f"<b>{perfil}</b><br>T=%{{x:.1f}}°C<br>"
                           f"D=%{{y:.3f}} N<extra></extra>"),
        ), row=1, col=2)

        # q e Re são independentes do perfil — plotar só para o primeiro
        if idx == 0:
            fig.add_trace(go.Scatter(
                x=temperaturas, y=q_vals,
                name="q [Pa]", legendgroup="q",
                mode="lines+markers",
                line=dict(color="#00CC96", width=2.3),
                marker=dict(symbol="diamond", size=7, color="#00CC96"),
                fill="tozeroy", fillcolor="rgba(0,204,150,0.10)",
                hovertemplate="T=%{x:.1f}°C<br>q=%{y:.3f} Pa<extra>q</extra>",
            ), row=2, col=1)

            fig.add_trace(go.Scatter(
                x=temperaturas, y=re_vals_p,
                name="Re", legendgroup="Re",
                mode="lines+markers",
                line=dict(color="#01021A", width=2.3),
                marker=dict(symbol="circle", size=7, color="#01021A"),
                hovertemplate="T=%{x:.1f}°C<br>Re=%{y:,.0f}<extra>Re</extra>",
            ), row=2, col=2)

            # linha Re_crítico
            fig.add_hline(y=5e5, line_dash="dot", line_color="gray",
                          line_width=1.2, row=2, col=2)
            fig.add_annotation(
                xref="x4", yref="y4",
                x=temperaturas[-1], y=5e5,
                text="Re_crit = 5×10⁵",
                showarrow=False, font=dict(size=8, color="gray"),
                xanchor="right", yanchor="bottom",
            )

        fig.add_trace(go.Scatter(**common, showlegend=False,
            y=P_vals,
            hovertemplate=(f"<b>{perfil}</b><br>T=%{{x:.1f}}°C<br>"
                           f"P=%{{y:.2f}} W<extra></extra>"),
        ), row=3, col=1)

        fig.add_trace(go.Scatter(**common, showlegend=False,
            y=ld_vals,
            hovertemplate=(f"<b>{perfil}</b><br>T=%{{x:.1f}}°C<br>"
                           f"L/D=%{{y:.2f}}<extra></extra>"),
        ), row=3, col=2)

    # Linha de peso como referência em L [N]
    peso_N = peso_cfg * g_acc
    fig.add_hline(y=peso_N, line_dash="dash", line_color="#EF553B",
                  line_width=1.5, row=1, col=1)
    fig.add_annotation(
        xref="x1", yref="y1",
        x=temperaturas[-1], y=peso_N,
        text=f"W = {peso_N:.1f} N",
        showarrow=False, font=dict(size=8, color="#EF553B"),
        xanchor="right", yanchor="bottom",
    )

    # Eixos
    for row in range(1, 4):
        for col in range(1, 3):
            fig.update_xaxes(title_text="Temperatura [°C]", row=row, col=col,
                             showgrid=True, gridcolor="rgba(200,200,200,0.4)")
            fig.update_yaxes(showgrid=True, gridcolor="rgba(200,200,200,0.4)",
                             row=row, col=col)

    fig.update_yaxes(title_text="L [N]",   row=1, col=1)
    fig.update_yaxes(title_text="D [N]",   row=1, col=2)
    fig.update_yaxes(title_text="q [Pa]",  row=2, col=1)
    fig.update_yaxes(title_text="Re",      row=2, col=2)
    fig.update_yaxes(title_text="P [W]",   row=3, col=1)
    fig.update_yaxes(title_text="L/D",     row=3, col=2)

    S_fig = b_cfg * c_cfg
    fig.update_layout(
        height=1050, width=1200, template="plotly_white",
        title=dict(
            text=(f"AsalabXYZ | Grandezas Dimensionais vs Temperatura | "
                  f"AsaT: <b>{asat}</b> | V={v_cfg} m/s | c={c_cfg} m | "
                  f"b={b_cfg} m | S={S_fig:.3f} m² | W={peso_cfg} kg | "
                  f"T = {temperaturas[0]:.0f}→{temperaturas[-1]:.0f} °C"),
            x=0.5, font=dict(size=13)
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.012,
            xanchor="right", x=1, font=dict(size=10),
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="lightgray", borderwidth=1,
        ),
        margin=dict(t=110, b=80, l=80, r=80),
        plot_bgcolor="white",
    )
    fig.show()
    print("  [Multi-Temp] Figura 1 aberta no navegador.")

    # ── Figura 2: Resumo vs Temperatura ──
    print("  [Multi-Temp] Gerando Figura 2: Resumo vs Temperatura...")

    # Reutilizar props_T calculado na Figura 1
    re_vals    = [resultado["dados"][float(T)]["re_real"] for T in temperaturas]
    clreq_vals = [resultado["dados"][float(T)]["cl_req"]  for T in temperaturas]
    rho_vals   = [props_T[float(T)]["rho"]   for T in temperaturas]
    mu_vals    = [props_T[float(T)]["mu"]    for T in temperaturas]
    vsnom_vals = [props_T[float(T)]["v_som"] for T in temperaturas]

    # Paleta (mesma da Figura 1)
    cores_perfis = ["#01021A", "#EF553B", "#00CC96", "#AB63FA",
                    "#FFA15A", "#19D3F3", "#FF6692", "#B6E880"]
    markers = ["circle", "square", "diamond", "cross",
               "triangle-up", "star", "hexagon", "pentagon"]

    fig2 = make_subplots(
        rows=3, cols=2,
        vertical_spacing=0.11, horizontal_spacing=0.13,
        subplot_titles=(
            "<b>Ângulo de Estol (α_stall) vs Temperatura</b>",
            "<b>Eficiência Máxima (L/D)_max vs Temperatura</b>",
            "<b>Número de Reynolds vs Temperatura</b>",
            "<b>CL Requerido vs Temperatura</b>",
            "<b>Densidade do Ar (ρ) vs Temperatura — ISA</b>",
            "<b>Viscosidade Dinâmica (μ) vs Temperatura — Sutherland</b>",
        )
    )

    # ── Linha 1: α_stall e (L/D)_max por perfil ──
    for idx, perfil in enumerate(perfis):
        cor = cores_perfis[idx % len(cores_perfis)]
        mk  = markers[idx % len(markers)]
        alpha_stalls, ld_maxs, cd0s = [], [], []
        for T in temperaturas:
            d = resultado["dados"][float(T)]
            r = d["resultados"][perfil]
            alpha_stalls.append(r["alpha_stall"])
            ld_maxs.append(r["ld_max"])
            cd0s.append(r["cd0"])

        fig2.add_trace(go.Scatter(
            x=temperaturas, y=alpha_stalls,
            name=perfil, legendgroup=perfil,
            mode="lines+markers",
            line=dict(color=cor, width=2.2),
            marker=dict(symbol=mk, size=7, color=cor),
            hovertemplate=(f"<b>{perfil}</b><br>T = %{{x:.1f}} °C<br>"
                           f"α_stall = %{{y:.2f}} °<extra></extra>"),
        ), row=1, col=1)

        fig2.add_trace(go.Scatter(
            x=temperaturas, y=ld_maxs,
            name=perfil, legendgroup=perfil,
            mode="lines+markers", showlegend=False,
            line=dict(color=cor, width=2.2),
            marker=dict(symbol=mk, size=7, color=cor),
            hovertemplate=(f"<b>{perfil}</b><br>T = %{{x:.1f}} °C<br>"
                           f"(L/D)_max = %{{y:.2f}}<extra></extra>"),
        ), row=1, col=2)

    # ── Linha 2: Re e CL_req (curvas únicas — independentes do perfil) ──
    fig2.add_trace(go.Scatter(
        x=temperaturas, y=re_vals,
        name="Reynolds (Re)", legendgroup="Re",
        mode="lines+markers",
        line=dict(color="#01021A", width=2.5),
        marker=dict(symbol="circle", size=6, color="#01021A"),
        hovertemplate="T = %{x:.1f} °C<br>Re = %{y:,.0f}<extra>Re</extra>",
    ), row=2, col=1)

    # Banda sombreada para Re > 500 000 (laminar → turbulento)
    re_critico = 5e5
    fig2.add_hline(y=re_critico, line_dash="dot", line_color="gray",
                   line_width=1.2, row=2, col=1)
    fig2.add_annotation(
        xref="x3", yref="y3",
        x=temperaturas[-1], y=re_critico,
        text="Re_crítico = 5×10⁵",
        showarrow=False, font=dict(size=8, color="gray"),
        xanchor="right", yanchor="bottom",
    )

    fig2.add_trace(go.Scatter(
        x=temperaturas, y=clreq_vals,
        name="CL requerido", legendgroup="CLreq",
        mode="lines+markers",
        line=dict(color="#EF553B", width=2.5),
        marker=dict(symbol="square", size=6, color="#EF553B"),
        hovertemplate="T = %{x:.1f} °C<br>CL_req = %{y:.4f}<extra>CL_req</extra>",
    ), row=2, col=2)

    # ── Linha 3: ρ e μ (propriedades atmosféricas — Lei de Sutherland) ──
    fig2.add_trace(go.Scatter(
        x=temperaturas, y=rho_vals,
        name="ρ [kg/m³]", legendgroup="rho",
        mode="lines+markers",
        line=dict(color="#00CC96", width=2.5),
        marker=dict(symbol="diamond", size=6, color="#00CC96"),
        fill="tozeroy", fillcolor="rgba(0,204,150,0.08)",
        hovertemplate="T = %{x:.1f} °C<br>ρ = %{y:.5f} kg/m³<extra>ρ</extra>",
    ), row=3, col=1)

    mu_vals_e5 = [m * 1e5 for m in mu_vals]
    fig2.add_trace(go.Scatter(
        x=temperaturas, y=mu_vals_e5,
        name="μ ×10⁻⁵ [Pa·s]", legendgroup="mu",
        mode="lines+markers",
        line=dict(color="#AB63FA", width=2.5),
        marker=dict(symbol="triangle-up", size=6, color="#AB63FA"),
        fill="tozeroy", fillcolor="rgba(171,99,250,0.08)",
        hovertemplate="T = %{x:.1f} °C<br>μ = %{y:.4f} ×10⁻⁵ Pa·s<extra>μ</extra>",
    ), row=3, col=2)

    # ── Eixos ──
    for row in range(1, 4):
        for col in range(1, 3):
            fig2.update_xaxes(title_text="Temperatura [°C]", row=row, col=col,
                              showgrid=True, gridcolor="rgba(200,200,200,0.4)")
            fig2.update_yaxes(showgrid=True, gridcolor="rgba(200,200,200,0.4)",
                              row=row, col=col)

    fig2.update_yaxes(title_text="α_stall [°]",        row=1, col=1)
    fig2.update_yaxes(title_text="(L/D)_max",           row=1, col=2)
    fig2.update_yaxes(title_text="Re",                  row=2, col=1)
    fig2.update_yaxes(title_text="CL_req",              row=2, col=2)
    fig2.update_yaxes(title_text="ρ [kg/m³]",           row=3, col=1)
    fig2.update_yaxes(title_text="μ ×10⁻⁵ [Pa·s]",     row=3, col=2)

    # ── Rodapé organizado ──
    v_cfg   = cfg.get("v",       "?")
    c_cfg   = cfg.get("c",       "?")
    b_cfg   = cfg.get("b",       "?")
    w_cfg   = cfg.get("peso_kg", "?")
    S_val   = (float(b_cfg) * float(c_cfg)) if (b_cfg != "?" and c_cfg != "?") else "?"
    AR_val  = (float(b_cfg)**2 / S_val)     if isinstance(S_val, float)         else "?"
    S_str   = f"{S_val:.3f} m²" if isinstance(S_val,  float) else "?"
    AR_str  = f"{AR_val:.2f}"   if isinstance(AR_val, float) else "?"
    Ma_val  = (float(v_cfg) / vsnom_vals[0]) if (v_cfg != "?" and vsnom_vals) else None
    Ma_str  = f"{Ma_val:.4f}" if Ma_val is not None else "?"

    perfis_str = "  |  ".join(
        f"<b>{p}</b>: α_stall={resultado['dados'][float(temperaturas[0])]['resultados'][p]['alpha_stall']:.1f}→"
        f"{resultado['dados'][float(temperaturas[-1])]['resultados'][p]['alpha_stall']:.1f}°  "
        f"(L/D)_max={resultado['dados'][float(temperaturas[0])]['resultados'][p]['ld_max']:.2f}→"
        f"{resultado['dados'][float(temperaturas[-1])]['resultados'][p]['ld_max']:.2f}"
        for p in perfis
    )

    footer2 = (
        f"<b>Condições:</b>  AsaT: {asat}  |  V = {v_cfg} m/s  |  "
        f"c = {c_cfg} m  |  b = {b_cfg} m  |  S = {S_str}  |  AR = {AR_str}  |  "
        f"W = {w_cfg} kg  |  Ma = {Ma_str}<br>"
        f"<b>Atmosfera (Sutherland):</b>  "
        f"ρ: {rho_vals[0]:.4f} → {rho_vals[-1]:.4f} kg/m³  |  "
        f"μ: {mu_vals[0]*1e5:.4f} → {mu_vals[-1]*1e5:.4f} ×10⁻⁵ Pa·s  |  "
        f"Re: {re_vals[0]:,.0f} → {re_vals[-1]:,.0f}  |  "
        f"CL_req: {clreq_vals[0]:.4f} → {clreq_vals[-1]:.4f}<br>"
        f"<b>Perfis ({len(perfis)}):</b>  {perfis_str}"
    )

    fig2.update_layout(
        height=1050, width=1200, template="plotly_white",
        title=dict(
            text=(f"AsalabXYZ | Resumo Multi-Temperatura | AsaT: <b>{asat}</b> | "
                  f"T = {temperaturas[0]:.0f} → {temperaturas[-1]:.0f} °C  "
                  f"(passo {temperaturas[1]-temperaturas[0]:.1f} °C)  |  "
                  f"Lei de Sutherland — White §1.7"),
            x=0.5, font=dict(size=14)
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.015,
            xanchor="right", x=1, font=dict(size=10),
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="lightgray", borderwidth=1,
        ),
        margin=dict(t=110, b=160, l=80, r=80),
        plot_bgcolor="white",
    )
    fig2.add_annotation(
        xref="paper", yref="paper", x=0.5, y=-0.135,
        text=footer2, showarrow=False, align="left",
        font=dict(size=9, color="#222"),
        bgcolor="rgba(255,255,255,0.95)",
        bordercolor="#555", borderwidth=1, borderpad=12,
    )
    fig2.show()
    print("  [Multi-Temp] Figura 2 aberta no navegador.")
    print("  [Multi-Temp] Análise concluída.")


# ================================================================= #
# BLOCO DE DEMONSTRAÇÃO (roda apenas se executado diretamente)
# ================================================================= #
if __name__ == "__main__":
    print("\n" + "═" * 80)
    print("  LEI DE SUTHERLAND — PROPRIEDADES DO AR POR CONDIÇÃO")
    print("  μ = μ₀ · (T/T₀)^(3/2) · (T₀+S) / (T+S)")
    print("  μ₀ = 1.716×10⁻⁵ Pa·s  T₀ = 273.15 K  S = 110.4 K")
    print("═" * 80)
    print(f"  {'Cond.':<8} {'T [K]':>7} {'T [°C]':>7} {'P [kPa]':>9} "
          f"{'ρ [kg/m³]':>10} {'μ×10⁻⁵ [Pa·s]':>14} {'a [m/s]':>9}")
    print("  " + "─" * 72)
    for chave in ["slISA", "p30", "p25", "p20", "p15"]:
        atm = propriedades_por_condicao(chave)
        print(
            f"  {chave:<8} {atm['T_K']:>7.2f} {atm['T_C']:>7.2f} "
            f"{atm['P_Pa']/1000:>9.3f} {atm['rho']:>10.5f} "
            f"{atm['mu']*1e5:>14.5f} {atm['v_som']:>9.3f}"
        )

    imprimir_re_condicoes([8.0, 10.0, 12.0, 15.0, 20.0],
                          [0.15, 0.20, 0.30, 0.40, 0.60])

    print("\n" + "═" * 65)
    print("  ANÁLISE MULTI-TEMPERATURA — NACA 4412 + SELIG 1223")
    print("═" * 65)

    todos = calcular_asa_multi_temp(
        v=15.0, c=0.40, b=3.0, peso_kg=28.0,
        perfis_sel=["NACA 4412", "SELIG 1223"],
        asat_sel="Retangular",
        temp_min=15.0, temp_max=30.0, temp_step=1.0,
    )

    print("  RESUMO POR PERFIL — alpha_stall e LD_max em cada temperatura")
    print("  " + "─" * 80)
    print(f"  {'T [°C]':>8} {'Perfil':<28} {'α_stall [°]':>12} {'LD_max':>8} "
          f"{'cd0':>8} {'a0_2d [1/°]':>12}")
    print("  " + "─" * 80)

    for T in todos["temperaturas"]:
        dados = todos["dados"][float(T)]
        for pf, r in dados["resultados"].items():
            print(
                f"  {T:>8.1f} {pf:<28} {r['alpha_stall']:>12.2f} "
                f"{r['ld_max']:>8.2f} {r['cd0']:>8.5f} {r['a0_2d_raw']:>12.5f}"
            )
    print()
