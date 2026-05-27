import sys


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--cli", "-c", "cli"):
        from cli import main_cli
        main_cli()
    else:
        from gui import launch_darkwing_gui
        from calculos import calcular_asa
        from analise_graficos import plotar_resultados
        from aerodynamic_report import generate_report, plotar_analise_sadraey

        cfg = launch_darkwing_gui()

        if cfg.get("cancelled"):
            print("Simulação cancelada.")
            return

        print("\n" + "═" * 65)
        print("  DARK WING PROJECT V2")
        print("═" * 65)
        print(f"  V={cfg['v']} m/s | c={cfg['c']} m | b={cfg['b']} m | W={cfg['peso_kg']} kg")
        print(f"  Altitude: {cfg.get('altitude_m', 0):.0f} m | Temp: {cfg.get('temp_C', 15):.1f} °C")
        print(f"  Perfis: {', '.join(cfg['perfis_sel'])}")
        print(f"  AsaT: {cfg['asat_sel']}")
        if cfg.get("cfg_sadraey"):
            sad = cfg["cfg_sadraey"]
            print(f"  Sadraey+LLT: Vs={sad['Vs']:.1f}m/s  Vc={sad['Vc']:.1f}m/s  "
                  f"perfis={', '.join(sad['perfis_sel'])}")
        print("═" * 65 + "\n")

        dados = calcular_asa(cfg["v"], cfg["c"], cfg["b"], cfg["peso_kg"],
                             cfg["perfis_sel"], cfg["asat_sel"],
                             cfg.get("altitude_m", 0), cfg.get("temp_C", 15.0))
        plotar_resultados(dados, None)

        if cfg.get("cfg_sadraey") and cfg["cfg_sadraey"]["ativar"]:
            print("\n  [Sadraey+LLT] Executando análise conceitual...")
            sad = cfg["cfg_sadraey"]
            # Calculate Re from the main analysis for proper interpolation
            from aerodynamic_report import calcular_atmosfera_isa
            atm = calcular_atmosfera_isa(cfg.get("altitude_m", 0), cfg.get("temp_C", 15.0))
            rho = atm["rho"]
            mu = atm["mu"]
            re_real = rho * cfg["v"] * cfg["c"] / mu

            base_cfg = {
                "v": cfg["v"],
                "c": cfg["c"],
                "b": cfg["b"],
                "peso_kg": cfg["peso_kg"],
                "WTO_N": cfg["peso_kg"] * 9.81,
                "Vc": sad["Vc"],
                "Vs": sad["Vs"],
                "altitude_m": cfg.get("altitude_m", 0),
                "temp_C": cfg.get("temp_C", 15.0),
                "perfis_sel": sad["perfis_sel"],
                "re_real": re_real,
            }
            for perfil in sad["perfis_sel"]:
                report_cfg = {
                    **base_cfg,
                    "perfil":  perfil,
                    # Repassa o flag: Figura 3 (Geometrias LLT) e Seção 3 do
                    # relatório só são geradas quando o usuário ativou GEO (RA).
                    "geo_llt": sad.get("geo_llt", False),
                }
                generate_report(report_cfg, output_filename=f"aerodynamic_report_{perfil.replace(' ','_')}.txt")
                plotar_analise_sadraey(report_cfg)


if __name__ == "__main__":
    main()
