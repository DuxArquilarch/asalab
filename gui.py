# ================================================================= #
# AsalabXYZ — GUI AUTÔNOMA v2.2  (aba Temperatura)                  #
#                                                                    #
# GUI completamente separada do database.py:                        #
#   • Recarrega database.py automaticamente ao detectar mudanças    #
#   • Nenhuma edição manual necessária ao adicionar aerofólios      #
#   • Compatível com qualquer database.py que exporte:             #
#       DATABASE, AsaT, MATERIAIS, CL_MAX_2D, CD0_PERFIL           #
#                                                                    #
# Uso:  python gui.py                                               #
#       (database.py deve estar na mesma pasta)                     #
# ================================================================= #

import tkinter as tk
from tkinter import ttk, messagebox
import importlib
import importlib.util
import sys
import os
import time
import threading

# ─────────────────────────────────────────────────────────────────
# LOADER DINÂMICO DE DATABASE
# Recarrega database.py sempre que o arquivo for modificado
# ─────────────────────────────────────────────────────────────────

DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.py")

def _load_database():
    """Carrega (ou recarrega) database.py e devolve o módulo."""
    spec = importlib.util.spec_from_file_location("database", DATABASE_PATH)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules["database"] = mod   # disponibiliza para outros imports
    return mod

def get_db():
    """Retorna o módulo database atualizado."""
    return sys.modules.get("database") or _load_database()

# Carrega na inicialização
_load_database()


# ─────────────────────────────────────────────────────────────────
# PALETA DARK
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
# WATCHER DE ARQUIVO — thread que detecta mudanças em database.py
# ─────────────────────────────────────────────────────────────────

class DatabaseWatcher:
    """
    Monitora database.py em background.
    Quando detecta modificação, chama callback(novo_mtime).
    """
    def __init__(self, path, callback, interval=1.5):
        self.path      = path
        self.callback  = callback
        self.interval  = interval
        self._last_mtime = self._mtime()
        self._stop     = threading.Event()
        self._thread   = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _mtime(self):
        try:
            return os.path.getmtime(self.path)
        except OSError:
            return 0

    def _run(self):
        while not self._stop.wait(self.interval):
            mt = self._mtime()
            if mt != self._last_mtime:
                self._last_mtime = mt
                try:
                    _load_database()
                    self.callback(mt)
                except Exception as e:
                    print(f"[Watcher] Erro ao recarregar database: {e}")

    def stop(self):
        self._stop.set()


# ─────────────────────────────────────────────────────────────────
# JANELA PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def launch_asalab_gui():
    """
    Recarrega o database automaticamente ao detectar mudanças.
    Retorna dict com todos os parâmetros, ou None se cancelado.
    """
    root = tk.Tk()
    root.title("AsalabXYZ V2")
    root.configure(bg=BG)
    root.resizable(True, True)

    result = {"cancelled": True}

    # ── Cabeçalho ──────────────────────────────────────────────
    hdr = tk.Frame(root, bg=PANEL, pady=10)
    hdr.pack(fill="x")
    tk.Label(hdr, text="ASALAB XYZ V2", bg=PANEL, fg=ACCENT,
             font=("Courier", 18, "bold")).pack()
    tk.Label(hdr, text="White §8 · Sadraey 2013 · Raymer 2012",
             bg=PANEL, fg=MUTED, font=("Courier", 8)).pack()

    # Indicador de reload
    reload_var = tk.StringVar(value=f"database.py  ·  {len(get_db().DATABASE)} aerofólios  ·  {len(get_db().MATERIAIS)} materiais")
    reload_lbl = tk.Label(hdr, textvariable=reload_var, bg=PANEL, fg=GREEN,
                          font=("Courier", 8))
    reload_lbl.pack()

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

    canvas1 = tk.Canvas(tab1, bg=BG, highlightthickness=0)
    sb1 = tk.Scrollbar(tab1, orient="vertical", command=canvas1.yview)
    canvas1.configure(yscrollcommand=sb1.set)
    sb1.pack(side="right", fill="y")
    canvas1.pack(side="left", fill="both", expand=True)
    inner1 = tk.Frame(canvas1, bg=BG, padx=14)
    canvas1.create_window((0, 0), window=inner1, anchor="nw")
    inner1.bind("<Configure>", lambda e: canvas1.configure(
        scrollregion=canvas1.bbox("all")))

    # Variáveis de voo
    v_var    = tk.DoubleVar(value=15.0)
    c_var    = tk.DoubleVar(value=0.60)
    b_var    = tk.DoubleVar(value=3.0)
    peso_var = tk.DoubleVar(value=5.0)

    s_voo = _section(inner1, "PARÂMETROS DE VOO")
    _scale(s_voo, v_var,    from_=3,   to=80,  label="Velocidade (m/s)",  resolution=0.5)
    _scale(s_voo, c_var,    from_=0.1, to=2.0, label="Corda c (m)",       resolution=0.05)
    _scale(s_voo, b_var,    from_=0.3, to=12,  label="Envergadura b (m)", resolution=0.1)
    _scale(s_voo, peso_var, from_=0.1, to=50,  label="Peso total (kg)",   resolution=0.1)

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
    for k, v in get_db().AsaT.items():
        descr = {"Retangular": "e_Oswald        | κ=1.00",
                 "Elíptica":   "e=1.00          | κ=1.00",
                 "Delta":      "e empírico      | κ=0.90"}.get(v, "")
        f = tk.Frame(s_asat, bg=PANEL); f.pack(fill="x", pady=1)
        _radio(f, f"[{k}] {v:<14} — {descr}", asat_var, v).pack(side="left")

    # ── Lista dinâmica de aerofólios ────────────────────────────
    s_perf = _section(inner1, "AEROFÓLIOS (selecione 1 a 3)")

    # Container que será reconstruído no reload
    perf_container = tk.Frame(s_perf, bg=PANEL)
    perf_container.pack(fill="x")

    lb_perfis_ref = [None]   # referência mutável para o listbox

    def _build_perfis_list(container):
        """Constrói (ou reconstrói) o listbox de aerofólios."""
        for w in container.winfo_children():
            w.destroy()

        db    = get_db()
        lista = list(db.DATABASE.keys())
        descs = []
        for p in lista:
            fam = ("5-dígitos" if any(d in p for d in ["23012","23015"])
                   else "6-dígitos" if any(d in p for d in ["63-","65-"])
                   else "MH" if p.startswith("MH ")
                   else "4-dígitos")
            clm = db.CL_MAX_2D.get(p, "—")
            cd0 = db.CD0_PERFIL.get(p, "—")
            clm_s = f"{clm:.3f}" if isinstance(clm, float) else str(clm)
            cd0_s = f"{cd0:.5f}" if isinstance(cd0, float) else str(cd0)
            descs.append(f"{p:<30}  CLmax={clm_s}  CD0={cd0_s}  [{fam}]")

        lb = _listbox(container, descs,
                      height=min(max(len(lista), 4), 16),
                      selectmode=tk.MULTIPLE)
        lb.selection_set(0)
        lb_perfis_ref[0] = lb
        tk.Label(container, text="Ctrl+clique para múltipla seleção (máx. 3)",
                 bg=PANEL, fg=MUTED, font=("Courier", 7)).pack()
        return lista

    perfis_lista_ref = [_build_perfis_list(perf_container)]

    # ════════════════════════════════════════════════════════════
    # ABA 2 — TEMPERATURA  (substitui antiga aba Materiais)
    # ════════════════════════════════════════════════════════════
    tab2 = tk.Frame(nb, bg=BG)
    nb.add(tab2, text="  🌡 TEMPERATURA  ")

    canvas2 = tk.Canvas(tab2, bg=BG, highlightthickness=0)
    sb2 = tk.Scrollbar(tab2, orient="vertical", command=canvas2.yview)
    canvas2.configure(yscrollcommand=sb2.set)
    sb2.pack(side="right", fill="y")
    canvas2.pack(side="left", fill="both", expand=True)
    inner2 = tk.Frame(canvas2, bg=BG, padx=14)
    canvas2.create_window((0, 0), window=inner2, anchor="nw")
    inner2.bind("<Configure>", lambda e: canvas2.configure(
        scrollregion=canvas2.bbox("all")))

    ativar_mt_var = tk.BooleanVar(value=False)
    s_mt_toggle = _section(inner2, "ANÁLISE MULTI-TEMPERATURA")
    _checkbtn(s_mt_toggle, "Ativar análise multi-temperatura (Lei de Sutherland)", ativar_mt_var).pack(anchor="w")
    tk.Label(s_mt_toggle, text="  Varia ρ, μ e velocidade do som com a temperatura ambiente.\n"
             "  Base: μ = μ₀·(T/T₀)^(3/2)·(T₀+S)/(T+S)   —   White §1.7",
             bg=PANEL, fg=MUTED, font=("Courier", 8), justify="left").pack(anchor="w")

    s_temp = _section(inner2, "FAIXA DE TEMPERATURA")
    tmin_var = tk.DoubleVar(value=15.0)
    tmax_var = tk.DoubleVar(value=30.0)
    tstep_var = tk.DoubleVar(value=1.0)
    _scale(s_temp, tmin_var, from_=15, to=30, label="T mínima (°C)", resolution=1.0)
    _scale(s_temp, tmax_var, from_=15, to=30, label="T máxima (°C)", resolution=1.0)

    # Garante clamp mesmo que o valor seja forçado por código ou teclado
    def _clamp_tmin(*_):
        v = tmin_var.get()
        if v < 15: tmin_var.set(15)
        elif v > 30: tmin_var.set(30)
    def _clamp_tmax(*_):
        v = tmax_var.get()
        if v < 15: tmax_var.set(15)
        elif v > 30: tmax_var.set(30)
    tmin_var.trace_add("write", _clamp_tmin)
    tmax_var.trace_add("write", _clamp_tmax)
    _scale(s_temp, tstep_var, from_=0.5, to=5.0, label="Passo ΔT (°C)", resolution=0.5)

    s_temp_info = _section(inner2, "INFO")
    tk.Label(s_temp_info, text="  Os perfis analisados serão os selecionados na aba ✈ VOO.\n"
             "  Saída: tabela comparativa + gráficos CL·CD·L/D por temperatura.",
             bg=PANEL, fg=MUTED, font=("Courier", 8), justify="left").pack(anchor="w")

    # ════════════════════════════════════════════════════════════
    # ABA 3 — GRÁFICOS
    # ════════════════════════════════════════════════════════════
    tab3 = tk.Frame(nb, bg=BG)
    nb.add(tab3, text="  📊 GRÁFICOS  ")

    inner3 = tk.Frame(tab3, bg=BG, padx=14)
    inner3.pack(fill="both", expand=True, pady=6)

    s_graf = _section(inner3, "GRÁFICOS AERODINÂMICOS (Figura 1 — sempre gerada)")
    tk.Label(s_graf, text="  CL · CD · L/D · Cm · XCp · Silhueta da asa\n"
             "  Layout 2×3 — White §8.1, §8.3, §8.4, §8.7",
             bg=PANEL, fg=MUTED, font=("Courier", 9), justify="left").pack(anchor="w", pady=4)

    s_graf2 = _section(inner3, "GRÁFICOS MULTI-TEMPERATURA (Figura 2 — requer aba 🌡 ativa)")
    show_mt_graf_var = tk.BooleanVar(value=True)
    _checkbtn(s_graf2,
              "Gerar gráficos de variação térmica (Lei de Sutherland)",
              show_mt_graf_var).pack(anchor="w")

    tk.Label(s_graf2,
             text=(
                 "  Inclui: CL·CD·L/D vs α para cada temperatura  |  "
                 "α_stall, (L/D)_max, Re e CL_req vs T"
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
        tmin = tmin_var.get(); tmax = tmax_var.get(); tstep = tstep_var.get()
        if ativar_mt_var.get():
            mt_str = f"Multi-Temp: {tmin:.0f}–{tmax:.0f}°C (Δ{tstep:.1f})"
        else:
            mt_str = "Multi-Temp: desativado"
        resumo_var.set(
            f"V={v} m/s  c={c} m  b={b} m  W={pe} kg\n"
            f"S={s:.3f} m²  AR={ar:.2f}  Re={re:.0f}\n"
            f"Asa: {asat_var.get()}  |  {mt_str}"
        )
    for var in (v_var, c_var, b_var, peso_var, tmin_var, tmax_var, tstep_var):
        var.trace_add("write", _upd_resumo)
    ativar_mt_var.trace_add("write", _upd_resumo)
    asat_var.trace_add("write", _upd_resumo)
    _upd_resumo()
    tk.Label(inner3, textvariable=resumo_var, bg=PANEL, fg=ACCENT,
             font=("Courier", 9), relief="flat", padx=10, pady=8,
             justify="left").pack(fill="x", pady=4)

    # ════════════════════════════════════════════════════════════
    # CALLBACK DE RELOAD — chamado pelo DatabaseWatcher
    # ════════════════════════════════════════════════════════════
    def _on_database_changed(mtime):
        """Redesenha as listas de aerofólios com os dados novos."""
        def _update():
            db = get_db()
            # Atualiza indicador no cabeçalho
            reload_var.set(
                f"⟳  database.py recarregado  ·  "
                f"{len(db.DATABASE)} aerofólios  ·  "
                f"{len(db.MATERIAIS)} materiais"
            )
            reload_lbl.configure(fg=YELLOW)
            root.after(3000, lambda: (
                reload_var.set(f"database.py  ·  {len(db.DATABASE)} aerofólios  ·  {len(db.MATERIAIS)} materiais"),
                reload_lbl.configure(fg=GREEN)
            ))

            # Recria listas
            perfis_lista_ref[0] = _build_perfis_list(perf_container)

            # Forçar redraw do canvas
            inner1.update_idletasks()
            canvas1.configure(scrollregion=canvas1.bbox("all"))
            inner2.update_idletasks()
            canvas2.configure(scrollregion=canvas2.bbox("all"))

        root.after(0, _update)   # chama na thread principal do Tk

    # Inicia watcher
    watcher = DatabaseWatcher(DATABASE_PATH, _on_database_changed)

    # ════════════════════════════════════════════════════════════
    # BARRA INFERIOR — BOTÕES
    # ════════════════════════════════════════════════════════════
    bar = tk.Frame(root, bg=PANEL, pady=10, padx=12)
    bar.pack(fill="x")

    status_var = tk.StringVar(value="Pronto.")
    tk.Label(bar, textvariable=status_var, bg=PANEL, fg=MUTED,
             font=("Courier", 8)).pack(side="left", padx=8)

    def _cancel():
        watcher.stop()
        result["cancelled"] = True
        root.destroy()

    def _run():
        sel_perf_idx = lb_perfis_ref[0].curselection() if lb_perfis_ref[0] else ()
        if not sel_perf_idx:
            messagebox.showerror("AsaLab", "Selecione pelo menos 1 aerofólio.")
            return
        if len(sel_perf_idx) > 3:
            messagebox.showerror("AsaLab", "Selecione no máximo 3 aerofólios.")
            return

        lista_atual = perfis_lista_ref[0]
        perfis_sel  = [lista_atual[i] for i in sel_perf_idx]

        cfg_multi_temp = None
        if ativar_mt_var.get():
            cfg_multi_temp = {
                "ativar":   True,
                "t_min":    tmin_var.get(),
                "t_max":    tmax_var.get(),
                "t_step":   tstep_var.get(),
                "perfis_sel": perfis_sel,
            }

        result.update({
            "cancelled":      False,
            "v":              v_var.get(),
            "c":              c_var.get(),
            "b":              b_var.get(),
            "peso_kg":        peso_var.get(),
            "perfis_sel":     perfis_sel,
            "asat_sel":       asat_var.get(),
            "cfg_multi_temp": cfg_multi_temp,
        })
        status_var.set("Calculando…")
        watcher.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _cancel)
    _btn(bar, "CANCELAR", _cancel, bg="#30363d", fg=TEXT).pack(side="right", padx=6)
    _btn(bar, " ✈  EXECUTAR SIMULAÇÃO ", _run, bg=ACCENT, fg=BG).pack(side="right", padx=6)

    # Centralizar janela
    root.update_idletasks()
    w, h = 800, 720
    sw = root.winfo_screenwidth(); sh = root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    root.mainloop()
    return result


# ─────────────────────────────────────────────────────────────────
# PONTO DE ENTRADA
# ─────────────────────────────────────────────────────────────────
def main():
    cfg = launch_asalab_gui()
    if cfg["cancelled"]:
        print("Simulação cancelada.")
        return

    print("\n" + "═"*65)
    print("  ASALAB GOLDEN EAGLE")
    print("═"*65)
    print(f"  V={cfg['v']} m/s | c={cfg['c']} m | b={cfg['b']} m | W={cfg['peso_kg']} kg")
    print(f"  Perfis: {', '.join(cfg['perfis_sel'])}")
    print(f"  Asa: {cfg['asat_sel']}")
    if cfg.get("cfg_multi_temp"):
        mt = cfg["cfg_multi_temp"]
        print(f"  Multi-Temp: {mt['t_min']:.0f}–{mt['t_max']:.0f} °C  "
              f"passo={mt['t_step']:.1f} °C")
    print("═"*65 + "\n")

    from calculos import calcular_asa
    from analise_graficos import plotar_resultados

    dados = calcular_asa(
        cfg["v"], cfg["c"], cfg["b"], cfg["peso_kg"],
        cfg["perfis_sel"], cfg["asat_sel"]
    )
    plotar_resultados(dados, None)

    if cfg.get("cfg_multi_temp") and cfg["cfg_multi_temp"]["ativar"]:
        from calculos import calcular_asa_multi_temp
        from analise_multi_temp import plotar_multi_temp
        mt = cfg["cfg_multi_temp"]
        print("\n  [Multi-Temp] Calculando variação térmica...")
        res_mt = calcular_asa_multi_temp(
            cfg["v"], cfg["c"], cfg["b"], cfg["peso_kg"],
            mt["perfis_sel"], cfg["asat_sel"],
            temp_min=mt["t_min"], temp_max=mt["t_max"], temp_step=mt["t_step"])
        plotar_multi_temp(res_mt, cfg)


if __name__ == "__main__":
    main()
