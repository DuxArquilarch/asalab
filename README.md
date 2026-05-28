# Dark Wing Project — V2

> Wing performance simulator and CFD suite for RC aircraft and UAV design.  
> Built on *Fluid Mechanics* — Frank M. White, 8th Ed. · Sadraey (2013) · Prandtl LLT · ISA/Sutherland.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Module Reference](#module-reference)
4. [Aerodynamic Database](#aerodynamic-database)
5. [Physics & Methods](#physics--methods)
6. [GUI Tabs](#gui-tabs)
7. [CLI Usage](#cli-usage)
8. [Output Files](#output-files)
9. [Dependencies](#dependencies)
10. [Installation](#installation)
11. [Quick Start](#quick-start)
12. [Adding Airfoils](#adding-airfoils)
13. [References](#references)

---

## Overview

Dark Wing V2 is a multi-module aerodynamic analysis tool for fixed-wing aircraft. It takes physical flight parameters (velocity, chord, span, weight, altitude, temperature) and produces lift/drag polars, pitching moment curves, center-of-pressure displacement, structural geometry visualizations, a full Sadraey+LLT conceptual report, and a real-time 2D CFD flow simulation — all from a single unified GUI.

**Key capabilities at a glance:**

- Reynolds-dependent log₁₀ interpolation of 2D airfoil data across 4 Re breakpoints (50 k – 500 k)
- ISA + Sutherland atmosphere: density, viscosity, speed of sound from altitude and temperature
- Prandtl-Glauert compressibility correction up to Ma 0.7
- Lifting Line Theory (LLT) for 3D wing slope, induced drag, and stall prediction
- Rectangular, Elliptical, and Delta planform models with individual Oswald efficiency treatments
- Sadraey (2013) conceptual sizing: minimum wing area, geometry sweeps, altitude sweeps, drag breakdown
- Tkinter GUI with live database hot-reload, 6-tab layout, and Toplevel sub-windows
- Plotly interactive charts saved as high-resolution PNGs to `Reports/`
- 2D Navier-Stokes CFD solver (Numba JIT + OpenCV) for `.DAT` and `.STL` profile inputs
- Geometric profile viewer with cross-section, thickness distribution, camber line, pseudo-3D view

---

## Architecture

```
asalab_Main.py          ← single entry point (GUI or CLI)
│
├── gui.py              ← 6-tab Tkinter GUI, DatabaseWatcher hot-reload
│   ├── Tab ✈  VOO      — flight parameters, airfoil selection, wing type
│   ├── Tab 📐 SADRAEY  — Sadraey+LLT conceptual analysis
│   ├── Tab 📐 GEO(RA)  — aspect ratio / wing area geometry lock
│   ├── Tab 📊 GRÁFICOS — output summary & options
│   ├── Tab 🌀 AEROSIM  — Dark_Wing 2D CFD launcher
│   └── Tab 🔷 GEO VIZ  — geo_visualizer launcher
│
├── calculos.py         ← core aerodynamic calculations (ISA, LLT, polars)
├── database.py         ← airfoil data, wing types, materials, CL_MAX, CD0
├── analise_graficos.py ← Plotly Figure 1 (2×3 dashboard)
├── analise_ra_calc.py  ← NACA geometry, wing silhouette, RA/S utility
├── aerodynamic_report.py ← ISA atmosphere, Sadraey+LLT report & figures
├── geo_visualizer.py   ← Matplotlib geometry viewer (Toplevel window)
├── Dark_Wing.py        ← 2D CFD solver, STL/DAT loader, OpenCV display
└── cli.py              ← terminal interface (--cli flag)

Reports/                ← all output files saved here (auto-created)
```

---

## Module Reference

### `asalab_Main.py`
Entry point. Detects `--cli` / `-c` flag and routes to `cli.py`; otherwise launches the full GUI pipeline.

```
python asalab_Main.py           # GUI mode
python asalab_Main.py --cli     # CLI mode
```

---

### `database.py`
Central data store. Contains four exports:

| Export | Type | Description |
|--------|------|-------------|
| `DATABASE` | `dict[str, dict[int, tuple]]` | Airfoil coefficients keyed by name → Re → `(a0, αL0, Cd0, Cm, XCp)` |
| `AsaT` | `dict` | Wing planform codes: `"1"` Rectangular · `"2"` Elliptical · `"3"` Delta |
| `MATERIAIS` | `dict` | RC construction materials with density, thickness, roughness drag increment |
| `CL_MAX_2D` | `dict` | 2D maximum lift coefficient per airfoil (Abbott & von Doenhoff) |
| `CD0_PERFIL` | `dict` | Profile zero-lift drag coefficient per airfoil |

The GUI watches `database.py` for file changes and hot-reloads all lists automatically — **no restart required** when adding airfoils.

---

### `calculos.py`
Core physics engine. Called by both the GUI and CLI.

| Function | Description |
|----------|-------------|
| `calcular_asa(v, c, b, peso_kg, perfis_sel, asat_sel, altitude_m, temp_C)` | Main entry — returns full result dict for all selected profiles |
| `interpolar_coeficientes(re_alvo, dados_perfil)` | Log₁₀ Re interpolation / extrapolation with clipping |
| `correcao_prandtl_glauert(a0_2d, v, v_som)` | Applies `1/√(1-Ma²)` to lift slope |
| `correcao_asat(forma, AR)` | Returns `(e_override, κ)` for Elliptical / Delta planforms |
| `eficiencia_oswald(AR)` | Empirical Oswald e from Raymer / Sadraey fit |
| `calcular_cm_xcp(alphas, cl_asa, cm0_2d, xcp0_2d, AR, e_oswald)` | Pitching moment and center of pressure via LLT |
| `ponto_transicao(v, c, rho, mu)` | Laminar-turbulent transition location (Michel criterion, White §7.4) |

---

### `aerodynamic_report.py`
ISA atmosphere, Sadraey+LLT report engine, and Plotly figure generator.

| Function | Description |
|----------|-------------|
| `calcular_atmosfera_isa(altitude_m, temp_C)` | Full ISA + Sutherland: T, P, ρ, μ, V_sound |
| `extrair_dados_perfil(nome_perfil, re_alvo)` | Reads `DATABASE`, interpolates Re, returns normalized coefficients |
| `generate_report(cfg, output_filename)` | Writes complete `.txt` report to `Reports/` |
| `plotar_analise_sadraey(cfg)` | Generates Sadraey Figures 1–3 (PNG) to `Reports/` |
| `varredura_geometrias(...)` | LLT geometry sweep: b, c, S, e, δ, CDi across RA range |
| `varredura_altitude(...)` | CLc and CLmax vs altitude (0 → h_max) |
| `calcular_drag_breakdown(...)` | Parasitic vs induced drag decomposition, downwash gradient |
| `polar_asa(CD0, RA, e)` | Parabolic polar: CD vs CL, L/D_max, CL* |

---

### `analise_graficos.py`
Generates **Figure 1** — the 2×3 Plotly aerodynamic dashboard.

Subplots: CL · CD · L/D · Cm · XCp · Wing silhouette.  
Output: `Reports/fig1_aerodinamica_<profiles>.png` at 2× scale (≈ 2800 × 2200 px).

---

### `analise_ra_calc.py`
Geometric utilities for airfoil coordinates and wing planforms.

| Function | Description |
|----------|-------------|
| `gerar_coord_naca(nome)` | Returns `(x, y_upper, y_lower)` for NACA 4/5/6-digit and custom profiles |
| `gerar_silhueta_asat(forma, b, c)` | Wing semi-span planform polygon for Rectangular / Elliptical / Delta |
| `geometria_de_ra_e_s(perfil_nome, forma, b, c)` | Cross-checks S, AR, and airfoil volume from geometry |

---

### `gui.py`
Tkinter main window. Exports `launch_darkwing_gui()` → returns config `dict` to `asalab_Main.py`.

- **DatabaseWatcher**: background thread polling `database.py` mtime every 1.5 s; rebuilds airfoil listboxes on change without blocking the UI
- All shared variables (v, c, b, peso, altitude, Vs, Vc) are `tk.DoubleVar` / `tk.StringVar` with cross-tab traces for live summary updates
- GEO(RA) lock mode derives `c` and `b` from user-specified AR and S, disabling manual entry fields

---

### `geo_visualizer.py`
Standalone Matplotlib geometry viewer opened as a `Toplevel` window from the GEO VIZ tab (or independently via `python geo_visualizer.py`).

**Displays per profile:**
- Upper/lower surface contours
- Mean camber line
- Thickness distribution (t/c vs x/c)
- Max-thickness vertical marker with annotation
- Pseudo-3D semi-wing sweep (14 chord slices, tapered by planform)
- Geometric metrics table: t/c max, camber max, location of each, area, LE radius

Accepts a `parent_cfg` dict to pre-populate selections from the main GUI tab. Supports custom `.DAT` / `.STL` profiles injected via `_CUSTOM_PROFILES`.

---

### `Dark_Wing.py`
2D incompressible CFD solver for airfoil cross-sections.

**Input formats:**
- `.DAT` — Selig or Lednicer format (standard airfoil coordinate files)
- `.STL` — binary or ASCII STL from CAD tools (Inventor, SolidWorks, Fusion 360); extracts mid-plane cross-section automatically

**Solver:** Explicit Navier-Stokes (velocity-pressure split), Numba `@njit` JIT-compiled inner loop, CFL-adaptive timestep, artificial viscosity stabilizer.  
**Output:** Real-time OpenCV window showing velocity magnitude field. Optional GIF export to `Reports/`.

---

### `cli.py`
Terminal interface. Identical physics to the GUI, with text prompts for all inputs.

```
python asalab_Main.py --cli
```

Accepts 1–3 airfoil selections, wing type, flight parameters, and optionally triggers the Sadraey+LLT report.

---

## Aerodynamic Database

Airfoil data is stored as `(a0_2d [1/°], αL0 [°], Cd0, Cm_ac, XCp)` tuples at discrete Reynolds numbers. The interpolation system extrapolates smoothly outside the tabulated range using log₁₀(Re) spacing.

| Airfoil | Family | CLmax | CD0 | Re range |
|---------|--------|-------|-----|----------|
| NACA 4412 | 4-digit | 1.650 | 0.009 | 50k – 500k |
| NACA 6412 | 4-digit | 1.700 | 0.010 | 50k – 500k |
| NACA 23015 | 5-digit | 1.500 | 0.009 | 50k – 500k |
| NACA 63-215 | 6-digit | 1.450 | 0.007 | 50k – 500k |
| NACA6409 9% | 4-digit | 1.480 | 0.012 | 50k – 500k |
| NACA 6909_54.79%_6412 | Blended | 1.600 | 0.009 | 50k – 500k |
| SELIG 1223 | High-lift | 2.100 | 0.018 | 50k – 500k |
| CH10_S1210_30 | High-lift cargo | 1.990 | 0.012 | 30k – 650k |
| MH 32 | Martin Hepperle | 1.300 | 0.010 | 50k – 500k |

**Tuple layout per Re entry:**

```python
DATABASE["NACA 4412"][100000] = (
    0.092,   # a0_2d    — lift slope [1/°]
   -3.9,     # αL0      — zero-lift angle [°]
    0.018,   # Cd0      — profile drag coefficient
   -0.095,   # Cm_ac    — pitching moment at aerodynamic center
    0.31,    # XCp      — center of pressure [x/c]
)
```

---

## Physics & Methods

### Atmosphere — ISA + Sutherland (White §1.8)

$$T(h) = T_0 - L \cdot h \qquad P(h) = P_0\left(\frac{T}{T_0}\right)^{g/(RL)} \qquad \rho = \frac{P}{RT}$$

$$\mu(T) = \mu_0 \left(\frac{T}{T_0}\right)^{3/2} \frac{T_0 + S}{T + S} \qquad S = 110.4 \text{ K}$$

### Reynolds Number & Interpolation

$$Re = \frac{\rho V c}{\mu}$$

Coefficients are interpolated linearly in $\log_{10}(Re)$ space between the two nearest table breakpoints, with extrapolation beyond the range and physical clipping of all five coefficient channels.

### Prandtl-Glauert Correction (White §8.7)

$$a_{0,\text{corrected}} = \frac{a_{0,\text{2D}}}{\sqrt{1 - Ma^2}} \qquad Ma = \frac{V}{a(T)}$$

Valid up to Ma ≈ 0.7. A warning is printed for Ma ≥ 0.7.

### Lifting Line Theory — 3D Wing Slope (White §8.4, Sadraey 2013)

$$C_{L\alpha,\text{3D}} = \frac{C_{L\alpha,\text{2D}}}{1 + \frac{57.3 \cdot C_{L\alpha,\text{2D}}}{\pi \cdot e \cdot AR}}$$

### Induced Drag & Oswald Efficiency

$$C_{D,\text{induced}} = \frac{C_L^2}{\pi \cdot AR \cdot e} \qquad e = 1.78(1 - 0.045 \cdot AR^{0.68}) - 0.64$$

For **Elliptical** planform: $e = 1.0$ (ideal).  
For **Delta** planform ($AR < 3$): blend of slender delta slope $C_{L\alpha} = \pi AR / 2$ with LLT, empirical $e \in [0.60, 0.88]$.

### Stall Angle (Sadraey)

$$\alpha_{\text{stall}} = \frac{1.2 + 0.12 \cdot AR}{C_{L\alpha,\text{3D}}} + \alpha_{L0}$$

### Pitching Moment & Center of Pressure

$$C_m(\alpha) = C_{m0} - 0.05 \cdot C_L - 0.12 \cdot C_{D,i}$$

$$X_{Cp} = 0.25 - \frac{C_m}{C_L} \qquad (C_L > 0.05)$$

### Laminar-Turbulent Transition — Michel Criterion (White §7.4)

$$x_{tr} = \frac{Re_{tr} \cdot \mu}{\rho V} \qquad Re_{tr} = 5 \times 10^5$$

### Downwash Gradient (Sadraey 2013 §12)

$$\frac{d\varepsilon}{d\alpha} = \frac{2 C_{L\alpha,\text{3D}}}{\pi \cdot AR}$$

---

## GUI Tabs

| Tab | Purpose |
|-----|---------|
| **✈ VOO** | Velocity, chord, span, weight, altitude, temperature, wing type, airfoil selection (up to 3) |
| **📐 SADRAEY** | Enable Sadraey+LLT analysis; set stall speed Vs (auto-calculated) and cruise speed Vc |
| **📐 GEO (RA)** | Set target AR and S; optionally lock c/b in VOO tab to derived values |
| **📊 GRÁFICOS** | Toggle Sadraey figure generation; live parameter summary |
| **🌀 AEROSIM** | Load `.DAT`/`.STL` profile; set AoA, velocity, altitude; launch 2D CFD in background thread |
| **🔷 GEO VIZ** | Open geometric profile viewer pre-filled from VOO tab; optionally inject custom profile |

---

## CLI Usage

```
python asalab_Main.py --cli
```

The CLI prompts in sequence:

```
[1] Parâmetros de voo: velocidade  corda  envergadura  peso
    Exemplo: 15  0.6  3.0  28

[2] Seleção de aerofólios (1–3 números separados por espaço)
    Exemplo: 1 5 8

[3] Tipo de asa: [1] Retangular  [2] Elíptica  [3] Delta

[4] Análise Sadraey+LLT? [s/n]
    → Se sim: Vs e Vc em m/s
```

---

## Output Files

All files are written to `Reports/` (created automatically if missing or deleted).

| File | Generator | Description |
|------|-----------|-------------|
| `fig1_aerodinamica_<profiles>.png` | `analise_graficos.py` | 2×3 aerodynamic dashboard — CL, CD, L/D, Cm, XCp, wing silhouette |
| `sadraey_fig1_<profile>.png` | `aerodynamic_report.py` | S vs RA sweep · Oswald e · altitude sweeps |
| `sadraey_fig2_<profile>.png` | `aerodynamic_report.py` | Polar CD-CL · CL(α) · L/D(α) · CDi(CL²) |
| `sadraey_fig3_<profile>.png` | `aerodynamic_report.py` | LLT geometry table (requires GEO RA tab active) |
| `aerodynamic_report_<profile>.txt` | `aerodynamic_report.py` | Full structured text report with all Sadraey sections |
| `sim_<label>.gif` | `gui.py` (AeroSim tab) | CFD velocity field animation (when GIF option is enabled) |
| `geometria_perfil.png` | `geo_visualizer.py` | Profile geometry export from the GEO VIZ tab |

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `numpy` | ≥ 1.24 | All numerical computation |
| `plotly` | ≥ 5.0 | Interactive charts, PNG export |
| `kaleido` | ≥ 0.2 | Plotly static image export (`write_image`) |
| `matplotlib` | ≥ 3.7 | Geometry viewer (geo_visualizer) |
| `tkinter` | stdlib | GUI — included with Python on all platforms |
| `numba` | ≥ 0.57 | JIT compilation for CFD solver |
| `opencv-python` | ≥ 4.8 | CFD display window (`cv2`) |
| `imageio` | ≥ 2.28 | GIF export from AeroSim |

> `tkinter` is bundled with CPython on Windows and macOS. On Linux: `sudo apt install python3-tk`

---

## Installation

```bash
# 1. Clone or copy the project folder
git clone <repo-url>
cd dark-wing

# 2. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install numpy plotly kaleido matplotlib numba opencv-python imageio

# 4. Linux only — Tkinter
sudo apt install python3-tk

# 5. Run
python asalab_Main.py
```

---

## Quick Start

**GUI:**
```
python asalab_Main.py
```
1. Tab **✈ VOO** — set velocity, chord, span, weight; select 1–3 airfoils and wing type
2. Tab **📐 SADRAEY** — check "Ativar análise conceitual" and set Vc
3. Click **✈ EXECUTAR SIMULAÇÃO**
4. PNGs and report appear in `Reports/`

**2D CFD:**
1. Go to tab **🌀 AEROSIM**
2. Select a `.DAT` airfoil file (or leave blank for built-in NACA 2412)
3. Set AoA, velocity, altitude
4. Click **🌀 EXECUTAR AEROSIM** — OpenCV window opens; press `q` to stop

**Geometry viewer:**
1. Select airfoils in tab **✈ VOO**
2. Go to tab **🔷 GEO VIZ** and click **🔷 ABRIR VISUALIZADOR DE GEOMETRIAS**
3. Enable "Vista pseudo-3D" and "Comparação (overlay)" for full view

---

## Adding Airfoils

Open `database.py` and add an entry to `DATABASE`, `CL_MAX_2D`, and `CD0_PERFIL`:

```python
DATABASE["MY NACA XXXX"] = {
    50000:  (a0, alpha_L0, Cd0, Cm, XCp),
    100000: (a0, alpha_L0, Cd0, Cm, XCp),
    200000: (a0, alpha_L0, Cd0, Cm, XCp),
    500000: (a0, alpha_L0, Cd0, Cm, XCp),
}
CL_MAX_2D["MY NACA XXXX"] = 1.55
CD0_PERFIL["MY NACA XXXX"] = 0.010
```

**Column reference:**

| Index | Symbol | Unit | Typical range |
|-------|--------|------|---------------|
| 0 | `a0_2d` | 1/° | 0.08 – 0.12 |
| 1 | `αL0` | ° | −8 to +1 |
| 2 | `Cd0` | — | 0.005 – 0.05 |
| 3 | `Cm_ac` | — | −0.20 to 0.00 |
| 4 | `XCp` | x/c | 0.25 – 0.50 |

Save the file — the GUI will detect the change and rebuild the airfoil lists automatically within 1.5 seconds.

---

## References

| Source | Scope |
|--------|-------|
| White, F.M. *Fluid Mechanics*, 8th Ed. McGraw-Hill, 2016 | §7.3 roughness · §7.4 Michel transition · §8.1 NACA geometry · §8.3 parabolic polar · §8.4 LLT · §8.7 Prandtl-Glauert · §8.8 delta wings |
| Sadraey, M. *Aircraft Design: A Systems Engineering Approach*. Wiley, 2013 | Wing sizing · Oswald efficiency · CL targets · downwash · drag breakdown · materials (Cap. 6) |
| Abbott, I.H.; von Doenhoff, A.E. *Theory of Wing Sections*. Dover, 1959 | CLmax and CD0 reference values |
| Glauert, H. *The Elements of Aerofoil and Airscrew Theory*. Cambridge, 1926 | δ correction factor for non-elliptic lift distribution |
| Hepperle, M. MH-Aerotools Airfoil Database. mh-aerotools.de | MH 32 profile data |
| XFLR5 v6 | Cross-validation of coefficient tables |

---

*Dark Wing Project V2 — all output saved to `Reports/`*
