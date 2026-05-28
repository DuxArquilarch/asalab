import numpy as np
import cv2
import warnings
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys
import math
import struct
from numba import njit

warnings.filterwarnings("ignore")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def launch_geometry_visualizer():
    """Abre o visualizador de geometrias no mesmo launcher."""
    try:
        from geo_visualizer import launch_geo_visualizer
        launch_geo_visualizer(parent_cfg={})
    except Exception as exc:
        messagebox.showerror("Geo Visualizer", f"Nao foi possivel abrir o visualizador:\n{exc}")

# ─────────────────────────────────────────────────────────
# FISICA E PROPRIEDADES (ISA)
# ─────────────────────────────────────────────────────────

def air_properties(altitude_m=0.0):
    T = 288.15 - 0.0065 * altitude_m
    P = 101325.0 * (T / 288.15) ** 5.2561
    rho = P / (287.05 * T)
    mu = 1.458e-6 * T**1.5 / (T + 110.4)
    return rho, mu

# ─────────────────────────────────────────────────────────
# GEOMETRIA 3D → 2D (STL SLICER)
# ─────────────────────────────────────────────────────────

def parse_stl_numpy(filepath):
    """
    Lê STL binário ou ASCII e retorna array (N,3) de vértices.
    Sem dependências externas além de NumPy.
    """
    with open(filepath, 'rb') as f:
        header = f.read(80)
        is_ascii = False
        try:
            if header.decode('ascii', errors='ignore').strip().lower().startswith('solid'):
                # Pode ser ASCII, mas alguns binários também começam com 'solid'
                # Faz um double-check lendo o restante
                f.seek(0)
                content = f.read().decode('ascii', errors='ignore')
                if 'facet normal' in content[:2000] and 'endsolid' in content[-1000:].lower():
                    is_ascii = True
        except:
            pass

        f.seek(0)
        if is_ascii:
            verts = []
            for line in f:
                line = line.decode('ascii', errors='ignore')
                if 'vertex' in line.lower():
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            verts.append([float(parts[1]), float(parts[2]), float(parts[3])])
                        except:
                            continue
            return np.array(verts, dtype=np.float64)
        else:
            # Binário
            f.seek(80)  # pula header
            num_tri = struct.unpack('<I', f.read(4))[0]
            # Cada triângulo: 12 bytes normal, 12 v0, 12 v1, 12 v2, 2 attr
            dtype = np.dtype([
                ('normal', np.float32, 3),
                ('v0', np.float32, 3),
                ('v1', np.float32, 3),
                ('v2', np.float32, 3),
                ('attr', np.uint16, 1)
            ])
            data = np.fromfile(f, dtype=dtype, count=num_tri)
            v0 = data['v0'].astype(np.float64)
            v1 = data['v1'].astype(np.float64)
            v2 = data['v2'].astype(np.float64)
            return np.vstack([v0, v1, v2])

def extract_2d_profile(verts, z_tol=1e-3, n_bins=300):
    """
    Extrai perfil 2D (X,Y) a partir de vértices 3D.
    Assume que o perfil está aproximadamente no plano Z≈0.
    Usa histograma para pegar borda superior e inferior.
    """
    # Centraliza Z para facilitar slice
    z_mid = (verts[:, 2].min() + verts[:, 2].max()) / 2.0
    mask = np.abs(verts[:, 2] - z_mid) <= z_tol
    
    if mask.sum() < 10:
        # Se não achar pontos no plano médio, pega todos e projeta no XY
        pts = verts[:, :2]
    else:
        pts = verts[mask][:, :2]
    
    # Remove duplicatas
    pts = np.unique(pts, axis=0)
    
    # Para cada faixa de X, pega Y máximo e mínimo → perfil fechado
    x_min, x_max = pts[:, 0].min(), pts[:, 0].max()
    bins = np.linspace(x_min, x_max, n_bins)
    upper, lower = [], []
    
    for i in range(len(bins)-1):
        mask_bin = (pts[:, 0] >= bins[i]) & (pts[:, 0] < bins[i+1])
        if np.any(mask_bin):
            upper.append([bins[i], pts[mask_bin, 1].max()])
            lower.append([bins[i], pts[mask_bin, 1].min()])
    
    if len(upper) < 5:
        raise ValueError("Não foi possível extrair perfil 2D do STL. Verifique orientação Z.")
    
    upper = np.array(upper)
    lower = np.array(lower)
    
    # Ordena do bordo de fuga (x max) para o bordo de ataque (x min) e volta
    upper = upper[np.argsort(upper[:, 0])]
    lower = lower[np.argsort(lower[:, 0])[::-1]]
    
    profile = np.vstack([upper, lower])
    
    # Fecha o loop se necessário
    if not np.allclose(profile[0], profile[-1]):
        profile = np.vstack([profile, profile[0]])
    
    return profile

def smooth_profile(pts, window=5):
    """Filtro de média móvel para não explodir em triangulações agressivas."""
    if len(pts) < window * 2:
        return pts
    smoothed = pts.copy()
    for i in range(2):
        cumsum = np.cumsum(np.insert(pts[:, i], 0, 0))
        smoothed[:, i] = (cumsum[window:] - cumsum[:-window]) / window
    # Mantém primeiro e último pontos intactos (bordos)
    smoothed[0] = pts[0]
    smoothed[-1] = pts[-1]
    return smoothed

def load_airfoil_robust(filepath):
    """Loader 6.0 — Suporta .DAT (Selig/Lednicer) e .STL (Inventor/CAD)."""
    if not filepath or not os.path.isfile(filepath):
        # NACA 2412 fallback
        return np.array([[1,0],[0.95,0.012],[0.8,0.038],[0.6,0.060],[0.4,0.072],
                         [0.2,0.062],[0.1,0.044],[0,0],[0.1,-0.024],[0.2,-0.034],
                         [0.4,-0.040],[0.6,-0.034],[0.8,-0.018],[0.95,-0.006],[1,0]], dtype=np.float64)

    ext = os.path.splitext(filepath)[1].lower()

    # ── STL (Inventor, SolidWorks, Fusion) ──
    if ext in ('.stl', '.stlb'):
        verts = parse_stl_numpy(filepath)
        pts = extract_2d_profile(verts)
        pts = smooth_profile(pts, window=5)
        # Normalização padrão
        x_min, x_max = pts[:, 0].min(), pts[:, 0].max()
        chord = x_max - x_min
        pts[:, 0] = (pts[:, 0] - x_min) / chord
        pts[:, 1] = pts[:, 1] / chord
        return pts

    # ── DAT / TXT (Airfoil Tools) ──
    raw_lines = []
    with open(filepath, 'r', errors='ignore') as f:
        raw_lines = f.readlines()

    def is_lednicer(lines):
        for line in lines[1:4]:
            parts = line.split()
            if len(parts) == 2:
                try:
                    a, b = float(parts[0]), float(parts[1])
                    if a > 2.0 and b > 2.0:
                        return True
                except: pass
        return False

    coords = []
    if is_lednicer(raw_lines):
        skip = 0
        for i, line in enumerate(raw_lines):
            parts = line.split()
            if len(parts) == 2:
                try:
                    a, b = float(parts[0]), float(parts[1])
                    if a > 2.0 and b > 2.0:
                        skip = i + 1
                        break
                except: pass
        for line in raw_lines[skip:]:
            parts = line.split()
            if len(parts) == 2:
                try: coords.append([float(parts[0]), float(parts[1])])
                except: continue
    else:
        started = False
        for line in raw_lines:
            parts = line.split()
            if len(parts) == 2:
                try:
                    x, y = float(parts[0]), float(parts[1])
                    if not started and abs(x) > 2.0:
                        continue
                    coords.append([x, y])
                    started = True
                except: continue

    if len(coords) < 6:
        return np.array([[1,0],[0.95,0.012],[0.8,0.038],[0.6,0.060],[0.4,0.072],
                         [0.2,0.062],[0.1,0.044],[0,0],[0.1,-0.024],[0.2,-0.034],
                         [0.4,-0.040],[0.6,-0.034],[0.8,-0.018],[0.95,-0.006],[1,0]], dtype=np.float64)

    pts = np.array(coords, dtype=np.float64)
    x_min, x_max = pts[:, 0].min(), pts[:, 0].max()
    chord = x_max - x_min
    pts[:, 0] = (pts[:, 0] - x_min) / chord
    pts[:, 1] = pts[:, 1] / chord
    return pts

# ─────────────────────────────────────────────────────────
# SOLVER ESTABILIZADO (sem alterações estruturais)
# ─────────────────────────────────────────────────────────

@njit
def solve_step(vxa, vya, pa, rho, mu, dl, dt, nu_extra=0.0):
    nx, ny = vxa.shape
    nvx, nvy, np_arr = vxa.copy(), vya.copy(), pa.copy()
    nu_art = (mu / rho) + 0.012 + nu_extra
    max_v = 0.1
    for i in range(1, nx - 1):
        for j in range(1, ny - 1):
            dvx_dx = (vxa[i+1, j] - vxa[i-1, j]) / (2 * dl)
            dvx_dy = (vxa[i, j+1] - vxa[i, j-1]) / (2 * dl)

            nvx[i, j] -= (vxa[i, j] * dvx_dx + vya[i, j] * dvx_dy) * dt
            nvy[i, j] -= (vxa[i, j] * (vya[i+1, j] - vya[i-1, j]) / (2 * dl) + vya[i, j] * (vya[i, j+1] - vya[i, j-1]) / (2 * dl)) * dt

            diff_coef = nu_art * (dt / dl**2)
            if diff_coef > 0.24: diff_coef = 0.24

            nvx[i, j] += diff_coef * (vxa[i+1, j] + vxa[i-1, j] + vxa[i, j+1] + vxa[i, j-1] - 4*vxa[i, j])
            nvy[i, j] += diff_coef * (vya[i+1, j] + vya[i-1, j] + vya[i, j+1] + vya[i, j-1] - 4*vya[i, j])

            div = (nvx[i+1, j] - nvx[i-1, j] + nvy[i, j+1] - nvy[i, j-1]) / (2 * dl)
            np_arr[i, j] = (pa[i+1, j] + pa[i-1, j] + pa[i, j+1] + pa[i, j-1]) / 4.0 - (rho * dl**2 / (4 * dt)) * div

            v_m = math.sqrt(nvx[i, j]**2 + nvy[i, j]**2)
            if v_m > max_v: max_v = v_m
    return nvx, nvy, np_arr, max_v

# ─────────────────────────────────────────────────────────
# MENU DARK (atualizado para aceitar STL)
# ─────────────────────────────────────────────────────────

def launch_ui():
    root = tk.Tk()
    root.title("AeroSim v4.1.0 — Inventor Compatible")
    root.geometry("530x580")
    root.configure(bg="#0d1117")
    ACCENT, BG, PANEL, TEXT = "#58a6ff", "#0d1117", "#161b22", "#e6edf3"
    res = {"filepath": None, "aoa": 5.0, "velocity": 30.0, "altitude": 0.0, "save_gif": False, "cancelled": True}

    tk.Label(root, text="AEROSIM v4.1", bg=PANEL, fg=ACCENT, font=("Courier", 16, "bold"), pady=15).pack(fill="x")
    body = tk.Frame(root, bg=BG, padx=22, pady=10); body.pack(fill="both", expand=True)

    s1 = tk.LabelFrame(body, text=" GEOMETRIA (.DAT / .STL) ", bg=BG, fg=ACCENT, font=("Courier", 9, "bold"), bd=1, pady=10)
    s1.pack(fill="x", pady=8)
    path_v = tk.StringVar(value="(Selecione .DAT ou .STL)")
    tk.Entry(s1, textvariable=path_v, bg="#21262d", fg=TEXT, relief="flat").pack(side="left", fill="x", expand=True, padx=5)
    tk.Button(s1, text="ARQUIVO", command=lambda: path_v.set(
        filedialog.askopenfilename(filetypes=[("Airfoil/3D", "*.dat *.DAT *.stl *.STL")]) or path_v.get()
    )).pack(side="right", padx=5)

    s2 = tk.LabelFrame(body, text=" PARÂMETROS ", bg=BG, fg=ACCENT, font=("Courier", 9, "bold"), bd=1, pady=10)
    s2.pack(fill="x", pady=8)
    aoa_v, vel_v, alt_v = tk.DoubleVar(value=5.0), tk.DoubleVar(value=30.0), tk.DoubleVar(value=0.0)
    
    tk.Scale(s2, from_=-20, to=20, resolution=0.5, orient="horizontal", variable=aoa_v, label="AoA (Graus)", bg=BG, fg=TEXT, highlightthickness=0).pack(fill="x")
    tk.Scale(s2, from_=5, to=60, resolution=1, orient="horizontal", variable=vel_v, label="Velocidade (m/s)", bg=BG, fg=TEXT, highlightthickness=0).pack(fill="x")
    tk.Scale(s2, from_=0, to=5000, resolution=100, orient="horizontal", variable=alt_v, label="Altitude (m)", bg=BG, fg=TEXT, highlightthickness=0).pack(fill="x")

    # Dica para STL
    tk.Label(body, text="Dica: exporte do Inventor como STL binário,\ncom o perfil alinhado ao plano XY.", 
             bg=BG, fg="#8b949e", font=("Courier", 8)).pack(pady=4)

    gif_v = tk.BooleanVar(value=False)
    tk.Checkbutton(body, text="Salvar GIF ", variable=gif_v, bg=BG, fg=TEXT, selectcolor=PANEL).pack(pady=5)

    def run():
        res.update({"filepath": path_v.get() if os.path.isfile(path_v.get()) else None, 
                    "aoa": aoa_v.get(), "velocity": vel_v.get(), "altitude": alt_v.get(),
                    "save_gif": gif_v.get(), "cancelled": False})
        root.destroy()

    tk.Button(root, text="EXECUTAR SIMULAÇÃO", command=run, bg=ACCENT, fg=BG, font=("Courier", 12, "bold"), pady=12).pack(fill="x", padx=22, pady=15)
    root.mainloop(); return res

# ─────────────────────────────────────────────────────────
# MAIN (com proteções anti-explosão para CAD)
# ─────────────────────────────────────────────────────────

def main():
    cfg = launch_ui()
    if cfg["cancelled"]: return

    Ny, Nx = 360, 640
    v_target = cfg["velocity"]
    rho, mu = air_properties(cfg["altitude"])
    dl = 1.0 / Nx
    
    # CFL mais conservador para geometrias de CAD (pode ter cantos vivos)
    dt = 0.10 / (v_target + 1e-6)

    aoa_deg = abs(cfg["aoa"])
    
    # Viscosidade extra: maior para AoA alto OU para arquivos STL (geometria mais "áspera")
    is_stl = str(cfg["filepath"]).lower().endswith('.stl')
    nu_extra = max(0.0, (aoa_deg - 6.0) * 0.005)
    if is_stl:
        nu_extra += 0.008  # amortecimento extra para malhas trianguladas

    pts_raw = load_airfoil_robust(cfg["filepath"])
    label = os.path.splitext(os.path.basename(cfg["filepath"]))[0] if cfg["filepath"] else "Airfoil"

    # MAPEAMENTO (igual ao original, mas com margem maior para STL)
    aoa = np.radians(cfg["aoa"])
    c, s = math.cos(aoa), math.sin(aoa)
    rot_matrix = np.array([[c, -s], [s, c]])

    pts_norm = pts_raw.copy()
    pts_norm[:, 0] = pts_norm[:, 0] - 0.5
    pts_norm[:, 1] = pts_norm[:, 1]

    pts_rot = (rot_matrix @ pts_norm.T).T
    scale = Nx * 0.35  # ligeiramente menor para dar margem a geometrias irregulares

    bx_min, bx_max = pts_rot[:, 0].min(), pts_rot[:, 0].max()
    by_min, by_max = pts_rot[:, 1].min(), pts_rot[:, 1].max()
    bx_center = (bx_min + bx_max) / 2.0
    by_center = (by_min + by_max) / 2.0

    pts_final = np.zeros_like(pts_rot)
    pts_final[:, 0] = (pts_rot[:, 0] - bx_center) * scale + Nx * 0.42
    pts_final[:, 1] = Ny / 2.0 - (pts_rot[:, 1] - by_center) * scale

    margin = 15
    x_out = max(0, -pts_final[:, 0].min() + margin, pts_final[:, 0].max() - (Nx - margin))
    y_out = max(0, -pts_final[:, 1].min() + margin, pts_final[:, 1].max() - (Ny - margin))
    if x_out > 0 or y_out > 0:
        shrink = min((Nx - 2*margin) / ((bx_max - bx_min) * scale + 1e-6),
                     (Ny - 2*margin) / ((by_max - by_min) * scale + 1e-6))
        scale *= shrink
        pts_final[:, 0] = (pts_rot[:, 0] - bx_center) * scale + Nx * 0.42
        pts_final[:, 1] = Ny / 2.0 - (rot_matrix @ pts_norm.T).T[:, 1] * scale  # recalcula Y puro

    mask = np.zeros((Ny, Nx), dtype=np.uint8)
    cv2.fillPoly(mask, [pts_final.astype(np.int32)], 255)
    objet = (mask.T > 127).astype(np.uint8)

    vx, vy, p = np.full((Nx, Ny), v_target, dtype=np.float64), np.zeros((Nx, Ny)), np.zeros((Nx, Ny))
    gif_frames = []

    try:
        for it in range(2500):
            vx, vy, p, v_max = solve_step(vx, vy, p, rho, mu, dl, dt, nu_extra)
            vx[1:-1, 1:-1] -= (dt/rho)*(p[2:, 1:-1]-p[:-2, 1:-1])/(2*dl)
            vy[1:-1, 1:-1] -= (dt/rho)*(p[1:-1, 2:]-p[1:-1, :-2])/(2*dl)

            v_lim = v_target * 3.5  # clamp mais agressivo para CAD
            np.clip(vx, -v_lim, v_lim, out=vx)
            np.clip(vy, -v_lim, v_lim, out=vy)

            dt = 0.30 * dl / max(v_max, v_target, 1.0)  # CFL mais seguro
            
            vx[objet==1], vy[objet==1] = 0, 0
            vx[0,:], vy[0,:] = v_target, 0

            if it % 40 == 0:
                mag = np.sqrt(vx**2 + vy**2).T
                display = cv2.merge([np.clip((mag/v_target)*127, 0, 255).astype(np.uint8)]*3)
                display[mask > 0] = [40, 40, 40]
                
                cv2.imshow(f"AeroSim Pro v4.1 — {label}", display)
                if cfg["save_gif"]: gif_frames.append(cv2.cvtColor(display, cv2.COLOR_BGR2RGB))
                if cv2.waitKey(1) & 0xFF == ord('q'): break
        
        if cfg["save_gif"] and gif_frames:
            import imageio
            imageio.mimsave(f"sim_{label}.gif", gif_frames, fps=24)

    finally:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
