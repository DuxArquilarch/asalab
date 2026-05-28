# ================================================================= #
# Dark Wing Project — GUI AUTÔNOMA v2.2                              #
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

def launch_darkwing_gui():
    """
    Recarrega o database automaticamente ao detectar mudanças.
    Retorna dict com todos os parâmetros, ou None se cancelado.
    """
    root = tk.Tk()
    root.title("Dark Wing Project V2")
    root.configure(bg=BG)
    root.resizable(True, True)

    result = {"cancelled": True}

    # ── Cabeçalho ──────────────────────────────────────────────
    hdr = tk.Frame(root, bg=PANEL, pady=10)
    hdr.pack(fill="x")
    tk.Label(hdr, text="DARK WING PROJECT V2", bg=PANEL, fg=ACCENT,
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
    c_var    = tk.StringVar(value="0.60")   # Entry de texto livre
    b_var    = tk.StringVar(value="3.0")    # Entry de texto livre
    peso_var = tk.DoubleVar(value=5.0)

    s_voo = _section(inner1, "PARÂMETROS DE VOO")
    _scale(s_voo, v_var,    from_=3,   to=80,  label="Velocidade (m/s)",  resolution=0.5)

    # ── Corda e Envergadura: entrada de texto livre ─────────────
    def _entry_row(parent, label_txt, var, unit="m", min_val=0.01, max_val=99.0):
        """Cria uma linha label + Entry + unidade com validação on-focus-out."""
        f = tk.Frame(parent, bg=PANEL)
        f.pack(fill="x", pady=3)
        tk.Label(f, text=label_txt, bg=PANEL, fg=MUTED,
                 font=("Courier", 8), width=26, anchor="w").pack(side="left")
        ent = _entry(f, var, width=12)
        ent.pack(side="left", padx=4)
        tk.Label(f, text=unit, bg=PANEL, fg=MUTED,
                 font=("Courier", 8)).pack(side="left")

        # Feedback visual de erro
        err_lbl = tk.Label(f, text="", bg=PANEL, fg=RED,
                           font=("Courier", 8))
        err_lbl.pack(side="left", padx=6)

        def _validate(*_):
            try:
                val = float(var.get())
                if val < min_val or val > max_val:
                    raise ValueError
                err_lbl.config(text="")
                ent.config(bg="#21262d")
            except (ValueError, tk.TclError):
                err_lbl.config(text=f"✗  [{min_val}–{max_val}]")
                ent.config(bg="#3d1a1a")

        ent.bind("<FocusOut>", _validate)
        ent.bind("<Return>",   _validate)
        return ent

    _ent_c = _entry_row(s_voo, "Corda c (m)",       c_var,    unit="m", min_val=0.01, max_val=20.0)
    _ent_b = _entry_row(s_voo, "Envergadura b (m)", b_var,    unit="m", min_val=0.01, max_val=60.0)
    # GEO lock will populate this list after the tab is built
    _geo_entries_ref = []   # placeholder; GEO tab appends to this after creation
    _scale(s_voo, peso_var, from_=0.1, to=50,  label="Peso total (kg)",   resolution=0.1)

    # ── Altitude e Temperatura (cálculo automático de ρ) ───────
    alt_var = tk.StringVar(value="0")
    _entry_row(s_voo, "Altitude h (m)", alt_var, unit="m", min_val=0, max_val=5000.0)

    temp_voo_var = tk.StringVar(value="15.0")
    _entry_row(s_voo, "Temperatura T (°C)", temp_voo_var, unit="°C", min_val=-50.0, max_val=50.0)

    # Frame para exibir ρ calculado
    rho_display_var = tk.StringVar(value="ρ = 1.225 kg/m³  |  ISA SL")
    tk.Label(s_voo, textvariable=rho_display_var, bg=PANEL, fg=GREEN,
             font=("Courier", 9, "bold")).pack(pady=4)

    ar_lbl_var = tk.StringVar()
    def _safe(var, fallback=0.0):
        try:    return float(var.get())
        except: return fallback

    def _upd_ar(*_):
        b = _safe(b_var); c = _safe(c_var)
        ar = b**2 / (b * c) if c > 0 and b > 0 else 0
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

    def _bind_lb_vs(*_):
        lb = lb_perfis_ref[0]
        if lb:
            lb.bind("<<ListboxSelect>>", _calc_vs)

    # ════════════════════════════════════════════════════════════
    # ABA 2 — SADRAEY + LLT  (substitui antiga aba Temperatura)
    # ════════════════════════════════════════════════════════════
    tab2 = tk.Frame(nb, bg=BG)
    nb.add(tab2, text="  📐 SADRAEY  ")

    canvas2 = tk.Canvas(tab2, bg=BG, highlightthickness=0)
    sb2 = tk.Scrollbar(tab2, orient="vertical", command=canvas2.yview)
    canvas2.configure(yscrollcommand=sb2.set)
    sb2.pack(side="right", fill="y")
    canvas2.pack(side="left", fill="both", expand=True)
    inner2 = tk.Frame(canvas2, bg=BG, padx=14)
    canvas2.create_window((0, 0), window=inner2, anchor="nw")
    inner2.bind("<Configure>", lambda e: canvas2.configure(
        scrollregion=canvas2.bbox("all")))

    ativar_sad_var = tk.BooleanVar(value=False)
    s_sad_toggle = _section(inner2, "ANÁLISE SADRAEY + LLT")
    _checkbtn(s_sad_toggle, "Ativar análise conceitual Sadraey (2013) + LLT", ativar_sad_var).pack(anchor="w")
    tk.Label(s_sad_toggle, text="  Dimensionamento de asa via coeficientes alvo + Teoria da Linha Sustentadora.\n"
             "  Inclui: varredura de geometrias, altitude, polar e performance.",
             bg=PANEL, fg=MUTED, font=("Courier", 8), justify="left").pack(anchor="w")

    s_sad_param = _section(inner2, "PARÂMETROS DE MISSÃO")
    vs_var = tk.DoubleVar(value=7.5)
    vc_var = tk.DoubleVar(value=12.0)

    # Vs display (read-only, calculated)
    vs_frame = tk.Frame(s_sad_param, bg=PANEL)
    vs_frame.pack(fill="x", pady=2)
    tk.Label(vs_frame, text="Vel. estol Vs (m/s)", bg=PANEL, fg=MUTED,
             font=("Courier", 8), width=26, anchor="w").pack(side="left")
    vs_display_var = tk.StringVar(value="—")
    tk.Label(vs_frame, textvariable=vs_display_var, bg=PANEL, fg=GREEN,
             font=("Courier", 10, "bold"), width=10).pack(side="left")
    tk.Label(vs_frame, text="(calculado: √(2W/ρSCLmax))", bg=PANEL, fg=MUTED,
             font=("Courier", 8)).pack(side="left", padx=6)

    def _calc_vs(*_):
        """Recalculates Vs from current flight params and selected airfoil CLmax."""
        try:
            from aerodynamic_report import calcular_atmosfera_isa
            from database import CL_MAX_2D
            peso = peso_var.get()
            b = _safe(b_var); c = _safe(c_var)
            s = b * c
            if s <= 0:
                vs_display_var.set("—")
                return
            alt = _safe(alt_var, 0); temp = _safe(temp_voo_var, 15.0)
            atm = calcular_atmosfera_isa(alt, temp)
            rho = atm["rho"]
            # Get CLmax from first selected airfoil, or use default 1.5
            sel_idx = lb_perfis_ref[0].curselection() if lb_perfis_ref[0] else ()
            lista = perfis_lista_ref[0]
            if sel_idx and lista:
                perfil_nome = lista[sel_idx[0]]
                cl_max = CL_MAX_2D.get(perfil_nome, 1.5)
            else:
                cl_max = 1.5
            vs_calc = (2.0 * peso * 9.81 / (rho * s * cl_max)) ** 0.5
            vs_var.set(round(vs_calc, 2))
            vs_display_var.set(f"{vs_calc:.2f} m/s")
        except Exception:
            vs_display_var.set("—")

    for _v in (peso_var, b_var, c_var, alt_var, temp_voo_var):
        _v.trace_add("write", _calc_vs)

    root.after(100, _bind_lb_vs)
    root.after(200, _calc_vs)

    _scale(s_sad_param, vc_var, from_=5, to=40, label="Vel. cruzeiro Vc (m/s)", resolution=0.5)

    s_sad_info = _section(inner2, "INFO")
    tk.Label(s_sad_info, text="  Os perfis analisados serão os selecionados na aba ✈ VOO.\n"
             "  Saída: relatório texto + gráficos interativos (Plotly).",
             bg=PANEL, fg=MUTED, font=("Courier", 8), justify="left").pack(anchor="w")
    # ════════════════════════════════════════════════════════════
    # ABA — GEOMETRIA VIA AERODYNAMIC_REPORT
    # ════════════════════════════════════════════════════════════
    tab_geo_ra = tk.Frame(nb, bg=BG)
    nb.add(tab_geo_ra, text="  📐 GEO (RA)  ")

    canvas_geo = tk.Canvas(tab_geo_ra, bg=BG, highlightthickness=0)
    sb_geo = tk.Scrollbar(tab_geo_ra, orient="vertical", command=canvas_geo.yview)
    canvas_geo.configure(yscrollcommand=sb_geo.set)
    sb_geo.pack(side="right", fill="y")
    canvas_geo.pack(side="left", fill="both", expand=True)
    
    inner_geo = tk.Frame(canvas_geo, bg=BG, padx=14)
    canvas_geo.create_window((0, 0), window=inner_geo, anchor="nw")
    inner_geo.bind("<Configure>", lambda e: canvas_geo.configure(
        scrollregion=canvas_geo.bbox("all")))

    # Controle para ativar o cálculo/varredura geométrica do relatório
    ativar_geo_report_var = tk.BooleanVar(value=False)
    s_geo_toggle = _section(inner_geo, "INTEGRAÇÃO COM AERODYNAMIC_REPORT")
    _checkbtn(s_geo_toggle, "Habilitar módulo de cálculo geométrico por RA", ativar_geo_report_var).pack(anchor="w")

    # Lock geometry toggle
    geo_lock_var = tk.BooleanVar(value=False)
    geo_lock_chk = tk.Checkbutton(
        s_geo_toggle,
        text="🔒  Bloquear c e b na aba ✈ VOO (derivar de RA e S abaixo)",
        variable=geo_lock_var,
        bg=BG, fg=YELLOW, selectcolor=PANEL,
        activebackground=BG, activeforeground=ACCENT,
        font=("Courier", 9, "bold"),
    )
    geo_lock_chk.pack(anchor="w", pady=4)

    # Inputs dos parâmetros alvo que alimentarão o aerodynamic_report
    s_geo_param = _section(inner_geo, "PARÂMETROS DE ENTRADA PARA O RELATÓRIO")

    ra_alvo_var   = tk.StringVar(value="8.0")
    area_alvo_var = tk.StringVar(value="1.5")

    _entry_row(s_geo_param, "Razão de Aspecto Alvo (RA)", ra_alvo_var,   unit="",   min_val=0.5,  max_val=50.0)
    _entry_row(s_geo_param, "Área Alar Alvo S (m²)",      area_alvo_var, unit="m²", min_val=0.01, max_val=100.0)

    # Derived c/b display
    geo_derived_var = tk.StringVar(value="")
    tk.Label(s_geo_param, textvariable=geo_derived_var, bg=PANEL, fg=ACCENT,
             font=("Courier", 9, "bold")).pack(anchor="w", pady=4)

    # ── Wire: push derived c/b into c_var/b_var and disable entries when lock ON ──
    _geo_entries_ref.extend([_ent_c, _ent_b])  # populated here, used in _apply_geo_lock

    def _apply_geo_lock(*_):
        """Compute c/b from RA+S and push to flight vars if lock is active."""
        try:
            ra  = _safe(ra_alvo_var,   8.0)
            s   = _safe(area_alvo_var, 1.5)
            from analise_ra_calc import geometria_de_ra_e_s
            geom = geometria_de_ra_e_s(ra, s)
            geo_derived_var.set(
                f"→  b = {geom['b']:.3f} m   c = {geom['c']:.3f} m   "
                f"AR = {geom['AR']:.2f}   S = {geom['S']:.3f} m²"
            )
            if geo_lock_var.get():
                c_var.set(f"{geom['c']:.4f}")
                b_var.set(f"{geom['b']:.4f}")
                # Disable the entry widgets in the VOO tab
                for ent in _geo_entries_ref:
                    try:
                        ent.config(state="disabled", disabledbackground="#1e3a1e",
                                   disabledforeground=MUTED)
                    except Exception:
                        pass
            else:
                # Re-enable entries
                for ent in _geo_entries_ref:
                    try:
                        ent.config(state="normal", bg="#21262d")
                    except Exception:
                        pass
        except Exception as exc:
            geo_derived_var.set(f"✗ {exc}")

    for v in (ra_alvo_var, area_alvo_var, geo_lock_var):
        v.trace_add("write", _apply_geo_lock)
    _apply_geo_lock()

    s_geo_info = _section(inner_geo, "INFO")
    tk.Label(s_geo_info,
             text="  Com 🔒 ativo: c e b na aba ✈ VOO são derivados de RA e S.\n"
                  "  Os campos ficam readonly — não editáveis manualmente.\n"
                  "  Esta aba exportará RA e S para aerodynamic_report.",
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

    s_graf2 = _section(inner3, "GRÁFICOS SADRAEY+LLT (Figura 2 — requer aba 📐 ativa)")
    show_sad_graf_var = tk.BooleanVar(value=True)
    _checkbtn(s_graf2,
              "Gerar gráficos de análise conceitual (Sadraey+LLT)",
              show_sad_graf_var).pack(anchor="w")

    tk.Label(s_graf2,
             text=(
                 "  Inclui: polar CD·CL, varredura RA·S, altitude, AOA 3D  |  "
                 "tabela de geometrias LLT"
             ),
             bg=PANEL, fg=MUTED, font=("Courier", 8), justify="left").pack(anchor="w", pady=2)

    # Resumo dinâmico
    s_resumo = _section(inner3, "RESUMO DOS PARÂMETROS ATUAIS")
    resumo_var = tk.StringVar()
    def _upd_resumo(*_):
        v = v_var.get(); c = _safe(c_var); b = _safe(b_var); pe = peso_var.get()
        # Calcular atmosfera automaticamente
        from aerodynamic_report import calcular_atmosfera_isa
        atm = calcular_atmosfera_isa(_safe(alt_var, 0), _safe(temp_voo_var, 15.0))
        rho = atm["rho"]
        mu = atm["mu"]
        rho_display_var.set(f"ρ = {rho:.4f} kg/m³  |  {atm['P_Pa']/100:.1f} hPa  |  ISA {atm['delta_T']:+.1f}°C")
        v_som = atm["v_som"]
        s = b * c; ar = b**2 / s if s > 0 else 0
        re = rho * v * c / mu
        vs = vs_var.get(); vc = vc_var.get()
        if ativar_sad_var.get():
            sad_str = f"Sadraey: Vs={vs_var.get():.1f}m/s (calc.) Vc={vc_var.get():.1f}m/s"
        else:
            sad_str = "Sadraey: desativado"
        resumo_var.set(
            f"V={v} m/s  c={c} m  b={b} m  W={pe} kg  ρ={rho} kg/m³\n"
            f"S={s:.3f} m²  AR={ar:.2f}  Re={re:.0f}\n"
            f"Asa: {asat_var.get()}  |  {sad_str}"
        )
    for var in (v_var, c_var, b_var, peso_var, alt_var, temp_voo_var, vs_var, vc_var):
        var.trace_add("write", _upd_resumo)
    ativar_sad_var.trace_add("write", _upd_resumo)
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
            _bind_lb_vs()

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
            messagebox.showerror("Dark Wing", "Selecione pelo menos 1 aerofólio.")
            return
        if len(sel_perf_idx) > 3:
            messagebox.showerror("Dark Wing", "Selecione no máximo 3 aerofólios.")
            return

        # Validar corda e envergadura
        try:
            c_val = float(c_var.get())
            b_val = float(b_var.get())
            if c_val <= 0 or b_val <= 0:
                raise ValueError
        except (ValueError, tk.TclError):
            messagebox.showerror("Dark Wing", "Corda e Envergadura devem ser números positivos.")
            return

        lista_atual = perfis_lista_ref[0]
        perfis_sel  = [lista_atual[i] for i in sel_perf_idx]

        cfg_sadraey = None
        if ativar_sad_var.get():
            cfg_sadraey = {
                "ativar":        True,
                "Vs":            vs_var.get(),
                "Vc":            vc_var.get(),
                "perfis_sel":    perfis_sel,
                # Geometria LLT (Figura 3 + Seção 3 do relatório) só gerada
                # quando o usuário ativa explicitamente a aba 📐 GEO (RA).
                "geo_llt":       ativar_geo_report_var.get(),
            }

        result.update({
            "cancelled":      False,
            "v":              v_var.get(),
            "c":              c_val,
            "b":              b_val,
            "peso_kg":        peso_var.get(),
            "perfis_sel":     perfis_sel,
            "asat_sel":       asat_var.get(),
            "altitude_m":     float(alt_var.get() or 0),
            "temp_C":         float(temp_voo_var.get() or 15.0),
            "cfg_sadraey":    cfg_sadraey,
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
    cfg = launch_darkwing_gui()
    if cfg["cancelled"]:
        print("Simulação cancelada.")
        return

    print("\n" + "═"*65)
    print("  DARK WING PROJECT")
    print("═"*65)
    print(f"  V={cfg['v']} m/s | c={cfg['c']} m | b={cfg['b']} m | W={cfg['peso_kg']} kg")
    print(f"  Perfis: {', '.join(cfg['perfis_sel'])}")
    print(f"  Asa: {cfg['asat_sel']}")
    print("═"*65 + "\n")

    from calculos import calcular_asa
    from analise_graficos import plotar_resultados

    dados = calcular_asa(
        cfg["v"], cfg["c"], cfg["b"], cfg["peso_kg"],
        cfg["perfis_sel"], cfg["asat_sel"]
    )
    plotar_resultados(dados, None)


if __name__ == "__main__":
    main()
