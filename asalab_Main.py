# ================================================================= #
# AsalabXYZ — SISTEMA UNIFICADO v2.0                                #
#                                                                    #
# GUI baseada no estilo do AeroSim (exp3_v2.py)                     #
# Integra:                                                           #
#   Módulo 1 — DATABASE (aerofólios + materiais)                    #
#   Módulo 2 — CÁLCULOS AERODINÂMICOS (calculos.py)                 #
#   Módulo 3 — GRÁFICOS (analise_graficos.py)                       #
#   Módulo 4 — MATERIAIS / PESO / STALL (materiais_peso_stall.py)   #
#                                                                    #
# Referências:                                                        #
#   White, F.M. Fluid Mechanics, 8ª Ed. McGraw-Hill, 2016.          #
#   Sadraey, M. Aircraft Design. Wiley, 2013.                       #
#   Raymer, D. Aircraft Design, 5ª Ed., 2012.                       #
# ================================================================= #

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np

from database import DATABASE, AsaT
from materiais_peso_stall import MATERIAIS, CL_MAX_2D, CD0_PERFIL


# ─────────────────────────────────────────────────────────────────
# PALETA DARK (idêntica ao AeroSim)
# ─────────────────────────────────────────────────────────────────
BG     = "#0d1117"
PANEL  = "#161b22"
ACCENT = "#58a6ff"
TEXT   = "#e6edf3"
MUTED  = "#8b949e"
GREEN  = "#3fb950"
YELLOW = "#d29922"
RED    = "#f85149"
BORDER = "#30363d"


# ─────────────────────────────────────────────────────────────────
# HELPERS DE ESTILO
# ─────────────────────────────────────────────────────────────────
def _label(parent, text, fg=TEXT, font=("Courier", 9), **kw):
    return tk.Label(parent, text=text, bg=BG, fg=fg, font=font, **kw)

def _label_panel(parent, text, fg=TEXT, font=("Courier", 9), **kw):
    return tk.Label(parent, text=text, bg=PANEL, fg=fg, font=font, **kw)

def _section(parent, title):
    f = tk.LabelFrame(parent, text=f" {title} ", bg=BG, fg=ACCENT,
                      font=("Courier", 9, "bold"), bd=1,
                      highlightbackground=BORDER, pady=6, padx=8)
    f.pack(fill="x", pady=5)
    return f

def _entry(parent, var, width=12):
    e = tk.Entry(parent, textvariable=var, bg="#21262d", fg=TEXT,
                 insertbackground=TEXT, relief="flat", width=width,
                 font=("Courier", 10))
    return e

def _scale(parent, var, from_, to, label, resolution=0.5):
    f = tk.Frame(parent, bg=PANEL)
    f.pack(fill="x", pady=2)
    tk.Label(f, text=label, bg=PANEL, fg=MUTED,
             font=("Courier", 8), width=26, anchor="w").pack(side="left")
    s = tk.Scale(f, from_=from_, to=to, resolution=resolution,
                 orient="horizontal", variable=var, bg=PANEL, fg=TEXT,
                 highlightthickness=0, troughcolor="#21262d",
                 activebackground=ACCENT, length=260)
    s.pack(side="left", fill="x", expand=True)
    val_lbl = tk.Label(f, textvariable=var, bg=PANEL, fg=ACCENT,
                       font=("Courier", 9, "bold"), width=7)
    val_lbl.pack(side="left")
    return s

def _btn(parent, text, cmd, bg=ACCENT, fg=BG, font=("Courier", 10, "bold")):
    return tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                     font=font, relief="flat", padx=8, pady=6,
                     activebackground="#79c0ff", activeforeground=BG,
                     cursor="hand2")

def _checkbtn(parent, text, var):
    return tk.Checkbutton(parent, text=text, variable=var,
                          bg=BG, fg=TEXT, selectcolor=PANEL,
                          activebackground=BG, activeforeground=ACCENT,
                          font=("Courier", 9))

def _radio(parent, text, var, val):
    return tk.Radiobutton(parent, text=text, variable=var, value=val,
                          bg=PANEL, fg=TEXT, selectcolor=BG,
                          activebackground=PANEL, activeforeground=ACCENT,
                          font=("Courier", 9))

def _listbox(parent, items, height=5, selectmode=tk.MULTIPLE):
    frame = tk.Frame(parent, bg=PANEL)
    sb = tk.Scrollbar(frame, orient="vertical", bg=PANEL)
    lb = tk.Listbox(frame, height=height, selectmode=selectmode,
                    bg="#21262d", fg=TEXT, font=("Courier", 8),
                    selectbackground=ACCENT, selectforeground=BG,
                    relief="flat", activestyle="none",
                    yscrollcommand=sb.set, exportselection=False)
    sb.config(command=lb.yview)
    sb.pack(side="right", fill="y")
    lb.pack(side="left", fill="both", expand=True)
    for item in items:
        lb.insert(tk.END, item)
    frame.pack(fill="x", pady=2)
    return lb


# ─────────────────────────────────────────────────────────────────
# JANELA PRINCIPAL
# ─────────────────────────────────────────────────────────────────
def launch_asalab_gui():
    """
    GUI unificada do AsaLab.
    Retorna dict com todos os parâmetros, ou None se cancelado.
    """
    root = tk.Tk()
    root.title("AsalabXYZ 𝐈𝐈 Simulador Aerodinâmico")
    root.configure(bg=BG)
    root.resizable(True, True)

    result = {"cancelled": True}

    # ── Cabeçalho ──────────────────────────────────────────────
    hdr = tk.Frame(root, bg=PANEL, pady=10)
    hdr.pack(fill="x")
    tk.Label(hdr, text="ASALAB XYZ  𝐈𝐈", bg=PANEL, fg=ACCENT,
             font=("Courier", 18, "bold")).pack()
    tk.Label(hdr, text="White §8 · Sadraey 2013 · Raymer 2012",
             bg=PANEL, fg=MUTED, font=("Courier", 8)).pack()

    # ── Notebook (abas) ────────────────────────────────────────
    style = ttk.Style()
    style.theme_use("default")
    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED,
                    font=("Courier", 9, "bold"), padding=[12, 5])
    style.map("TNotebook.Tab",
              background=[("selected", ACCENT)],
              foreground=[("selected", BG)])

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True, padx=10, pady=6)

    # ════════════════════════════════════════════════════════════
    # ABA 1 — PARÂMETROS DE VOO
    # ════════════════════════════════════════════════════════════
    tab1 = tk.Frame(nb, bg=BG)
    nb.add(tab1, text="  ✈ VOO  ")

    # Canvas + scrollbar para aba longa
    canvas1 = tk.Canvas(tab1, bg=BG, highlightthickness=0)
    sb1 = tk.Scrollbar(tab1, orient="vertical", command=canvas1.yview)
    canvas1.configure(yscrollcommand=sb1.set)
    sb1.pack(side="right", fill="y")
    canvas1.pack(side="left", fill="both", expand=True)
    inner1 = tk.Frame(canvas1, bg=BG, padx=14)
    canvas1.create_window((0, 0), window=inner1, anchor="nw")
    inner1.bind("<Configure>", lambda e: canvas1.configure(
        scrollregion=canvas1.bbox("all")))

    # Variáveis — parâmetros de voo
    v_var    = tk.DoubleVar(value=15.0)
    c_var    = tk.DoubleVar(value=0.60)
    b_var    = tk.DoubleVar(value=3.0)
    peso_var = tk.DoubleVar(value=5.0)

    s_voo = _section(inner1, "PARÂMETROS DE VOO")
    _scale(s_voo, v_var,    from_=3,   to=80,  label="Velocidade (m/s)",  resolution=0.5)
    _scale(s_voo, c_var,    from_=0.1, to=2.0, label="Corda c (m)",       resolution=0.05)
    _scale(s_voo, b_var,    from_=0.3, to=12,  label="Envergadura b (m)", resolution=0.1)
    _scale(s_voo, peso_var, from_=0.1, to=50,  label="Peso total (kg)",   resolution=0.1)

    # AR preview
    ar_lbl_var = tk.StringVar()
    def _upd_ar(*_):
        b = b_var.get(); c = c_var.get()
        ar = b**2 / (b * c) if c > 0 else 0
        s  = b * c
        ar_lbl_var.set(f"AR = {ar:.2f}   |   S = {s:.3f} m²")
    for var in (b_var, c_var):
        var.trace_add("write", _upd_ar)
    _upd_ar()
    tk.Label(s_voo, textvariable=ar_lbl_var, bg=PANEL, fg=GREEN,
             font=("Courier", 9, "bold")).pack(pady=4)

    # Tipo de asa
    s_asat = _section(inner1, "TIPO DE ASA (AsaT) — White §8")
    asat_var = tk.StringVar(value="Retangular")
    for k, v in AsaT.items():
        descr = {"Retangular": "e_Oswald        | κ=1.00",
                 "Elíptica":   "e=1.00          | κ=1.00",
                 "Delta":      "e empírico      | κ=0.90"}[v]
        f = tk.Frame(s_asat, bg=PANEL); f.pack(fill="x", pady=1)
        _radio(f, f"[{k}] {v:<14} — {descr}", asat_var, v).pack(side="left")

    # Seleção de Perfis (1–3)
    s_perf = _section(inner1, "AEROFÓLIOS (selecione 1 a 3) — White §8.1")
    perfis_lista = list(DATABASE.keys())
    # Construir descrição enriquecida
    perf_descs = []
    for p in perfis_lista:
        fam = ("5-dígitos" if any(d in p for d in ["23012","23015"])
               else "6-dígitos" if any(d in p for d in ["63-","65-"])
               else "4-dígitos")
        clm = CL_MAX_2D.get(p, "—")
        cd0 = CD0_PERFIL.get(p, "—")
        clm_s = f"{clm:.3f}" if isinstance(clm, float) else str(clm)
        cd0_s = f"{cd0:.5f}" if isinstance(cd0, float) else str(cd0)
        perf_descs.append(f"{p:<30}  CLmax={clm_s}  CD0={cd0_s}  [{fam}]")

    lb_perfis = _listbox(s_perf, perf_descs, height=len(perfis_lista), selectmode=tk.MULTIPLE)
    lb_perfis.selection_set(0)
    tk.Label(s_perf, text="Ctrl+clique para múltipla seleção (máx. 3)",
             bg=PANEL, fg=MUTED, font=("Courier", 7)).pack()

    # ════════════════════════════════════════════════════════════
    # ABA 2 — CÁLCULOS DE MATERIAIS (unificado do Módulo 4)
    # ════════════════════════════════════════════════════════════
    tab2 = tk.Frame(nb, bg=BG)
    nb.add(tab2, text="  🔩 MATERIAIS  ")

    canvas2 = tk.Canvas(tab2, bg=BG, highlightthickness=0)
    sb2 = tk.Scrollbar(tab2, orient="vertical", command=canvas2.yview)
    canvas2.configure(yscrollcommand=sb2.set)
    sb2.pack(side="right", fill="y")
    canvas2.pack(side="left", fill="both", expand=True)
    inner2 = tk.Frame(canvas2, bg=BG, padx=14)
    canvas2.create_window((0, 0), window=inner2, anchor="nw")
    inner2.bind("<Configure>", lambda e: canvas2.configure(
        scrollregion=canvas2.bbox("all")))

    ativar_mat_var = tk.BooleanVar(value=False)
    s_mat_toggle = _section(inner2, "ANÁLISE DE MATERIAIS / PESO / STALL")
    _checkbtn(s_mat_toggle, "Ativar análise de materiais (Sadraey 2013)", ativar_mat_var).pack(anchor="w")

    # Modo de análise
    s_modo = _section(inner2, "MODO DE ANÁLISE")
    modo_var = tk.StringVar(value="1")
    modos = [
        ("1", "Análise completa    — 1 perfil + 1 material  (4 tabelas: Peso | Stall | CD0 | Alertas)"),
        ("2", "Comparar materiais  — todos os materiais, perfil principal"),
        ("3", "Comparar aerofólios — todos os perfis, 1 material selecionado"),
    ]
    for val, txt in modos:
        f = tk.Frame(s_modo, bg=PANEL); f.pack(fill="x", pady=1)
        _radio(f, txt, modo_var, val).pack(side="left")

    # Missão RC
    s_miss = _section(inner2, "PARÂMETROS DA MISSÃO RC")
    vc_var      = tk.DoubleVar(value=12.0)
    payload_var = tk.DoubleVar(value=2.5)
    trem_var    = tk.BooleanVar(value=True)
    _scale(s_miss, vc_var,      from_=3,  to=60, label="V_cruzeiro (m/s)", resolution=0.5)
    _scale(s_miss, payload_var, from_=0.1, to=25, label="Payload útil (kg)", resolution=0.1)
    f_trem = tk.Frame(s_miss, bg=PANEL); f_trem.pack(fill="x", pady=2)
    _checkbtn(f_trem, "Incluir trem de pouso fixo (Sadraey §3.6)", trem_var).pack(side="left")

    # Material único (modos 1 e 3)
    s_mat1 = _section(inner2, "MATERIAL — seleção única (modos 1 e 3)")
    mats_lista = list(MATERIAIS.keys())
    mat_descs = []
    for m in mats_lista:
        mi = MATERIAIS[m]
        mat_descs.append(
            f"{m:<37}  ρ={mi['densidade_kg_m3']:>4} kg/m³  "
            f"e={mi['espessura_mm']} mm  ΔCd0={mi['cd0_rugosidade']:.4f}"
        )
    lb_mat1 = _listbox(s_mat1, mat_descs, height=len(mats_lista), selectmode=tk.SINGLE)
    lb_mat1.selection_set(0)

    # Descrição do material selecionado
    mat_desc_var = tk.StringVar(value=MATERIAIS[mats_lista[0]]["descricao"])
    desc_lbl = tk.Label(s_mat1, textvariable=mat_desc_var, bg=PANEL, fg=MUTED,
                        font=("Courier", 8), wraplength=600, justify="left")
    desc_lbl.pack(anchor="w", pady=2)
    def _upd_mat_desc(evt=None):
        sel = lb_mat1.curselection()
        if sel:
            mat_desc_var.set(MATERIAIS[mats_lista[sel[0]]]["descricao"])
    lb_mat1.bind("<<ListboxSelect>>", _upd_mat_desc)

    # Múltiplos materiais (modo 2)
    s_mat2 = _section(inner2, "MATERIAIS — seleção múltipla (modo 2 — comparar)")
    lb_mat2 = _listbox(s_mat2, mat_descs, height=8, selectmode=tk.MULTIPLE)
    for i in range(len(mats_lista)):
        lb_mat2.selection_set(i)
    tk.Label(s_mat2, text="Ctrl+clique para múltipla seleção",
             bg=PANEL, fg=MUTED, font=("Courier", 7)).pack()

    # ════════════════════════════════════════════════════════════
    # ABA 3 — GRÁFICOS DE MATERIAIS (controle de saída)
    # ════════════════════════════════════════════════════════════
    tab3 = tk.Frame(nb, bg=BG)
    nb.add(tab3, text="  📊 GRÁFICOS  ")

    inner3 = tk.Frame(tab3, bg=BG, padx=14)
    inner3.pack(fill="both", expand=True, pady=6)

    s_graf = _section(inner3, "GRÁFICOS AERODINÂMICOS (Figura 1 — sempre gerada)")
    tk.Label(s_graf, text="  CL · CD · L/D · Cm · XCp · Silhueta da asa\n"
             "  Layout 2×3 — White §8.1, §8.3, §8.4, §8.7",
             bg=PANEL, fg=MUTED, font=("Courier", 9), justify="left").pack(anchor="w", pady=4)

    s_graf2 = _section(inner3, "GRÁFICOS DE MATERIAIS (Figura 2 — requer aba Materiais ativa)")
    show_mat_graf_var = tk.BooleanVar(value=True)
    _checkbtn(s_graf2,
              "Gerar gráfico/tabelas de materiais (Sadraey Cap.5/6 + White §7.3)",
              show_mat_graf_var).pack(anchor="w")

    tk.Label(s_graf2,
             text=(
                 "  Modo 1: 4 tabelas — Peso estrutural | Stall & Desempenho | Decomp. CD0 | Alertas\n"
                 "  Modo 2: tabela comparativa de todos os materiais\n"
                 "  Modo 3: tabela comparativa de todos os aerofólios"
             ),
             bg=PANEL, fg=MUTED, font=("Courier", 8), justify="left").pack(anchor="w", pady=2)

    # Resumo dinâmico
    s_resumo = _section(inner3, "RESUMO DOS PARÂMETROS ATUAIS")
    resumo_var = tk.StringVar()
    def _upd_resumo(*_):
        v = v_var.get(); c = c_var.get(); b = b_var.get(); pe = peso_var.get()
        s = b * c; ar = b**2 / s if s > 0 else 0
        rho = 1.225; mu = 1.849e-5
        re = rho * v * c / mu
        vc = vc_var.get(); pl = payload_var.get()
        resumo_var.set(
            f"V={v} m/s  c={c} m  b={b} m  W={pe} kg\n"
            f"S={s:.3f} m²  AR={ar:.2f}  Re={re:.0f}\n"
            f"Asa: {asat_var.get()}  |  V_cruise={vc} m/s  Payload={pl} kg"
        )
    for var in (v_var, c_var, b_var, peso_var, vc_var, payload_var, asat_var):
        if hasattr(var, 'trace_add'):
            var.trace_add("write", _upd_resumo)
    _upd_resumo()
    tk.Label(inner3, textvariable=resumo_var, bg=PANEL, fg=ACCENT,
             font=("Courier", 9), relief="flat", padx=10, pady=8,
             justify="left").pack(fill="x", pady=4)

    # ════════════════════════════════════════════════════════════
    # BARRA INFERIOR — BOTÕES
    # ════════════════════════════════════════════════════════════
    bar = tk.Frame(root, bg=PANEL, pady=10, padx=12)
    bar.pack(fill="x")

    status_var = tk.StringVar(value="Pronto.")
    tk.Label(bar, textvariable=status_var, bg=PANEL, fg=MUTED,
             font=("Courier", 8)).pack(side="left", padx=8)

    def _cancel():
        result["cancelled"] = True
        root.destroy()

    def _run():
        # Validação de perfis
        sel_perf_idx = lb_perfis.curselection()
        if not sel_perf_idx:
            messagebox.showerror("AsaLab", "Selecione pelo menos 1 aerofólio.")
            return
        if len(sel_perf_idx) > 3:
            messagebox.showerror("AsaLab", "Selecione no máximo 3 aerofólios.")
            return

        perfis_sel = [perfis_lista[i] for i in sel_perf_idx]

        # Cfg materiais
        cfg_mat = None
        if ativar_mat_var.get():
            modo = modo_var.get()
            # material único
            sel_m1 = lb_mat1.curselection()
            mat_unico = mats_lista[sel_m1[0]] if sel_m1 else mats_lista[0]
            # múltiplos materiais
            sel_m2 = lb_mat2.curselection()
            mats_multi = [mats_lista[i] for i in sel_m2] if sel_m2 else mats_lista[:]

            cfg_mat = {
                "modo":            modo,
                "v_cruise":        vc_var.get(),
                "payload":         payload_var.get(),
                "v_max":           v_var.get(),
                "com_trem":        trem_var.get(),
                "perfil_principal":perfis_sel[0],
                "lista_mat":       mats_multi if modo == "2" else mats_lista,
                "material":        mat_unico,
                "show_graf":       show_mat_graf_var.get(),
            }

        result.update({
            "cancelled":  False,
            "v":          v_var.get(),
            "c":          c_var.get(),
            "b":          b_var.get(),
            "peso_kg":    peso_var.get(),
            "perfis_sel": perfis_sel,
            "asat_sel":   asat_var.get(),
            "cfg_mat":    cfg_mat,
        })
        status_var.set("Calculando…")
        root.destroy()

    _btn(bar, "CANCELAR", _cancel, bg="#30363d", fg=TEXT).pack(side="right", padx=6)
    _btn(bar, " ✈  EXECUTAR SIMULAÇÃO ", _run, bg=ACCENT, fg=BG).pack(side="right", padx=6)

    # Centralizar janela
    root.update_idletasks()
    w, h = 780, 700
    sw = root.winfo_screenwidth(); sh = root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    root.mainloop()
    return result


# ─────────────────────────────────────────────────────────────────
# PONTO DE ENTRADA — integra com analise_graficos
# ─────────────────────────────────────────────────────────────────
def main():
    cfg = launch_asalab_gui()
    if cfg["cancelled"]:
        print("Simulação cancelada.")
        return

    print("\n" + "═"*65)
    print("  ASALAB XYZ 𝐈𝐈 — Iniciando simulação")
    print("═"*65)
    print(f"  V={cfg['v']} m/s | c={cfg['c']} m | b={cfg['b']} m | W={cfg['peso_kg']} kg")
    print(f"  Perfis: {', '.join(cfg['perfis_sel'])}")
    print(f"  AsaT: {cfg['asat_sel']}")
    if cfg['cfg_mat']:
        m = cfg['cfg_mat']
        print(f"  Módulo 4: modo={m['modo']} | material={m.get('material','todos')} | "
              f"payload={m['payload']} kg | V_cruise={m['v_cruise']} m/s")
    print("═"*65 + "\n")

    # Importa após GUI para não bloquear tkinter
    from calculos import calcular_asa
    from analise_graficos import plotar_resultados

    dados = calcular_asa(
        cfg["v"], cfg["c"], cfg["b"], cfg["peso_kg"],
        cfg["perfis_sel"], cfg["asat_sel"]
    )
    plotar_resultados(dados, cfg["cfg_mat"] if cfg["cfg_mat"] and cfg["cfg_mat"].get("show_graf", True) else None)


if __name__ == "__main__":
    main()
