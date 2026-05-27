# ================================================================= #
# Dark Wing Project — MÓDULO: VISUALIZADOR DE GEOMETRIAS                    #
#                                                                    #
# Menu GUI independente para visualização de:                        #
#   • Perfil aerodinâmico (seção transversal)                       #
#   • Silhueta da asa (planta baixa semi-envergadura)               #
#   • Estatísticas geométricas e métricas de perfil                 #
#   • Comparação lado-a-lado de até 3 perfis                        #
#                                                                    #
# Requer: database.py, analise_ra_calc.py (mesma pasta)             #
# ================================================================= #

import tkinter as tk
from tkinter import ttk
import numpy as np
import importlib, importlib.util, sys, os

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

# ── carrega database dinâmico ─────────────────────────────────────
_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.py")
def _load_db():
    spec = importlib.util.spec_from_file_location("database", _DB_PATH)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules["database"] = mod
    return mod
_load_db()

from analise_ra_calc import gerar_coord_naca, gerar_silhueta_asat, geometria_de_ra_e_s

# ── paleta dark (igual ao gui.py) ─────────────────────────────────
BG     = "#0d1117"
PANEL  = "#161b22"
ACCENT = "#58a6ff"
TEXT   = "#e6edf3"
MUTED  = "#8b949e"
GREEN  = "#3fb950"
YELLOW = "#d29922"
RED    = "#f85149"
BORDER = "#30363d"

# paleta matplotlib para até 3 perfis
CORES_PLOT = ["#58a6ff", "#3fb950", "#f0883e"]

# estilos matplotlib dark
PLT_STYLE = {
    "figure.facecolor":  BG,
    "axes.facecolor":    PANEL,
    "axes.edgecolor":    BORDER,
    "axes.labelcolor":   MUTED,
    "axes.titlecolor":   TEXT,
    "xtick.color":       MUTED,
    "ytick.color":       MUTED,
    "grid.color":        BORDER,
    "grid.linewidth":    0.5,
    "text.color":        TEXT,
    "lines.linewidth":   2.0,
    "font.family":       "monospace",
    "font.size":         9,
}


# ================================================================= #
# HELPERS DE GEOMETRIA                                               #
# ================================================================= #

def _metricas_perfil(nome: str):
    """Retorna dicionário com métricas geométricas do perfil."""
    x, yu, yl = gerar_coord_naca(nome)
    camber    = (yu + yl) / 2.0
    thickness = yu - yl

    t_max_idx  = np.argmax(thickness)
    t_max      = float(np.max(thickness))
    t_max_x    = float(x[t_max_idx])
    c_max_idx  = np.argmax(np.abs(camber))
    c_max      = float(camber[c_max_idx])
    c_max_x    = float(x[c_max_idx])

    # área do perfil (trapézio composto)
    area = float(np.trapz(yu - yl, x))

    # raio de bordo de ataque (aproximação parabólica nos primeiros pontos)
    dy = yu[1] - yu[0]
    dx = x[1] - x[0]
    le_radius = float((dy / dx) ** 2 / 2) if dx > 0 else 0.0

    return {
        "t_max_pct":  t_max * 100,
        "t_max_x":    t_max_x,
        "c_max_pct":  c_max * 100,
        "c_max_x":    c_max_x,
        "area_adim":  area,
        "le_radius":  le_radius,
    }


def _plot_perfil(ax, nome: str, cor: str, label: str, chord_m: float = 1.0,
                 show_details: bool = True, alpha_fill: float = 0.15):
    """Plota perfil em eixo matplotlib."""
    x, yu, yl = gerar_coord_naca(nome)
    xc = x * chord_m; yuc = yu * chord_m; ylc = yl * chord_m
    camber = ((yu + yl) / 2.0) * chord_m

    ax.plot(xc, yuc, color=cor, linewidth=2.0, label=label)
    ax.plot(xc, ylc, color=cor, linewidth=2.0)
    ax.fill_between(xc, yuc, ylc, alpha=alpha_fill, color=cor)

    if show_details:
        ax.plot(xc, camber, color=cor, linewidth=0.8,
                linestyle="--", alpha=0.6, label=f"{label} — linha de curvatura")
        # ponto de máx. espessura
        idx = np.argmax(yu - yl)
        ax.axvline(x[idx] * chord_m, color=cor, linewidth=0.5,
                   linestyle=":", alpha=0.5)

    return xc, yuc, ylc


def _plot_wing(ax, forma: str, b: float, c: float, cor: str, label: str,
               alpha_fill: float = 0.18):
    """Plota silhueta da asa em eixo matplotlib (semi-envergadura)."""
    xs, ys = gerar_silhueta_asat(forma, b, c)
    ax.plot(xs, ys, color=cor, linewidth=2.0, label=label)
    ax.fill(xs, ys, alpha=alpha_fill, color=cor)
    # linha de 1/4 de corda
    x_qc = [0, b / 2]
    y_qc = [c * 0.25, c * 0.25] if forma == "Retangular" else [c * 0.25, c * 0.25]
    ax.plot(x_qc, y_qc, color=cor, linewidth=0.7, linestyle=":", alpha=0.5)


# ================================================================= #
# JANELA PRINCIPAL DO VISUALIZADOR                                   #
# ================================================================= #

def launch_geo_visualizer(parent_cfg: dict = None):
    """
    Lança o visualizador de geometrias como janela Toplevel independente.
    parent_cfg: dict opcional com chaves 'perfis_sel', 'c', 'b', 'asat_sel'
                para pré-preencher os controles.
    """
    db = _load_db()
    perfis_disponiveis = list(db.DATABASE.keys())
    asas_disponiveis   = list(db.AsaT.values())

    root = tk.Toplevel() if parent_cfg is not None else tk.Tk()
    root.title("Dark Wing Project — Visualizador de Geometrias")
    root.configure(bg=BG)
    root.resizable(True, True)

    # ── cabeçalho ─────────────────────────────────────────────────
    hdr = tk.Frame(root, bg=PANEL, pady=8)
    hdr.pack(fill="x")
    tk.Label(hdr, text="VISUALIZADOR DE GEOMETRIAS",
             bg=PANEL, fg=ACCENT, font=("Courier", 14, "bold")).pack()
    tk.Label(hdr, text="Dark Wing Project  ·  White §8.1  ·  NACA Theory of Wing Sections",
             bg=PANEL, fg=MUTED, font=("Courier", 8)).pack()

    # ── layout principal: painel esq + canvas dir ──────────────────
    main = tk.Frame(root, bg=BG)
    main.pack(fill="both", expand=True)

    # ── painel de controles ────────────────────────────────────────
    ctrl_outer = tk.Frame(main, bg=BG, width=260)
    ctrl_outer.pack(side="left", fill="y", padx=6, pady=6)
    ctrl_outer.pack_propagate(False)

    ctrl_canvas = tk.Canvas(ctrl_outer, bg=BG, highlightthickness=0, width=254)
    ctrl_sb     = tk.Scrollbar(ctrl_outer, orient="vertical", command=ctrl_canvas.yview)
    ctrl_canvas.configure(yscrollcommand=ctrl_sb.set)
    ctrl_sb.pack(side="right", fill="y")
    ctrl_canvas.pack(side="left", fill="both", expand=True)
    ctrl = tk.Frame(ctrl_canvas, bg=BG, padx=8)
    ctrl_canvas.create_window((0, 0), window=ctrl, anchor="nw")
    ctrl.bind("<Configure>", lambda e: ctrl_canvas.configure(
        scrollregion=ctrl_canvas.bbox("all")))

    def _sec(parent, title):
        f = tk.LabelFrame(parent, text=f" {title} ", bg=BG, fg=ACCENT,
                          font=("Courier", 8, "bold"), bd=1,
                          highlightbackground=BORDER, pady=5, padx=6)
        f.pack(fill="x", pady=4)
        return f

    def _lbl(parent, text, fg=MUTED):
        tk.Label(parent, text=text, bg=BG, fg=fg,
                 font=("Courier", 8)).pack(anchor="w")

    def _entry_row(parent, label, var, unit=""):
        f = tk.Frame(parent, bg=BG); f.pack(fill="x", pady=2)
        tk.Label(f, text=label, bg=BG, fg=MUTED,
                 font=("Courier", 8), width=14, anchor="w").pack(side="left")
        e = tk.Entry(f, textvariable=var, bg="#21262d", fg=TEXT,
                     insertbackground=TEXT, relief="flat", width=8,
                     font=("Courier", 9))
        e.pack(side="left", padx=2)
        tk.Label(f, text=unit, bg=BG, fg=MUTED,
                 font=("Courier", 8)).pack(side="left")
        return e

    # ── seleção de perfis ──────────────────────────────────────────
    s_perf = _sec(ctrl, "PERFIS  (1–3)")
    tk.Label(s_perf, text="Ctrl+clique para múltiplos", bg=BG, fg=MUTED,
             font=("Courier", 7)).pack(anchor="w")
    sb_lb = tk.Scrollbar(s_perf, orient="vertical", bg=PANEL)
    lb_perfis = tk.Listbox(s_perf, height=9, selectmode=tk.MULTIPLE,
                           bg="#21262d", fg=TEXT, font=("Courier", 8),
                           selectbackground=ACCENT, selectforeground=BG,
                           relief="flat", activestyle="none",
                           yscrollcommand=sb_lb.set, exportselection=False)
    sb_lb.config(command=lb_perfis.yview)
    sb_lb.pack(side="right", fill="y")
    lb_perfis.pack(fill="x")
    for p in perfis_disponiveis:
        lb_perfis.insert(tk.END, p)

    # pré-seleciona do parent_cfg
    if parent_cfg and parent_cfg.get("perfis_sel"):
        for ps in parent_cfg["perfis_sel"]:
            if ps in perfis_disponiveis:
                lb_perfis.selection_set(perfis_disponiveis.index(ps))
    else:
        lb_perfis.selection_set(0)

    # ── geometria da asa ───────────────────────────────────────────
    s_geo = _sec(ctrl, "GEOMETRIA DA ASA")

    c_var   = tk.StringVar(value=str(parent_cfg.get("c", 0.6)) if parent_cfg else "0.6")
    b_var   = tk.StringVar(value=str(parent_cfg.get("b", 3.0)) if parent_cfg else "3.0")
    ra_var  = tk.StringVar(value="8.0")
    s_var   = tk.StringVar(value="1.8")

    _entry_row(s_geo, "Corda c",     c_var,  "m")
    _entry_row(s_geo, "Enverg. b",   b_var,  "m")

    # RA + S derivados
    ra_frame = tk.Frame(s_geo, bg=BG); ra_frame.pack(fill="x", pady=2)
    tk.Label(ra_frame, text="RA alvo",  bg=BG, fg=MUTED,
             font=("Courier", 8), width=14, anchor="w").pack(side="left")
    tk.Entry(ra_frame, textvariable=ra_var, bg="#21262d", fg=TEXT,
             insertbackground=TEXT, relief="flat", width=8,
             font=("Courier", 9)).pack(side="left", padx=2)

    s_frame = tk.Frame(s_geo, bg=BG); s_frame.pack(fill="x", pady=2)
    tk.Label(s_frame, text="Área S",   bg=BG, fg=MUTED,
             font=("Courier", 8), width=14, anchor="w").pack(side="left")
    tk.Entry(s_frame, textvariable=s_var, bg="#21262d", fg=TEXT,
             insertbackground=TEXT, relief="flat", width=8,
             font=("Courier", 9)).pack(side="left", padx=2)
    tk.Label(s_frame, text="m²", bg=BG, fg=MUTED,
             font=("Courier", 8)).pack(side="left")

    geo_info_var = tk.StringVar(value="")
    tk.Label(s_geo, textvariable=geo_info_var, bg=BG, fg=GREEN,
             font=("Courier", 8), justify="left").pack(anchor="w", pady=2)

    def _sync_ra(*_):
        try:
            ra = float(ra_var.get()); sv = float(s_var.get())
            g  = geometria_de_ra_e_s(ra, sv)
            c_var.set(f"{g['c']:.4f}"); b_var.set(f"{g['b']:.4f}")
            geo_info_var.set(f"b={g['b']:.3f}m  c={g['c']:.3f}m  AR={g['AR']:.2f}")
        except Exception:
            geo_info_var.set("—")
    for _v in (ra_var, s_var):
        _v.trace_add("write", _sync_ra)

    # ── tipo de asa ────────────────────────────────────────────────
    s_asa = _sec(ctrl, "TIPO DE ASA")
    asat_var = tk.StringVar(value=parent_cfg.get("asat_sel", "Retangular") if parent_cfg else "Retangular")
    for asa in asas_disponiveis:
        tk.Radiobutton(s_asa, text=asa, variable=asat_var, value=asa,
                       bg=BG, fg=TEXT, selectcolor=PANEL,
                       activebackground=BG, activeforeground=ACCENT,
                       font=("Courier", 9)).pack(anchor="w")

    # ── opções de exibição ─────────────────────────────────────────
    s_opt = _sec(ctrl, "OPÇÕES DE EXIBIÇÃO")
    show_camber_var  = tk.BooleanVar(value=True)
    show_thick_var   = tk.BooleanVar(value=True)
    show_stats_var   = tk.BooleanVar(value=True)
    show_compare_var = tk.BooleanVar(value=False)
    show_3d_var      = tk.BooleanVar(value=False)
    normalize_var    = tk.BooleanVar(value=False)

    def _chk(parent, text, var):
        tk.Checkbutton(parent, text=text, variable=var,
                       bg=BG, fg=TEXT, selectcolor=PANEL,
                       activebackground=BG, activeforeground=ACCENT,
                       font=("Courier", 8)).pack(anchor="w")

    _chk(s_opt, "Linha de curvatura",      show_camber_var)
    _chk(s_opt, "Linhas de espessura",      show_thick_var)
    _chk(s_opt, "Painel de estatísticas",   show_stats_var)
    _chk(s_opt, "Comparação (overlay)",     show_compare_var)
    _chk(s_opt, "Vista pseudo-3D",          show_3d_var)
    _chk(s_opt, "Normalizar (c = 1 m)",     normalize_var)

    # ── corda real para escala ─────────────────────────────────────
    chord_display_var = tk.StringVar(value="")
    tk.Label(s_opt, textvariable=chord_display_var, bg=BG, fg=ACCENT,
             font=("Courier", 8), justify="left").pack(anchor="w", pady=2)

    # ── botões ─────────────────────────────────────────────────────
    def _btn(parent, text, cmd, bg=ACCENT, fg=BG):
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                      font=("Courier", 9, "bold"), relief="flat",
                      padx=8, pady=5, activebackground="#79c0ff",
                      activeforeground=BG, cursor="hand2")
        b.pack(fill="x", pady=3)
        return b

    s_act = _sec(ctrl, "AÇÕES")
    _btn(s_act, "  ATUALIZAR GRÁFICOS",  lambda: _render())
    _btn(s_act, "  EXPORTAR PNG",        lambda: _export(),   bg="#21262d", fg=TEXT)
    _btn(s_act, "  MÉTRICAS TXT",        lambda: _show_txt(), bg="#21262d", fg=TEXT)

    # ── canvas matplotlib ──────────────────────────────────────────
    plot_frame = tk.Frame(main, bg=BG)
    plot_frame.pack(side="left", fill="both", expand=True, padx=4, pady=6)

    fig = Figure(figsize=(10, 7.5), dpi=96, facecolor=BG)
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.get_tk_widget().pack(fill="both", expand=True)

    toolbar_frame = tk.Frame(plot_frame, bg=PANEL)
    toolbar_frame.pack(fill="x")
    toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
    toolbar.config(bg=PANEL)
    toolbar.update()

    # ── estado interno ─────────────────────────────────────────────
    _last_perfis = []

    # ── funções de renderização ────────────────────────────────────
    def _get_sel():
        idxs = lb_perfis.curselection()
        return [perfis_disponiveis[i] for i in idxs[:3]]

    def _safe_float(var, default):
        try:    return float(var.get())
        except: return default

    def _render(*_):
        nonlocal _last_perfis
        with plt.style.context(PLT_STYLE):
            fig.clear()
            perfis = _get_sel()
            if not perfis:
                ax = fig.add_subplot(111)
                ax.text(0.5, 0.5, "Selecione pelo menos 1 perfil",
                        ha="center", va="center", color=MUTED,
                        transform=ax.transAxes, fontsize=11)
                canvas.draw(); return

            _last_perfis = perfis
            c_real    = _safe_float(c_var,  0.6)
            b_real    = _safe_float(b_var,  3.0)
            chord_m   = 1.0 if normalize_var.get() else c_real
            asat      = asat_var.get()
            n         = len(perfis)

            chord_display_var.set(
                f"Escala: c={chord_m:.3f}m  b={b_real:.3f}m\n"
                f"AR={b_real/c_real:.2f}  S={b_real*c_real:.3f}m²" if not normalize_var.get()
                else "Normalizado: c = 1 m")

            # layout das subplots
            show_stats   = show_stats_var.get()
            show_3d      = show_3d_var.get()
            show_compare = show_compare_var.get()

            if show_stats and show_3d:
                gs = GridSpec(3, 2, figure=fig,
                              hspace=0.55, wspace=0.35,
                              top=0.92, bottom=0.06, left=0.07, right=0.97)
                ax_prof  = fig.add_subplot(gs[0, 0])
                ax_asa   = fig.add_subplot(gs[0, 1])
                ax_thick = fig.add_subplot(gs[1, 0])
                ax_camb  = fig.add_subplot(gs[1, 1])
                ax_stats = fig.add_subplot(gs[2, 0])
                ax_3d    = fig.add_subplot(gs[2, 1], projection="3d")
            elif show_stats:
                gs = GridSpec(2, 2, figure=fig,
                              hspace=0.5, wspace=0.35,
                              top=0.92, bottom=0.06, left=0.07, right=0.97)
                ax_prof  = fig.add_subplot(gs[0, :])
                ax_asa   = fig.add_subplot(gs[1, 0])
                ax_stats = fig.add_subplot(gs[1, 1])
                ax_thick = None; ax_camb = None; ax_3d = None
            elif show_3d:
                gs = GridSpec(2, 2, figure=fig,
                              hspace=0.5, wspace=0.35,
                              top=0.92, bottom=0.06, left=0.07, right=0.97)
                ax_prof  = fig.add_subplot(gs[0, :])
                ax_asa   = fig.add_subplot(gs[1, 0])
                ax_3d    = fig.add_subplot(gs[1, 1], projection="3d")
                ax_stats = None; ax_thick = None; ax_camb = None
            else:
                gs = GridSpec(1, 2, figure=fig,
                              hspace=0.3, wspace=0.35,
                              top=0.92, bottom=0.06, left=0.07, right=0.97)
                ax_prof  = fig.add_subplot(gs[0, 0])
                ax_asa   = fig.add_subplot(gs[0, 1])
                ax_stats = None; ax_thick = None; ax_camb = None; ax_3d = None

            for ax in [ax_prof, ax_asa] + [a for a in [ax_thick, ax_camb, ax_stats] if a]:
                ax.set_facecolor(PANEL)
                ax.tick_params(colors=MUTED, labelsize=8)
                ax.grid(True, color=BORDER, linewidth=0.5, alpha=0.7)
                for sp in ax.spines.values():
                    sp.set_edgecolor(BORDER)

            # ── perfil(s) ──────────────────────────────────────────
            for idx, perfil in enumerate(perfis):
                cor   = CORES_PLOT[idx]
                label = f"[{idx+1}] {perfil}" if n > 1 else perfil
                x, yu, yl = gerar_coord_naca(perfil)
                xc    = x * chord_m
                yuc   = yu * chord_m
                ylc   = yl * chord_m
                camber_c = ((yu + yl) / 2.0) * chord_m
                thick_c  = (yu - yl) * chord_m

                ax_prof.plot(xc, yuc, color=cor, linewidth=2.0, label=label)
                ax_prof.plot(xc, ylc, color=cor, linewidth=2.0)
                ax_prof.fill_between(xc, yuc, ylc, alpha=0.12, color=cor)

                if show_camber_var.get():
                    ax_prof.plot(xc, camber_c, color=cor, linewidth=0.9,
                                 linestyle="--", alpha=0.65)
                if show_thick_var.get():
                    idx_t = np.argmax(yu - yl)
                    ax_prof.axvline(xc[idx_t], color=cor, linewidth=0.6,
                                    linestyle=":", alpha=0.55)
                    ax_prof.annotate(
                        f"t={thick_c[idx_t]*1000:.1f}mm" if not normalize_var.get()
                        else f"t/c={float(yu[idx_t]-yl[idx_t]):.3f}",
                        xy=(xc[idx_t], yuc[idx_t]),
                        xytext=(xc[idx_t] + chord_m*0.03, yuc[idx_t] + chord_m*0.015),
                        color=cor, fontsize=7,
                        arrowprops=dict(arrowstyle="->", color=cor, lw=0.8))

                # ── espessura e curvatura ──────────────────────────
                if ax_thick:
                    ax_thick.plot(xc, thick_c, color=cor, linewidth=1.8,
                                  label=label if idx == 0 else "")
                if ax_camb:
                    ax_camb.plot(xc, camber_c, color=cor, linewidth=1.8,
                                 label=label if idx == 0 else "")

                # ── vista 3D pseudo ────────────────────────────────
                if ax_3d:
                    offsets = np.linspace(0, b_real * 0.5, 8)
                    for yoff in offsets:
                        alpha3 = 0.25 + 0.55 * (yoff / (b_real * 0.5))
                        ax_3d.plot(xc, [yoff] * len(xc), yuc,
                                   color=cor, linewidth=0.9, alpha=alpha3)
                        ax_3d.plot(xc, [yoff] * len(xc), ylc,
                                   color=cor, linewidth=0.9, alpha=alpha3)

            # formatação ax_prof
            ax_prof.set_title("Geometria do Perfil Aerodinâmico", color=TEXT,
                               fontsize=10, fontweight="bold", pad=8)
            ax_prof.set_xlabel(f"x {'(normalizado)' if normalize_var.get() else '[m]'}",
                               color=MUTED, fontsize=8)
            ax_prof.set_ylabel(f"y {'(normalizado)' if normalize_var.get() else '[m]'}",
                               color=MUTED, fontsize=8)
            ax_prof.set_aspect("equal")
            ax_prof.axhline(0, color=BORDER, linewidth=0.7, linestyle="-")
            ax_prof.legend(fontsize=8, facecolor=PANEL, edgecolor=BORDER,
                           labelcolor=TEXT, loc="upper right")

            if ax_thick:
                ax_thick.set_title("Distribuição de Espessura (t/c)",
                                   color=TEXT, fontsize=9)
                ax_thick.set_xlabel("x [m]" if not normalize_var.get() else "x",
                                    color=MUTED, fontsize=8)
                ax_thick.set_ylabel("Espessura", color=MUTED, fontsize=8)
            if ax_camb:
                ax_camb.set_title("Linha de Curvatura (y_c)",
                                  color=TEXT, fontsize=9)
                ax_camb.set_xlabel("x [m]" if not normalize_var.get() else "x",
                                   color=MUTED, fontsize=8)
                ax_camb.set_ylabel("Curvatura", color=MUTED, fontsize=8)
                ax_camb.axhline(0, color=BORDER, linewidth=0.5)

            # ── silhueta da asa ────────────────────────────────────
            ax_asa.set_facecolor(PANEL)
            ax_asa.set_aspect("equal")
            ax_asa.tick_params(colors=MUTED, labelsize=8)
            ax_asa.grid(True, color=BORDER, linewidth=0.5, alpha=0.7)
            for sp in ax_asa.spines.values():
                sp.set_edgecolor(BORDER)

            # silhueta principal
            cor0 = CORES_PLOT[0]
            xs, ys = gerar_silhueta_asat(asat, b_real, c_real)
            ax_asa.plot(xs, ys, color=cor0, linewidth=2.0, label=asat)
            ax_asa.fill(xs, ys, alpha=0.15, color=cor0)

            # anotações da asa
            ax_asa.axhline(c_real * 0.25, color=cor0, linewidth=0.7,
                           linestyle=":", alpha=0.5)
            ax_asa.axhline(c_real * 0.75, color=cor0, linewidth=0.7,
                           linestyle=":", alpha=0.4)
            ax_asa.annotate("c/4", xy=(b_real * 0.48, c_real * 0.25),
                            color=cor0, fontsize=7, alpha=0.7)
            ax_asa.annotate("3c/4", xy=(b_real * 0.48, c_real * 0.75),
                            color=cor0, fontsize=7, alpha=0.7)

            S    = b_real * c_real
            AR   = b_real ** 2 / S
            ax_asa.set_title(
                f"Silhueta da Asa — {asat}\n"
                f"b={b_real:.2f}m  c={c_real:.2f}m  AR={AR:.2f}  S={S:.3f}m²",
                color=TEXT, fontsize=9, fontweight="bold", pad=6)
            ax_asa.set_xlabel("Semi-envergadura y [m]", color=MUTED, fontsize=8)
            ax_asa.set_ylabel("Corda x [m]",            color=MUTED, fontsize=8)

            # ── painel de estatísticas ─────────────────────────────
            if ax_stats:
                ax_stats.axis("off")
                ax_stats.set_title("Métricas Geométricas", color=TEXT,
                                   fontsize=9, fontweight="bold", loc="left")

                rows  = []
                colunas = ["Métrica"]
                for p in perfis:
                    colunas.append(p[:18])

                metricas_labels = [
                    ("t/c máx  [%]",  "t_max_pct",  "{:.2f}"),
                    ("x(t_max) [c]",  "t_max_x",    "{:.3f}"),
                    ("Camber máx [%]","c_max_pct",   "{:.2f}"),
                    ("x(camber) [c]", "c_max_x",     "{:.3f}"),
                    ("Área (adim.)",   "area_adim",  "{:.4f}"),
                ]
                # linha extra: valores reais se não normalizado
                if not normalize_var.get():
                    metricas_labels += [
                        ("t_max [mm]",    "_t_max_mm",  "{:.1f}"),
                        ("Área real [m²]","_area_real", "{:.5f}"),
                    ]

                all_m = []
                for p in perfis:
                    m = _metricas_perfil(p)
                    m["_t_max_mm"]   = m["t_max_pct"] / 100.0 * c_real * 1000
                    m["_area_real"]  = m["area_adim"] * c_real ** 2
                    all_m.append(m)

                for lbl, key, fmt in metricas_labels:
                    row = [lbl]
                    for m in all_m:
                        row.append(fmt.format(m.get(key, 0)))
                    rows.append(row)

                tbl = ax_stats.table(
                    cellText   = rows,
                    colLabels  = colunas,
                    cellLoc    = "center",
                    loc        = "center",
                    bbox       = [0, 0, 1, 1],
                )
                tbl.auto_set_font_size(False)
                tbl.set_fontsize(8)

                for (r, c_), cell in tbl.get_celld().items():
                    cell.set_facecolor(PANEL if r > 0 else "#21262d")
                    cell.set_edgecolor(BORDER)
                    cell.set_text_props(
                        color=TEXT if r > 0 else ACCENT,
                        fontname="monospace",
                        fontweight="bold" if r == 0 or c_ == 0 else "normal")

            # ── vista 3D ───────────────────────────────────────────
            if ax_3d:
                ax_3d.set_facecolor(PANEL)
                ax_3d.set_xlabel("x [m]", color=MUTED, fontsize=7)
                ax_3d.set_ylabel("y span [m]", color=MUTED, fontsize=7)
                ax_3d.set_zlabel("z [m]", color=MUTED, fontsize=7)
                ax_3d.set_title("Vista 3D (semi-asa)", color=TEXT,
                                fontsize=9, pad=4)
                ax_3d.tick_params(colors=MUTED, labelsize=6)
                ax_3d.xaxis.pane.fill = False
                ax_3d.yaxis.pane.fill = False
                ax_3d.zaxis.pane.fill = False
                ax_3d.xaxis.pane.set_edgecolor(BORDER)
                ax_3d.yaxis.pane.set_edgecolor(BORDER)
                ax_3d.zaxis.pane.set_edgecolor(BORDER)

            fig.suptitle("Dark Wing Project  ·  Visualizador de Geometrias  ·  White §8.1",
                         color=MUTED, fontsize=8, y=0.99)
            canvas.draw()

    # ── exportar PNG ───────────────────────────────────────────────
    def _export():
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("SVG", "*.svg")],
            initialfile="geometria_perfil.png")
        if path:
            fig.savefig(path, dpi=180, bbox_inches="tight",
                        facecolor=BG)
            tk.messagebox.showinfo("Exportado", f"Salvo em:\n{path}")

    # ── painel de texto com métricas ───────────────────────────────
    def _show_txt():
        perfis = _get_sel()
        if not perfis:
            return
        c_real = _safe_float(c_var, 0.6)
        b_real = _safe_float(b_var, 3.0)
        lines  = [
            "=" * 60,
            "  Dark Wing Project — MÉTRICAS GEOMÉTRICAS",
            "=" * 60,
            f"  Corda c = {c_real:.4f} m   |   Envergadura b = {b_real:.4f} m",
            f"  AR = {b_real**2/(b_real*c_real):.2f}   |   S = {b_real*c_real:.4f} m²",
            f"  AsaT: {asat_var.get()}",
            "",
        ]
        for perfil in perfis:
            m = _metricas_perfil(perfil)
            lines += [
                f"  ─── {perfil} ───",
                f"    Espessura máx. (t/c):  {m['t_max_pct']:.2f}%  @ x/c = {m['t_max_x']:.3f}",
                f"    Espessura real (t):    {m['t_max_pct']/100*c_real*1000:.2f} mm",
                f"    Curvatura máx.:        {m['c_max_pct']:.2f}%  @ x/c = {m['c_max_x']:.3f}",
                f"    Área adimensional:     {m['area_adim']:.5f} c²",
                f"    Área real:             {m['area_adim']*c_real**2*1e4:.2f} cm²",
                "",
            ]
        lines.append("=" * 60)
        txt = "\n".join(lines)

        win = tk.Toplevel(root)
        win.title("Métricas Geométricas")
        win.configure(bg=BG)
        st = tk.Text(win, bg=PANEL, fg=TEXT, font=("Courier", 9),
                     relief="flat", padx=12, pady=8)
        st.insert("1.0", txt)
        st.config(state="disabled")
        st.pack(fill="both", expand=True, padx=8, pady=8)
        tk.Button(win, text="Copiar", bg="#21262d", fg=TEXT,
                  font=("Courier", 9), relief="flat",
                  command=lambda: (win.clipboard_clear(),
                                   win.clipboard_append(txt))).pack(pady=4)

    # ── atalhos de teclado ─────────────────────────────────────────
    root.bind("<Return>", lambda e: _render())
    root.bind("<F5>",     lambda e: _render())

    # ── atualização automática ao mudar controles ──────────────────
    for v in (c_var, b_var, asat_var, show_camber_var, show_thick_var,
              show_stats_var, show_compare_var, show_3d_var, normalize_var):
        try:
            v.trace_add("write", lambda *_: _render())
        except Exception:
            pass
    lb_perfis.bind("<<ListboxSelect>>", lambda e: root.after(80, _render))

    # ── render inicial ─────────────────────────────────────────────
    root.after(200, _render)

    # dimensões iniciais
    root.update_idletasks()
    w, h = 1300, 760
    sw = root.winfo_screenwidth(); sh = root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{max(0,(sw-w)//2)}+{max(0,(sh-h)//2)}")

    if isinstance(root, tk.Tk):
        root.mainloop()
    return root


# ================================================================= #
# PONTO DE ENTRADA DIRETO                                            #
# ================================================================= #
if __name__ == "__main__":
    launch_geo_visualizer()
