import sys


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--cli", "-c", "cli"):
        from cli import main_cli
        main_cli()
    else:
        from gui import launch_asalab_gui
        from calculos import calcular_asa, calcular_asa_multi_temp
        from analise_graficos import plotar_resultados
        from analise_multi_temp import plotar_multi_temp

        cfg = launch_asalab_gui()

        if cfg.get("cancelled"):
            print("Simulação cancelada.")
            return

        print("\n" + "═" * 65)
        print("  ASALAB XYZ V2")
        print("═" * 65)
        print(f"  V={cfg['v']} m/s | c={cfg['c']} m | b={cfg['b']} m | W={cfg['peso_kg']} kg")
        print(f"  Perfis: {', '.join(cfg['perfis_sel'])}")
        print(f"  AsaT: {cfg['asat_sel']}")
        if cfg.get("cfg_multi_temp"):
            mt = cfg["cfg_multi_temp"]
            print(f"  Multi-Temp: {mt['t_min']:.0f}–{mt['t_max']:.0f} °C  "
                  f"passo={mt['t_step']:.1f} °C  perfis={', '.join(mt['perfis_sel'])}")
        print("═" * 65 + "\n")

        dados = calcular_asa(cfg["v"], cfg["c"], cfg["b"], cfg["peso_kg"],
                             cfg["perfis_sel"], cfg["asat_sel"])
        plotar_resultados(dados, None)

        if cfg.get("cfg_multi_temp") and cfg["cfg_multi_temp"]["ativar"]:
            print("\n  [Multi-Temp] Calculando variação térmica...")
            mt = cfg["cfg_multi_temp"]
            res_mt = calcular_asa_multi_temp(
                cfg["v"], cfg["c"], cfg["b"], cfg["peso_kg"],
                mt["perfis_sel"], cfg["asat_sel"],
                temp_min=mt["t_min"], temp_max=mt["t_max"], temp_step=mt["t_step"])
            plotar_multi_temp(res_mt, cfg)


if __name__ == "__main__":
    main()
