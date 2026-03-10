import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. DATABASE DE AEROFÓLIOS (15 Perfis)
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

def engine_aero(pid, v, c, b, m_kg):
    d = AERO_DB[pid]
    nome, cla2d, a0, clm_ref, cd0_ref, cm0, t, curv = d
    rho, mu, g = 1.225, 1.789e-5, 9.81
    
    S, AR = b * c, b / (c if c > 0 else 0.1)
    e = np.clip((1.78 * (1 - 0.045 * (AR**0.68)) - 0.64) * 0.88, 0.60, 0.85)
    re = (rho * v * c) / mu
    w_n = m_kg * g
    
    clmax_re = lambda r: clm_ref * (0.6 + 0.11 * np.log10(np.maximum(r, 10000)/50000))
    clmax_v = clmax_re(re)
    
    alpha = np.linspace(-8, 20, 100)
    cla3d = cla2d / (1 + (cla2d / (np.pi * AR * e)))
    cl = np.where(cla3d*(alpha-a0) < clmax_v*0.9, cla3d*(alpha-a0), 
                  clmax_v - (clmax_v*0.1)*np.exp(-12*((cla3d*(alpha-a0))/clmax_v - 0.9)))
    cl = np.clip(cl, -0.5, clmax_v)
    cd = (cd0_ref*(re/500000)**-0.15 + 0.02*(cl - curv*10)**4) + ((cl**2)/(np.pi * AR * e))
    
    l_max = 0.5 * rho * v**2 * S * clmax_v
    cl_req = w_n / (0.5 * rho * v**2 * S)
    cd_req = (cd0_ref*(re/500000)**-0.15 + 0.02*(cl_req - curv*10)**4) + ((cl_req**2)/(np.pi * AR * e))
    
    return {
        'n': nome, 'a': alpha, 'cl': cl, 'cd': cd, 'ld': cl/cd, 're': re,
        's': S, 'ar': AR, 'w': w_n, 'l_max': l_max, 'drag': 0.5 * rho * v**2 * S * cd_req,
        'vs': np.sqrt((2 * w_n) / (rho * S * clmax_v)), 'cl_req': cl_req,
        're_range': np.geomspace(50000, 1500000, 50), 'clm_range': clmax_re(np.geomspace(50000, 1500000, 50))
    }

def plot_asa_lab(r1, r2):
    fig = make_subplots(
        rows=2, cols=3,
        specs=[[{"type": "xy"}, {"type": "xy"}, {"type": "table", "rowspan": 2}],
               [{"type": "xy"}, {"type": "xy"}, None]],
        subplot_titles=("Sustentação (CL vs Alpha)", "Eficiência (L/D)", "Tabela Técnica de Cálculos", "Polar de Arrasto", "Reynolds")
    )
    
    st = [("#040D1A", "solid", "Asa A"), ("#E95A07", "dash", "Asa B")]
    for i, r in enumerate([r1, r2]):
        fig.add_trace(go.Scatter(x=r['a'], y=r['cl'], name=f"{st[i][2]}: {r['n']}", line=dict(color=st[i][0], width=3, dash=st[i][1])), row=1, col=1)
        fig.add_trace(go.Scatter(x=r['a'], y=r['ld'], line=dict(color=st[i][0], dash=st[i][1]), showlegend=False), row=1, col=2)
        fig.add_trace(go.Scatter(x=r['cd'], y=r['cl'], line=dict(color=st[i][0], dash=st[i][1]), showlegend=False), row=2, col=1)
        fig.add_trace(go.Scatter(x=r['re_range'], y=r['clm_range'], line=dict(color=st[i][0], width=1, dash=st[i][1]), showlegend=False), row=2, col=2)
        fig.add_trace(go.Scatter(x=[r['re']], y=[np.max(r['cl'])], mode='markers', marker=dict(size=10, color=st[i][0]), showlegend=False), row=2, col=2)

    fig.add_trace(go.Table(
        header=dict(values=['<b>PARÂMETRO</b>', '<b>ASA A</b>', '<b>ASA B</b>'], fill_color='#111111', font=dict(color='white')),
        cells=dict(values=[
            ['Perfil', 'Área Alar (S)', 'Alongamento (AR)', 'Peso (W = m*g)', 'CL', 'CL max', 'Arrasto Total (D)', 'CL Req', 'Veloc. Stall', 'Reynolds'],
            [r1['n'], f"{r1['s']:.2f} m²", f"{r1['ar']:.2f}", f"{r1['w']:.1f} N", f"{r1['w']:.1f} N", f"{r1['l_max']:.1f} N", f"{r1['drag']:.2f} N", f"{r1['cl_req']:.3f}", f"{r1['vs']:.2f} m/s", f"{r1['re']:,.0f}"],
            [r2['n'], f"{r2['s']:.2f} m²", f"{r2['ar']:.2f}", f"{r2['w']:.1f} N", f"{r2['w']:.1f} N", f"{r2['l_max']:.1f} N", f"{r2['drag']:.2f} N", f"{r2['cl_req']:.3f}", f"{r2['vs']:.2f} m/s", f"{r2['re']:,.0f}"]
        ], fill_color='#FDFDFD', align='center')
    ), row=1, col=3)

    fig.update_layout(height=800, title_text="✈️ ASA LAB V9.5 ")
    fig.show()

if __name__ == "__main__":
    print(f"\n{' ASA LAB V9.5 - PERFIS DISPONÍVEIS ':=^60}")
    print(f"{'ID':<4} | {'PERFIL':<15} | {'CARACTERÍSTICA'}")
    print("-" * 60)
    perfis = ["Simétrico", "Camber Baixo", "Camber Médio", "Alta Sustentação", "Fundo Chato", "Carga Extrema", "STOL Especial", "Treinador Médio", "High-Speed", "Baixo Reynolds", "Alta Curvatura", "Aviação Geral", "Laminar", "Asa Grossa", "Planador Compet."]
    for i in range(1, 16):
        print(f"{i:<4} | {AERO_DB[str(i)][0]:<15} | {perfis[i-1]}")
    
    print("\n" + "="*60)
    ids = input("Digite os 2 IDs (ex: 6 11): ").split()
    
    get_d = lambda l: map(float, input(f"[{l}] Velocidade(m/s), Corda(m), Envergadura(m), Massa(kg): ").replace(',','.').split())
    v1, c1, b1, m1 = get_d("ASA A")
    v2, c2, b2, m2 = get_d("ASA B")
    
    plot_asa_lab(engine_aero(ids[0], v1, c1, b1, m1), engine_aero(ids[1], v2, c2, b2, m2))