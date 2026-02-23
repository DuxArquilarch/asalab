
import numpy as np
import matplotlib.pyplot as plt

# 1. BANCO DE DADOS  (1-15)
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
    '12':('Riblett GA',0.105, -3.5, 1.5, 0.007, -0.07, 0.12, 0.03),
    '13':('FX 60-126', 0.092, -4.5, 1.5, 0.008, -0.10, 0.12, 0.04),
    '14':('NACA 4418', 0.094, -3.8, 1.5, 0.009, -0.09, 0.18, 0.04),
    '15':('Drela AG24',0.108, -3.0, 1.4, 0.006, -0.05, 0.08, 0.02)
}

def get_rho(alt):
    return 1.225 * (1 - 2.25577e-5 * alt)**4.25588

def calc_aero(pid, v, c, b, w):
    n, cla2d, a0, clm_ref, cd0_ref, cm0, t, m = AERO_DB[pid]
    re = (1.225 * v * c) / 1.789e-5
    alpha = np.linspace(-5, 20, 100)
    cla3d = cla2d / (1 + (cla2d / (np.pi * (b/c) * 0.85)))
    cl = np.clip(np.where(alpha <= 12, cla3d*(alpha-a0), (clm_ref*0.9)-0.1*(alpha-12)), -0.5, clm_ref*0.95)
    cd = cd0_ref + (cl**2)/(np.pi*(b/c)*0.85)
    
    # Cálculo de Teto Aerodinâmico
    alts = np.linspace(0, 8000, 100)
    rhos = get_rho(alts)
    cl_req = (2 * w) / (rhos * v**2 * (c*b))
    cl_max = np.max(cl)
    idx_teto = np.where(cl_req <= cl_max)[0]
    teto = alts[idx_teto[-1]] if len(idx_teto) > 0 else 0
    
    return {'n':n, 'a':alpha, 'cl':cl, 'cd':cd, 're':re, 'cl_req':cl_req, 'alts':alts, 
            'clmax':cl_max, 'astall':alpha[np.argmax(cl)], 'teto':teto, 't':t, 'ld':cl/cd}

def plot_res(r1, r2):
    c1, c2, c_st = '#008000', '#FF4500', '#000000'
    fig = plt.figure(figsize=(16, 9), facecolor='white')
    
    # Layout: 2 colunas principais (Gráficos vs Dados)
    gs = fig.add_gridspec(2, 3, width_ratios=[1, 1, 0.7])

    # CL vs AoA
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(r1['a'], r1['cl'], color=c1, lw=2.5, label=r1['n'])
    ax1.plot(r2['a'], r2['cl'], color=c2, lw=2.5, ls='--', label=r2['n'])
    ax1.axvline(r1['astall'], color=c_st, ls=':', lw=1.2)
    ax1.axvline(r2['astall'], color=c_st, ls=':', lw=1.2)
    ax1.set_title("Sustentação ($C_L$)", weight='bold'); ax1.grid(True, alpha=0.2)

    # L/D vs AoA
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(r1['a'], r1['ld'], color=c1, lw=2.5)
    ax2.plot(r2['a'], r2['ld'], color=c2, lw=2.5, ls='--')
    ax2.set_title("Eficiência ($L/D$)", weight='bold'); ax2.grid(True, alpha=0.2)

    # Polar de Arrasto
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.plot(r1['cd'], r1['cl'], color=c1, lw=2.5)
    ax3.plot(r2['cd'], r2['cl'], color=c2, lw=2.5, ls='--')
    ax3.set_title("Polar de Arrasto", weight='bold'); ax3.grid(True, alpha=0.2)

    # Teto de Serviço
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.plot(r1['alts'], r1['cl_req'], color=c1, lw=2)
    ax4.plot(r2['alts'], r2['cl_req'], color=c2, lw=2, ls='--')
    ax4.axhline(r1['clmax'], color=c1, ls=':', alpha=0.4)
    ax4.axhline(r2['clmax'], color=c2, ls=':', alpha=0.4)
    ax4.set_ylim(0, 2.5); ax4.set_title("Teto: $C_L$ Necessário", weight='bold')
    ax4.set_xlabel("Altitude (m)"); ax4.grid(True, alpha=0.2)

    # --- LADO DIREITO: PERFIS, REYNOLDS E TABELA ---
    # 1. Perfis Geométricos (Topo Direita)
    ax_g = fig.add_subplot(gs[0, 2])
    for i, (r, color) in enumerate([(r1, c1), (r2, c2)]):
        x = np.linspace(0, 1, 60); yt = 5 * r['t'] * (0.2969*np.sqrt(x)-0.126*x-0.3516*x**2+0.2843*x**3-0.1015*x**4)
        y_sh = 0.5 if i == 0 else -0.5
        ax_g.plot(x, y_sh+yt, color, lw=2); ax_g.plot(x, y_sh-yt, color, lw=2)
        ax_g.fill_between(x, y_sh+yt, y_sh-yt, color=color, alpha=0.1)
        ax_g.text(0.5, y_sh-0.3, r['n'], color=color, ha='center', weight='bold', fontsize=9)
    ax_g.set_title("Geometria dos Perfis", fontsize=10, pad=10)
    ax_g.set(xlim=(-0.1, 1.1), ylim=(-1, 1)); ax_g.axis('off')

    # 2. Reynolds e Tabela (Abaixo dos Perfis)
    ax_t = fig.add_subplot(gs[1, 2]); ax_t.axis('off')
    
    # Dados formatados
    tab_d = [
        ['Reynolds (Re)', f"{r1['re']:,.0f}", f"{r2['re']:,.0f}"],
        ['$C_L$ Máximo', f"{r1['clmax']:.3f}", f"{r2['clmax']:.3f}"],
        ['Ângulo Stall', f"{r1['astall']:.1f}°", f"{r2['astall']:.1f}°"],
        ['Eficiência Max', f"{np.max(r1['ld']):.1f}", f"{np.max(r2['ld']):.1f}"],
        ['TETO SERVIÇO', f"{r1['teto']:.0f} m", f"{r2['teto']:.0f} m"]
    ]
    
    t = ax_t.table(cellText=tab_d, colLabels=['Parâmetro', r1['n'], r2['n']], loc='center')
    t.auto_set_font_size(False); t.set_fontsize(8.5); t.scale(1.2, 3.8)
    
    # Destaque para a linha do Reynolds
    for j in range(3): t.get_celld()[(1, j)].set_facecolor('#f9f9f9')

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    print(f"\n{' Asa Lab V7 ':=^50}")
    it = list(AERO_DB.items())
    for i in range(0, len(it), 3): print("  ".join([f"[{k:>2}] {v[0]:<15}" for k, v in it[i:i+3]]))
    try:
        ids = input("\nIDs dos perfis: ").split()
        v, c, b, w = map(float, input("Vel(m/s) Corda(m) Env(m) Peso(N): ").split())
        plot_res(calc_aero(ids[0], v, c, b, w), calc_aero(ids[1], v, c, b, w))
    except: print("\n[ERRO] Verifique as entradas.")


