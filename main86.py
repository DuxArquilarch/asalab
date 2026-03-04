import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. DATABASE COMPLETO (Nome, Cl_alfa, Alfa_0, Cl_max_ref, Cd0_ref, Cm0, t, m)
AERO_DB = {
    '1': ('NACA 0012', 0.105, 0.0, 1.6, 0.006, 0.00, 0.12, 0.00),
    '2': ('NACA 2412', 0.100, -2.5, 1.4, 0.007, -0.05, 0.12, 0.02),
    '3': ('NACA 4412', 0.095, -4.0, 1.5, 0.008, -0.09, 0.12, 0.04),
    '4': ('FX 63-137', 0.088, -6.0, 2.0, 0.009, -0.12, 0.13, 0.06),
    '5': ('Clark Y',   0.090, -5.0, 1.7, 0.008, -0.08, 0.11, 0.03),
    '6': ('Selig S1223', 0.110, -8.0, 2.2, 0.015, -0.15, 0.12, 0.08),
    '7': ('Eppler 423', 0.102, -7.5, 2.0, 0.012, -0.14, 0.12, 0.07),
    '8': ('NACA 4415', 0.100, -4.2, 1.6, 0.007, -0.09, 0.15, 0.04),
    '9': ('MH 32',      0.108, -2.2, 1.3, 0.006, -0.04, 0.08, 0.02),
    '10':('DAE-21',    0.112, -4.5, 1.5, 0.005, -0.11, 0.09, 0.04),
    '11':('NACA 6412', 0.100, -6.0, 1.7, 0.009, -0.13, 0.12, 0.06),
    '12':('Riblett GA', 0.105, -3.5, 1.5, 0.007, -0.07, 0.12, 0.03),
    '13':('FX 60-126', 0.092, -4.5, 1.5, 0.008, -0.10, 0.12, 0.04),
    '14':('NACA 4418', 0.094, -3.8, 1.5, 0.009, -0.09, 0.18, 0.04),
    '15':('Drela AG24', 0.108, -3.0, 1.4, 0.006, -0.05, 0.08, 0.02)
}

def calc_aero_v9(pid, v, c, b, w):
    dados = AERO_DB[pid]
    n, cla2d, a0, clm_ref, cd0_ref, cm0, t, m = dados
    rho = 1.225
    mu = 1.789e-5
    S = b * c
    AR = b / c
    e = 0.85 # Fator de Oswald

    # CÁLCULO DE REYNOLDS E SENSIBILIDADE (Física de Camada Limite)
    re = (rho * v * c) / mu
    re_range = np.geomspace(50000, 1000000, 50)
    
    # Ajuste de Cl_max via Reynolds (Aproximação XFOIL)
    clmax_func = lambda r: clm_ref * (0.6 + 0.11 * np.log10(r/50000))
    cl_max_atual = clmax_func(re)
    
    # Ajuste de Cd0 via Reynolds 
    cd0_real = cd0_ref * (re / 500000)**-0.15 
    
    # CURVA DE SUSTENTAÇÃO (Linear com arredondamento no estol)
    alpha = np.linspace(-6, 20, 100)
    cla3d = cla2d / (1 + (cla2d / (np.pi * AR * e)))
    cl_linear = cla3d * (alpha - a0)
    
    # Modelagem de transição suave para o estol
    cl = np.where(cl_linear < cl_max_atual * 0.9, 
                  cl_linear, 
                  cl_max_atual - (cl_max_atual * 0.1) * np.exp(-12 * (cl_linear/cl_max_atual - 0.9)))
    cl = np.where(alpha > 15, cl_max_atual * 0.7 - 0.05*(alpha-15), cl) # Decaimento pós-estol
    cl = np.clip(cl, -0.4, cl_max_atual)

    # POLAR DE ARRASTO REALISTA (Bucket Laminar e Induzido)
    cl_design = m * 10 
    cd_perfil = cd0_real + 0.015 * (cl - cl_design)**4 # Penalidade fora do range de projeto
    cd_induzido = (cl**2) / (np.pi * AR * e)
    cd = cd_perfil + cd_induzido

    # PERFORMANCE E ENVELOPE DE VOO
    v_stall = np.sqrt((2 * w) / (rho * S * cl_max_atual))
    ld = cl / cd
    
    return {
        'n': n, 'a': alpha, 'cl': cl, 'cd': cd, 're': re, 'ld': ld,
        'clmax': cl_max_atual, 'v_stall': v_stall, 'astall': alpha[np.argmax(cl)],
        're_range': re_range, 'clmax_sens': clmax_func(re_range), 's': S
    }

def plot_res_v9(r1, r2):
    fig = make_subplots(
        rows=2, cols=3,
        specs=[[{"type": "xy"}, {"type": "xy"}, {"type": "table", "rowspan": 2}],
               [{"type": "xy"}, {"type": "xy"}, None]],
        subplot_titles=("Curva de Sustentação Realista", "Eficiência Aerodinâmica (L/D)", 
                        "Análise de Missão", "Polar de Arrasto (Cd vs Cl)", "Sensibilidade do Perfil (Re)"),
        horizontal_spacing=0.1, vertical_spacing=0.15
    )

    colors = [("#494949", "solid"), ("#0D6EFF", 'dash')] 

    for i, r in enumerate([r1, r2]):
        color, dash = colors[i]
        
        # 1. Cl vs Alpha
        fig.add_trace(go.Scatter(x=r['a'], y=r['cl'], name=r['n'], line=dict(color=color, width=3, dash=dash)), row=1, col=1)
        
        # 2. L/D
        fig.add_trace(go.Scatter(x=r['a'], y=r['ld'], line=dict(color=color, dash=dash), showlegend=False), row=1, col=2)

        # 3. Polar Cd vs Cl (X-Bucket)
        fig.add_trace(go.Scatter(x=r['cd'], y=r['cl'], line=dict(color=color, dash=dash), showlegend=False), row=2, col=1)

        # 4. Sensibilidade Re
        fig.add_trace(go.Scatter(x=r['re_range'], y=r['clmax_sens'], line=dict(color=color, dash=dash), showlegend=False), row=2, col=2)
        fig.add_trace(go.Scatter(x=[r['re']], y=[r['clmax']], mode='markers', marker=dict(color=color, size=10, symbol='diamond')), row=2, col=2)

    # TABELA DE ENGENHARIA
    fig.add_trace(
        go.Table(
            header=dict(values=['<b>Métrica</b>', f'<b>{r1["n"]}</b>', f'<b>{r2["n"]}</b>'],
                        fill_color='#1A237E', font=dict(color='white')),
            cells=dict(values=[
                ['Velocidade de Estol', 'L/D Máximo (Cruise)', 'Reynolds de Voo', 'Área da Asa (S)'],
                [f"{r1['v_stall']:.2f} m/s", f"{np.max(r1['ld']):.1f}", f"{r1['re']:,.0f}", f"{r1['s']:.2f} m²"],
                [f"{r2['v_stall']:.2f} m/s", f"{np.max(r2['ld']):.1f}", f"{r2['re']:,.0f}", f"{r2['s']:.2f} m²"]
            ], fill_color='#F5F5F5', align='center')
        ), row=1, col=3
    )

    fig.update_layout(title="<b>Asa Lab V8.6 - Engenharia de Asas </b>", template="plotly_white", height=850)
    fig.show()

if __name__ == "__main__":
    print(f"\n{' ASA LAB V8.6 ':=^50}")
    for k in sorted(AERO_DB.keys(), key=int): print(f"[{k}] {AERO_DB[k][0]}")
    
    try:
        ids = input("\nIDs para comparação (ex: 1 6): ").split()
        v, c, b, w = map(float, input("Vel(m/s) Corda(m) Env(m) Peso(N): ").split())
        
        res1 = calc_aero_v9(ids[0], v, c, b, w)
        res2 = calc_aero_v9(ids[1], v, c, b, w)
        plot_res_v9(res1, res2)
    except Exception as e:
        print(f"\n[ERRO]: {e}")