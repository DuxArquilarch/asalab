# ================================================================= #
# AsalabXYZ — MÓDULO 3: ANÁLISE, GRÁFICOS + MATERIAIS/PESO/STALL   #
#                                                                    #
# Figura 1 (sempre): layout 2×3 aerodinâmico — original intacto.   #
# Figura 2 (opcional): tabelas Módulo 4 — materiais/peso/stall.     #
#                                                                    #
# White, F.M. Fluid Mechanics, 8ª Ed., 2016 (aerodinâmica)         #
# Sadraey, M. Aircraft Design, Wiley, 2013  (materiais/peso/stall)  #
# ================================================================= #

import re
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from database import DATABASE, AsaT, MATERIAIS, CL_MAX_2D, CD0_PERFIL
from calculos import calcular_asa

from materiais_peso_stall import (
    estimar_componentes, peso_asa_material,
    cl_max_asa_finita, velocidade_stall,
    cd0_total, polar_e_desempenho,
    eficiencia_oswald, fracoes_peso,
)


# ================================================================= #
# GEOMETRIA DO PERFIL (White §8.1)                                   #
# ================================================================= #

def gerar_coord_naca(nome):
    x = np.linspace(0, 1, 101)
    def thickness(t):
        return 5*t*(0.2969*np.sqrt(x)-0.1260*x-0.3516*x**2+0.2843*x**3-0.1015*x**4)
    u = nome.upper()
    if "23012" in u:
        r,k1=0.2025,15.957
        yc=np.where(x<r,k1/6*(x**3-3*r*x**2+r**2*(3-r)*x),k1*r**3/6*(1-x)); yt=thickness(0.12)
    elif "23015" in u:
        r,k1=0.2025,15.957
        yc=np.where(x<r,k1/6*(x**3-3*r*x**2+r**2*(3-r)*x),k1*r**3/6*(1-x)); yt=thickness(0.15)
    elif "63-2" in u or "632" in u:
        m,p=0.02,0.35
        yc=np.where(x<p,m/p**2*(2*p*x-x**2),m/(1-p)**2*((1-2*p)+2*p*x-x**2)); yt=thickness(0.15)
    elif "65-2" in u or "652" in u:
        m,p=0.015,0.40
        yc=np.where(x<p,m/p**2*(2*p*x-x**2),m/(1-p)**2*((1-2*p)+2*p*x-x**2)); yt=thickness(0.10)
    elif "4412" in u:
        m,p=0.04,0.4
        yc=np.where(x<p,m/p**2*(2*p*x-x**2),m/(1-p)**2*((1-2*p)+2*p*x-x**2)); yt=thickness(0.12)
    elif "6412" in u:
        m,p=0.06,0.4
        yc=np.where(x<p,m/p**2*(2*p*x-x**2),m/(1-p)**2*((1-2*p)+2*p*x-x**2)); yt=thickness(0.12)
    elif "1223" in u:
        m,p=0.11,0.2
        yc=np.where(x<p,m/p**2*(2*p*x-x**2),m/(1-p)**2*((1-2*p)+2*p*x-x**2)); yt=thickness(0.23)
    else:
        m,p=0.05,0.5
        yc=np.where(x<p,m/p**2*(2*p*x-x**2),m/(1-p)**2*((1-2*p)+2*p*x-x**2)); yt=thickness(0.15)
    return x, yc+yt, yc-yt

def gerar_silhueta_asat(forma, b, c):
    if forma=="Retangular":
        return [0,b/2,b/2,0,0],[0,0,c,c,0]
    elif forma=="Elíptica":
        th=np.linspace(0,np.pi,120)
        return list((b/2)*np.sin(th))+[0], list(c*np.cos(th)/2+c/2)+[c/2]
    else:
        return [0,b/2,0,0],[0,c/2,c,0]

# ================================================================= #
# PALETA                                                             #
# ================================================================= #
CORES  = ["#01021A","#EF553B","#00CC96"]
DASHES = ["solid","dot","dash"]

# ================================================================= #
# MENU HELPERS                                                       #
# ================================================================= #
def _L(char="─",n=65): print(char*n)
def _cab(t): _L("═"); print(f"   {t}"); _L("═")
def _sec(t): print(); _L(); print(f"  {t}"); _L()
def _ex(t):  print(f"      Exemplo: {t}")

def _exibir_perfis(lista):
    _sec("PERFIS DISPONÍVEIS")
    print(f"  {'Nº':<4} {'Perfil':<32} {'Família':<12} {'CLmax':>6}  {'CD0':>8}")
    _L(" ",68)
    for i,p in enumerate(lista,1):
        fam=("5-dígitos" if any(d in p for d in ["23012","23015"])
             else "6-dígitos" if any(d in p for d in ["63-","65-"]) else "4-dígitos")
        clm=CL_MAX_2D.get(p,"—"); cd0=CD0_PERFIL.get(p,"—")
        print(f"  {i:<4} {p:<32} {fam:<12} "
              f"{(f'{clm:.3f}' if isinstance(clm,float) else clm):>6}  "
              f"{(f'{cd0:.5f}' if isinstance(cd0,float) else cd0):>8}")

def _exibir_asat():
    _sec("TIPOS DE ASA (AsaT)")
    for k,(n,d) in {"1":("Retangular","e_Oswald padrão | κ=1.00"),
                    "2":("Elíptica","e=1.00 (ideal) | κ=1.00"),
                    "3":("Delta","e empírico | κ=0.90")}.items():
        print(f"  [{k}]  {n:<14} — {d}")

def _exibir_materiais():
    _sec("MATERIAIS RC  (Módulo 4 — Sadraey Cap. 6)")
    nomes=list(MATERIAIS.keys())
    for i,n in enumerate(nomes,1):
        m=MATERIAIS[n]
        print(f"  [{i:>2}]  {n:<37}  {m['densidade_kg_m3']:>5} kg/m³  "
              f"e={m['espessura_mm']} mm  ΔCd0={m['cd0_rugosidade']:.4f}")
    return nomes

# ================================================================= #
# COLETA DE INPUTS                                                   #
# ================================================================= #
def coletar_inputs():
    lista_perfis=list(DATABASE.keys())
    _cab("ASALAB XYZ — SIMULADOR AERODINÂMICO + ANÁLISE RC")
    print("   White 8ª Ed. (aerodinâmica)  +  Sadraey 2013 (materiais/peso/stall)")
    _exibir_perfis(lista_perfis)
    _exibir_asat()

    _sec("PARÂMETROS DE VOO")
    print("  Velocidade [m/s]  |  Corda [m]  |  Envergadura [m]  |  Peso total [kg]")
    _ex("15  0.6  3.0  28")
    in1=input("  → ")
    n1=[float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+",in1)]
    if len(n1)<4: raise ValueError("Informe 4 valores: velocidade, corda, envergadura, peso.")
    v,c,b,peso_kg=n1[0],n1[1],n1[2],n1[3]

    _sec("SELEÇÃO DE AEROFÓLIOS  (1–3 perfis)")
    _ex("1 5 8   ou   3   ou   2 7")
    in2=input("  → ")
    numeros=[int(x) for x in re.findall(r"\d+",in2)]
    if not (1<=len(numeros)<=3): raise ValueError("Selecione entre 1 e 3 perfis.")
    for n in numeros:
        if not (1<=n<=len(lista_perfis)): raise ValueError(f"Número {n} inválido.")
    seen=[]
    for n in numeros:
        if n not in seen: seen.append(n)
    if len(seen)<len(numeros): print("  [AVISO] Duplicatas removidas.")
    perfis_sel=[lista_perfis[n-1] for n in seen]
    print(f"\n  Perfis selecionados: {', '.join(perfis_sel)}")

    _sec("TIPO DE ASA")
    in3=input("  [1/2/3] → ").strip()
    asat_sel=AsaT.get(in3,"Retangular")
    print(f"  → {asat_sel}")

    _sec("ANÁLISE DE MATERIAIS / PESO / STALL  (Módulo 4 — Sadraey 2013)")
    print("  Incluir tabelas de material/peso/stall nos gráficos? [s/n]")
    ativar=input("  → ").strip().lower() in ("s","sim","y","yes","")

    cfg_mat=None
    if ativar:
        lista_mat=_exibir_materiais()
        print("\n  MODO:")
        print("    [1]  Análise completa  — 1 perfil + 1 material")
        print("         (4 tabelas: Peso | Stall+Desempenho | CD0 | Alertas)")
        print("    [2]  Comparar materiais — todos os materiais, perfil principal")
        print("    [3]  Comparar aerofólios — todos os perfis, 1 material")
        modo=input("  → ").strip() or "1"

        _sec("PARÂMETROS DA MISSÃO RC")
        print(f"  Velocidade cruzeiro [m/s]  (padrão: {v*0.80:.1f}):")
        raw_vc=input("  → ").strip()
        v_cruise=float(raw_vc) if raw_vc else v*0.80

        print(f"  Payload útil [kg]  (padrão: {peso_kg*0.50:.1f}):")
        raw_pl=input("  → ").strip()
        payload=float(raw_pl) if raw_pl else peso_kg*0.50

        print("  Trem de pouso fixo? [s/n]  (padrão: s):")
        com_trem=input("  → ").strip().lower() not in ("n","nao","não")

        cfg_mat={"modo":modo,"v_cruise":v_cruise,"payload":payload,
                 "v_max":v,"com_trem":com_trem,"lista_mat":lista_mat,
                 "perfil_principal":perfis_sel[0]}

        if modo in ("1",""):
            print(f"\n  Material (1–{len(lista_mat)}):")
            im=int(input("  → ").strip() or "1")-1
            cfg_mat["material"]=lista_mat[max(0,min(im,len(lista_mat)-1))]
        elif modo=="3":
            print(f"\n  Material (1–{len(lista_mat)}):")
            im=int(input("  → ").strip() or "1")-1
            cfg_mat["material"]=lista_mat[max(0,min(im,len(lista_mat)-1))]

    _sec("RESUMO")
    S_p=b*c; AR_p=b**2/S_p
    print(f"  V={v} m/s  c={c} m  b={b} m  W={peso_kg} kg")
    print(f"  S={S_p:.3f} m²  AR={AR_p:.2f}")
    print(f"  Perfis: {', '.join(perfis_sel)}  |  Asa: {asat_sel}")
    if cfg_mat:
        mat_n=cfg_mat.get("material","todos")
        print(f"  Módulo 4: modo={cfg_mat['modo']} | material={mat_n} | "
              f"payload={cfg_mat['payload']:.1f} kg | V_cruise={cfg_mat['v_cruise']:.1f} m/s")
    _L()
    return v,c,b,peso_kg,perfis_sel,asat_sel,cfg_mat

# ================================================================= #
# HELPERS DE COR (semáforo Sadraey §4.5)                            #
# ================================================================= #
def _cor_margem(m):
    return "#d4edda" if m>=0.30 else "#fff3cd" if m>=0.15 else "#f8d7da"
def _cor_ld(ld):
    return "#d4edda" if ld>=10 else "#fff3cd" if ld>=6 else "#f8d7da"
def _cor_cl_ratio(r):
    return "#d4edda" if r<=0.70 else "#fff3cd" if r<=0.90 else "#f8d7da"
def _flag(m):
    return "✅" if m>=0.30 else "⚠️" if m>=0.15 else "❌"

# ================================================================= #
# CÁLCULO MÓDULO 4                                                   #
# ================================================================= #
def _calcular_mod4(cfg_mat,c,b):
    perfil=cfg_mat["perfil_principal"]; payload=cfg_mat["payload"]
    v_max=cfg_mat["v_max"]; v_cruise=cfg_mat["v_cruise"]
    com_trem=cfg_mat["com_trem"]; modo=cfg_mat["modo"]
    lista_mat=cfg_mat["lista_mat"]
    S=b*c; AR=b**2/S
    base={"modo":modo,"S":S,"AR":AR,"perfil":perfil,
          "v_cruise":v_cruise,"v_max":v_max,"payload":payload,"com_trem":com_trem}

    if modo in ("1",""):
        mat=cfg_mat["material"]
        comps=estimar_componentes(payload,mat); mtow=comps["_mtow"]
        W_vaz=comps["_peso_vazio"]; f_est=comps["_frac_estrutura"]
        W_asa=peso_asa_material(S,mat)
        cl3=cl_max_asa_finita(perfil,AR); cl2d=CL_MAX_2D.get(perfil,1.5)
        vs=velocidade_stall(mtow,S,cl3)
        mg_c=(v_cruise/vs)-1.0; mg_vm=(v_max/vs)-1.0
        cl_c=(2*mtow*9.81)/(1.225*v_cruise**2*S)
        cl_vm=(2*mtow*9.81)/(1.225*v_max**2*S)
        vels=np.linspace(max(vs*0.90,4.0),v_max*1.30,80)
        pf=polar_e_desempenho(mtow,S,AR,vels,perfil,mat,c,b,com_trem)
        cd0d=cd0_total(perfil,mat,S,c,b,com_trem)
        def iv(arr,vt): return float(np.interp(vt,vels,arr))
        base.update({"material":mat,"comps":comps,"mtow":mtow,
            "W_vazio":W_vaz,"f_est":f_est,"W_asa":W_asa,
            "cl_max_3d":cl3,"cl_max_2d":cl2d,"v_stall":vs,
            "mg_cruise":mg_c,"mg_vmax":mg_vm,"cl_cruise":cl_c,"cl_vmax":cl_vm,
            "LD_cruise":iv(pf["L/D"],v_cruise),"LD_vmax":iv(pf["L/D"],v_max),
            "D_cruise":iv(pf["D_N"],v_cruise),"D_vmax":iv(pf["D_N"],v_max),
            "P_cruise":iv(pf["P_W"],v_cruise),"P_vmax":iv(pf["P_W"],v_max),
            "V_LD_max":pf["V_LD_max"],"LD_max":pf["LD_max"],
            "perf":pf,"vels":vels,"cd0d":cd0d})

    elif modo=="2":
        linhas=[]
        for mat in lista_mat:
            if mat not in MATERIAIS: continue
            comps=estimar_componentes(payload,mat); mt=comps["_mtow"]; wv=comps["_peso_vazio"]
            cl3=cl_max_asa_finita(perfil,AR); vs=velocidade_stall(mt,S,cl3)
            mg=(v_cruise/vs)-1.0; vp=np.array([v_cruise,v_max])
            pf=polar_e_desempenho(mt,S,AR,vp,perfil,mat,c,b,com_trem)
            linhas.append({"mat":mat,"mtow":mt,"W_vazio":wv,"v_stall":vs,
                           "mg_cruise":mg,"LD_cruise":float(pf["L/D"][0]),
                           "P_vmax":float(pf["P_W"][1]),"CD0":pf["CD0"]})
        base["linhas"]=linhas

    elif modo=="3":
        mat=cfg_mat["material"]
        comps=estimar_componentes(payload,mat); mtow=comps["_mtow"]
        linhas=[]
        for perf in CL_MAX_2D:
            cl2d=CL_MAX_2D[perf]; cl3d=cl_max_asa_finita(perf,AR)
            vs=velocidade_stall(mtow,S,cl3d)
            cl_cr=(2*mtow*9.81)/(1.225*v_cruise**2*S)
            mg=(v_cruise/vs)-1.0; e_osw=eficiencia_oswald(AR)
            cd0_p=CD0_PERFIL.get(perf,0.010)
            cl_ld=np.sqrt(np.pi*AR*e_osw*cd0_p); ld_mx=cl_ld/(2.0*cd0_p)
            linhas.append({"perfil":perf,"cl2d":cl2d,"cl3d":cl3d,"v_stall":vs,
                           "cl_req":cl_cr,"mg_cruise":mg,"LD_max":ld_mx,"cd0_perf":cd0_p})
        base.update({"material":mat,"mtow":mtow,"linhas":linhas})
    return base

# ================================================================= #
# TABELAS PLOTLY — MODO 1                                            #
# ================================================================= #
def _tab_peso(d4):
    mat=d4["material"]; comps=d4["comps"]; mtow=d4["mtow"]; frac=fracoes_peso(mat)
    mi=MATERIAIS[mat]
    nomes,fracs_txt,pesos_txt,fill=[],[],[],[]
    for comp,peso in comps.items():
        if comp.startswith("_"): continue
        f=frac.get(comp,0.0)
        nomes.append(comp.capitalize()); fracs_txt.append(f"{f*100:.1f}%")
        pesos_txt.append(f"{peso:.3f} kg"); fill.append("white")
    nomes.append("<b>MTOW</b>"); fracs_txt.append("<b>100.0%</b>")
    pesos_txt.append(f"<b>{mtow:.3f} kg</b>"); fill.append("#dbe9ff")
    sub=(f"{mat} | ρ={mi['densidade_kg_m3']} kg/m³ | e={mi['espessura_mm']} mm | "
         f"fc={mi['fator_construcao']:.2f} | ΔCd0={mi['cd0_rugosidade']:.4f}")
    return go.Table(
        columnwidth=[2.2,1.0,1.0],
        header=dict(values=[f"<b>📦 Peso — Sadraey Cap. 6</b><br><sub>{sub}</sub>",
                            "<b>Fração</b>","<b>Peso</b>"],
                    fill_color="#2c3e50",font=dict(color="white",size=11),
                    align=["left","center","center"],height=40),
        cells=dict(values=[nomes,fracs_txt,pesos_txt],
                   fill_color=[fill,fill,fill],
                   font=dict(size=10),align=["left","center","center"],height=22))

def _tab_stall(d4):
    vc=d4["v_cruise"]; vm=d4["v_max"]
    vs=d4["v_stall"]; cl3=d4["cl_max_3d"]; cl2=d4["cl_max_2d"]
    mg_c=d4["mg_cruise"]; mg_v=d4["mg_vmax"]
    cl_c=d4["cl_cruise"]; cl_v=d4["cl_vmax"]
    ld_c=d4["LD_cruise"]; ld_v=d4["LD_vmax"]
    d_c=d4["D_cruise"]; d_v=d4["D_vmax"]
    p_c=d4["P_cruise"]; p_v=d4["P_vmax"]
    params=["V_stall","CL_max  2D / 3D",
            f"CL_req  @  {vc:.0f} m/s",f"CL_req  @  {vm:.0f} m/s",
            f"Margem stall  @  {vc:.0f} m/s",f"Margem stall  @  {vm:.0f} m/s",
            f"L/D  @  {vc:.0f} m/s",f"L/D  @  {vm:.0f} m/s",
            f"Arrasto  @  {vc:.0f} m/s",f"Arrasto  @  {vm:.0f} m/s",
            f"Potência  @  {vc:.0f} m/s",f"Potência  @  {vm:.0f} m/s",
            "V_(L/D)_max","(L/D)_max analítico"]
    valores=[f"{vs:.2f} m/s",f"{cl2:.3f}  /  {cl3:.3f}",
             f"{cl_c:.4f}  ({cl_c/cl3*100:.0f}% CLmax)",
             f"{cl_v:.4f}  ({cl_v/cl3*100:.0f}% CLmax)",
             f"{_flag(mg_c)}  {mg_c*100:.1f}%",f"{_flag(mg_v)}  {mg_v*100:.1f}%",
             f"{ld_c:.2f}",f"{ld_v:.2f}",
             f"{d_c:.1f} N",f"{d_v:.1f} N",
             f"{p_c:.0f} W",f"{p_v:.0f} W",
             f"{d4['V_LD_max']:.2f} m/s",f"{d4['LD_max']:.2f}"]
    cores=["white","white",
           _cor_cl_ratio(cl_c/cl3),_cor_cl_ratio(cl_v/cl3),
           _cor_margem(mg_c),_cor_margem(mg_v),
           _cor_ld(ld_c),_cor_ld(ld_v),
           "white","white","white","white","#dbe9ff","#dbe9ff"]
    return go.Table(
        columnwidth=[2.4,2.0],
        header=dict(values=["<b>✈️  Parâmetro — Sadraey §4.5 + Cap. 5</b>","<b>Valor</b>"],
                    fill_color="#1a5276",font=dict(color="white",size=11),
                    align=["left","center"],height=36),
        cells=dict(values=[params,valores],fill_color=[cores,cores],
                   font=dict(size=10),align=["left","center"],height=22))

def _tab_cd0(d4):
    cd0d=d4["cd0d"]; total=cd0d["cd0_total"]
    NOMES_PT={"cd0_perfil":"Perfil (asa limpa)","cd0_rugosidade":"Rugosidade do material",
              "cd0_fuselagem":"Fuselagem caixa","cd0_trem":"Trem de pouso fixo",
              "cd0_empenagem":"Empenagem (H+V)","cd0_interferencia":"Interferência asa-fus."}
    nomes,vals,pcts,cores=[],[],[],[]
    for k,v in cd0d.items():
        if k=="cd0_total": continue
        nomes.append(NOMES_PT.get(k,k)); vals.append(f"{v:.5f}"); pcts.append(f"{v/total*100:.1f}%")
        frac=v/total; g=int(255-120*frac); bl=int(220-120*frac)
        cores.append(f"rgb(255,{max(g,135)},{max(bl,100)})")
    nomes.append("<b>CD0 TOTAL</b>"); vals.append(f"<b>{total:.5f}</b>")
    pcts.append("<b>100.0%</b>"); cores.append("#dbe9ff")
    return go.Table(
        columnwidth=[2.2,1.0,0.8],
        header=dict(values=["<b>🌊 Componente de CD0 — Sadraey §3.5–3.6</b>",
                            "<b>Valor</b>","<b>%</b>"],
                    fill_color="#154360",font=dict(color="white",size=11),
                    align=["left","center","center"],height=36),
        cells=dict(values=[nomes,vals,pcts],fill_color=[cores,cores,cores],
                   font=dict(size=10),align=["left","center","center"],height=22))

def _tab_alertas(d4):
    mg_c=d4["mg_cruise"]; cl_c=d4["cl_cruise"]; cl3=d4["cl_max_3d"]
    ld_c=d4["LD_cruise"]; p_vm=d4["P_vmax"]; mtow=d4["mtow"]
    W_as=d4["W_asa"]; comps=d4["comps"]
    rows=[]
    # MTOW
    rows.append(("✅ MTOW dentro do limite",f"{mtow:.1f} kg ≤ 25 kg.","#d4edda") if mtow<=25
                else ("❌ MTOW > 25 kg",f"{mtow:.1f} kg — verificar ANAC/DECEA.","#f8d7da"))
    # stall
    if mg_c<0.15:   rows.append(("❌ Stall CRÍTICO (cruzeiro)",f"Margem={mg_c*100:.0f}% — risco real.","#f8d7da"))
    elif mg_c<0.30: rows.append(("⚠️ Stall baixo",f"Margem={mg_c*100:.0f}% < 30% (Sadraey §4.5).","#fff3cd"))
    else:           rows.append(("✅ Margem de stall OK",f"Margem={mg_c*100:.0f}% ≥ 30%.","#d4edda"))
    # CL ratio
    r=cl_c/max(cl3,0.001)
    if r>0.90:   rows.append(("❌ CL_cruise > 90% CL_max","Risco iminente de stall.","#f8d7da"))
    elif r>0.75: rows.append(("⚠️ CL_cruise > 75% CL_max","Manobras limitadas.","#fff3cd"))
    else:        rows.append(("✅ CL_cruise adequado",f"{r*100:.0f}% do CL_max.","#d4edda"))
    # L/D
    if ld_c<6:    rows.append(("❌ L/D crítico",f"L/D={ld_c:.1f} — eficiência muito baixa.","#f8d7da"))
    elif ld_c<10: rows.append(("⚠️ L/D moderado",f"L/D={ld_c:.1f} — pode comprometer autonomia.","#fff3cd"))
    else:         rows.append(("✅ L/D bom",f"L/D={ld_c:.1f}.","#d4edda"))
    # Potência
    if p_vm>600:   rows.append(("❌ Potência muito alta",f"{p_vm:.0f} W — motor de alto Kv necessário.","#f8d7da"))
    elif p_vm>350: rows.append(("⚠️ Potência alta",f"{p_vm:.0f} W — dimensionar bateria com folga.","#fff3cd"))
    else:          rows.append(("✅ Potência OK",f"{p_vm:.0f} W.","#d4edda"))
    # Peso asa físico
    W_f=comps.get("asa",0)
    if W_as>W_f*1.5:
        rows.append(("⚠️ Peso físico da asa excede estimativa",
                     f"Vol.direto={W_as:.2f} kg  vs  fração={W_f:.2f} kg.","#fff3cd"))
    return go.Table(
        columnwidth=[2.1,3.0],
        header=dict(values=["<b>🔔 Diagnóstico</b>","<b>Detalhe</b>"],
                    fill_color="#4a235a",font=dict(color="white",size=11),
                    align="left",height=36),
        cells=dict(values=[[r[0] for r in rows],[r[1] for r in rows]],
                   fill_color=[[r[2] for r in rows],[r[2] for r in rows]],
                   font=dict(size=10),align="left",height=24))

# ================================================================= #
# TABELAS MODOS 2 E 3                                                #
# ================================================================= #
def _tab_comp_materiais(d4):
    linhas=d4["linhas"]
    mats,mtow_l,wv_l,vs_l,mg_l,ld_l,pw_l,cd0_l=[],[],[],[],[],[],[],[]
    mg_cores=[]
    for L in linhas:
        mats.append(L["mat"]); mtow_l.append(f"{L['mtow']:.1f}")
        wv_l.append(f"{L['W_vazio']:.1f}"); vs_l.append(f"{L['v_stall']:.2f}")
        mg_l.append(f"{_flag(L['mg_cruise'])}  {L['mg_cruise']*100:.1f}%")
        ld_l.append(f"{L['LD_cruise']:.1f}"); pw_l.append(f"{L['P_vmax']:.0f}")
        cd0_l.append(f"{L['CD0']:.5f}"); mg_cores.append(_cor_margem(L["mg_cruise"]))
    n=len(mats); white=["white"]*n
    return go.Table(
        columnwidth=[2.8,1.0,1.0,1.0,1.5,1.0,1.0,1.2],
        header=dict(
            values=[f"<b>📊 Material</b><br><sub>Perfil: {d4['perfil']} | "
                    f"Payload: {d4['payload']:.0f} kg | AR={d4['AR']:.1f} | "
                    f"V_cruise={d4['v_cruise']:.0f} m/s</sub>",
                    "<b>MTOW (kg)</b>","<b>W_vazio</b>","<b>V_stall</b>",
                    "<b>Margem Stall</b>","<b>L/D cruise</b>",
                    "<b>P_max (W)</b>","<b>CD0 total</b>"],
            fill_color="#1e8449",font=dict(color="white",size=10),
            align=["left"]+["center"]*7,height=40),
        cells=dict(values=[mats,mtow_l,wv_l,vs_l,mg_l,ld_l,pw_l,cd0_l],
                   fill_color=[white,white,white,white,mg_cores,white,white,white],
                   font=dict(size=10),align=["left"]+["center"]*7,height=22))

def _tab_comp_perfis(d4):
    linhas=d4["linhas"]
    perfs,cl2_l,cl3_l,vs_l,clr_l,mg_l,ld_l,cd0_l=[],[],[],[],[],[],[],[]
    mg_cores,cl_cores=[],[]
    for L in linhas:
        perfs.append(L["perfil"]); cl2_l.append(f"{L['cl2d']:.3f}")
        cl3_l.append(f"{L['cl3d']:.3f}"); vs_l.append(f"{L['v_stall']:.2f}")
        clr_l.append(f"{L['cl_req']:.4f}")
        mg_l.append(f"{_flag(L['mg_cruise'])}  {L['mg_cruise']*100:.1f}%")
        ld_l.append(f"{L['LD_max']:.1f}"); cd0_l.append(f"{L['cd0_perf']:.5f}")
        mg_cores.append(_cor_margem(L["mg_cruise"]))
        cl_cores.append(_cor_cl_ratio(L["cl_req"]/max(L["cl3d"],0.001)))
    n=len(perfs); white=["white"]*n
    return go.Table(
        columnwidth=[2.8,1.0,1.0,1.0,1.2,1.5,1.0,1.2],
        header=dict(
            values=[f"<b>📊 Aerofólio</b><br><sub>Material: {d4['material']} | "
                    f"MTOW: {d4['mtow']:.1f} kg | AR={d4['AR']:.1f} | "
                    f"V_cruise={d4['v_cruise']:.0f} m/s</sub>",
                    "<b>CLmax 2D</b>","<b>CLmax 3D</b>","<b>V_stall</b>",
                    "<b>CL_req</b>","<b>Margem Stall</b>",
                    "<b>(L/D)max</b>","<b>CD0 perf</b>"],
            fill_color="#6c3483",font=dict(color="white",size=10),
            align=["left"]+["center"]*7,height=40),
        cells=dict(values=[perfs,cl2_l,cl3_l,vs_l,clr_l,mg_l,ld_l,cd0_l],
                   fill_color=[white,white,white,white,cl_cores,mg_cores,white,white],
                   font=dict(size=10),align=["left"]+["center"]*7,height=22))

# ================================================================= #
# FIGURA 2 — TABELAS                                                 #
# ================================================================= #
def _plotar_tabelas_mod4(d4,cfg_mat):
    modo=d4["modo"]
    rodape=("Refs: Sadraey §3.5–3.6 (CD0) · §4.5 (CL_max Eq.4.28, V_stall Eq.4.24) · "
            "Cap.6 (peso Eq.6.1)  |  White §7.3 · §8.3 · §8.4  |  "
            "✅ ≥30%  ⚠️ 15–30%  ❌ <15%  (margem de stall mínima recomendada)")

    if modo in ("1",""):
        fig2=make_subplots(rows=2,cols=2,vertical_spacing=0.07,horizontal_spacing=0.04,
            subplot_titles=("📦 Estimativa de Peso  [Sadraey Cap. 6]",
                            "✈️  Stall & Desempenho  [Sadraey §4.5 + Cap. 5]",
                            "🌊 Decomposição de CD0  [Sadraey §3.5–3.6]",
                            "🔔 Diagnósticos & Alertas"),
            specs=[[{"type":"table"},{"type":"table"}],[{"type":"table"},{"type":"table"}]])
        fig2.add_trace(_tab_peso(d4),row=1,col=1)
        fig2.add_trace(_tab_stall(d4),row=1,col=2)
        fig2.add_trace(_tab_cd0(d4),row=2,col=1)
        fig2.add_trace(_tab_alertas(d4),row=2,col=2)
        altura=940
        titulo=(f"AsalabXYZ | Módulo 4 — Materiais · Peso · Stall  |  "
                f"Perfil: <b>{d4['perfil']}</b>  |  Material: <b>{d4['material']}</b>  |  "
                f"Payload: {d4['payload']:.0f} kg  |  V_cruise: {d4['v_cruise']:.0f} m/s")
    elif modo=="2":
        fig2=make_subplots(rows=1,cols=1,
            subplot_titles=(f"📊 Comparação de Materiais — Perfil: {d4['perfil']} | "
                            f"Payload: {d4['payload']:.0f} kg | AR={d4['AR']:.1f}  "
                            "[Sadraey Cap. 6 + §4.5]",),
            specs=[[{"type":"table"}]])
        fig2.add_trace(_tab_comp_materiais(d4),row=1,col=1)
        altura=140+26*len(d4["linhas"])
        titulo="AsalabXYZ | Módulo 4 — Comparação de Materiais"
    else:
        fig2=make_subplots(rows=1,cols=1,
            subplot_titles=(f"📊 Comparação de Aerofólios — Material: {d4['material']} | "
                            f"MTOW: {d4['mtow']:.1f} kg | AR={d4['AR']:.1f}  [Sadraey §4.5]",),
            specs=[[{"type":"table"}]])
        fig2.add_trace(_tab_comp_perfis(d4),row=1,col=1)
        altura=140+26*len(d4["linhas"])
        titulo="AsalabXYZ | Módulo 4 — Comparação de Aerofólios"

    fig2.update_layout(height=altura+60,width=1400,template="plotly_white",
        margin=dict(t=90,b=70,l=30,r=30),
        title=dict(text=titulo,x=0.5,font=dict(size=14)))
    fig2.add_annotation(xref="paper",yref="paper",x=0.5,y=-0.07,text=rodape,
        showarrow=False,font=dict(size=9,color="#555"),
        bgcolor="rgba(255,255,255,0.88)",bordercolor="#aaa",borderwidth=1,borderpad=8)
    fig2.show()

# ================================================================= #
# FIGURA 1 — GRÁFICOS AERODINÂMICOS (original intacto)              #
# ================================================================= #
def plotar_resultados(dados,cfg_mat=None):
    v=dados["v"]; c=dados["c"]; b=dados["b"]; peso_kg=dados["peso_kg"]
    S=dados["S"]; AR=dados["AR"]; re_real=dados["re_real"]; cl_req=dados["cl_req"]
    e_oswald=dados["e_oswald"]; kappa=dados["kappa"]; x_tr_pct=dados["x_tr_pct"]
    Ma_info=dados["Ma_info"]; alphas=dados["alphas"]; asat_sel=dados["asat_sel"]
    perfis_sel=dados["perfis_sel"]; resultados=dados["resultados"]
    n_perfis=len(perfis_sel)

    fig=make_subplots(rows=2,cols=3,vertical_spacing=0.18,horizontal_spacing=0.10,
        subplot_titles=("<b>Sustentação (CL)</b>","<b>Arrasto (CD)</b>","<b>Eficiência (L/D)</b>",
                        "<b>Coef. de Momento (Cm) — White §8.1</b>",
                        "<b>Centro de Pressão (XCp) — White §8.1</b>",
                        f"<b>AsaT — {asat_sel}</b>"))

    footer=(f"<b>Peso: {peso_kg} kg | CL_req: {cl_req:.4f} | Re: {re_real:.0f} | "
            f"Ma: {Ma_info:.3f} | AsaT: {asat_sel} (κ={kappa:.2f})</b><br>"
            f"<b>Envergadura: {b:.2f} m | Corda: {c:.2f} m | S: {S:.3f} m² | "
            f"AR: {AR:.2f} | e_Oswald: {e_oswald:.3f}</b><br>"
            f"<b>Transição lam→turb: {x_tr_pct:.1f}% da corda (critério de Michel, White §7.4)</b><br>")

    for idx,perfil in enumerate(perfis_sel):
        r=resultados[perfil]
        cl_asa=r["cl_asa"]; cd_tot=r["cd_tot"]; eff=r["eff"]; ld_max=r["ld_max"]
        alpha_stall=r["alpha_stall"]; a0_2d=r["a0_2d"]; a0_2d_raw=r["a0_2d_raw"]
        cm_asa=r["cm_asa"]; xcp_asa=r["xcp_asa"]; cm0_2d=r["cm0_2d"]
        footer+=(f"<b>{perfil}:</b> (L/D)_max={ld_max:.2f} analít. / {np.max(eff):.2f} numérico "
                 f"(α={alphas[np.argmax(eff)]:.1f}°) | α_estol≈{alpha_stall:.1f}° | "
                 f"PG: a0={a0_2d:.4f} (raw={a0_2d_raw:.4f}) | Cm0={cm0_2d:.4f}<br>")
        cor=CORES[idx]; dash=DASHES[idx]; dash_stall=dict(color=cor,width=1.2,dash="dashdot")
        label=f"[{idx+1}] {perfil}" if n_perfis>1 else perfil

        fig.add_trace(go.Scatter(x=alphas,y=cl_asa,name=label,
            line=dict(color=cor,width=2.5,dash=dash)),row=1,col=1)
        fig.add_trace(go.Scatter(x=[alpha_stall,alpha_stall],y=[-0.5,2.0],
            mode="lines",showlegend=False,line=dash_stall),row=1,col=1)
        fig.add_trace(go.Scatter(x=alphas,y=cd_tot,showlegend=False,
            line=dict(color=cor,width=2.5,dash=dash)),row=1,col=2)
        fig.add_trace(go.Scatter(x=alphas,y=eff,showlegend=False,
            line=dict(color=cor,width=2.5,dash=dash)),row=1,col=3)
        if idx==n_perfis-1:
            fig.add_annotation(xref="x3",yref="y3",x=alphas[np.argmax(eff)],y=np.max(eff),
                text="(L/D)_max",showarrow=True,arrowhead=2,font=dict(size=10))
        fig.add_trace(go.Scatter(x=alphas,y=cm_asa,showlegend=False,
            line=dict(color=cor,width=2.5,dash=dash)),row=2,col=1)
        fig.add_trace(go.Scatter(x=[-6,16],y=[0,0],mode="lines",showlegend=False,
            line=dict(color="gray",width=1,dash="dot")),row=2,col=1)
        fig.add_trace(go.Scatter(x=[alpha_stall,alpha_stall],y=[-0.5,0.3],
            mode="lines",showlegend=False,line=dash_stall),row=2,col=1)
        xcp_plot=np.where(cl_asa>0.05,xcp_asa,np.nan)
        fig.add_trace(go.Scatter(x=alphas,y=xcp_plot,showlegend=False,
            line=dict(color=cor,width=2.5,dash=dash)),row=2,col=2)
        for yref in [0.25,0.50]:
            fig.add_trace(go.Scatter(x=[-6,16],y=[yref,yref],mode="lines",showlegend=False,
                line=dict(color="lightgray",width=1,dash="dot")),row=2,col=2)

    fig.add_trace(go.Scatter(x=[-6,16],y=[cl_req,cl_req],mode="lines",name="CL req.",
        line=dict(color="black",dash="dash",width=1.5)),row=1,col=1)
    xs_pf,ys_pf=gerar_silhueta_asat(asat_sel,b,c)
    fig.add_trace(go.Scatter(x=xs_pf,y=ys_pf,fill="toself",
        fillcolor="rgba(30,80,180,0.25)",line=dict(color="navy",width=2),
        showlegend=False),row=2,col=3)
    fig.add_annotation(x=b/4,y=c*1.08,text=f"b={b:.2f} m | c={c:.2f} m | AR={AR:.2f}",
        showarrow=False,font=dict(size=10),row=2,col=3)
    if n_perfis>1:
        leg_txt="<br>".join(
            f"<span style='color:{CORES[i]}'><b>[{i+1}]</b></span> {p}"
            for i,p in enumerate(perfis_sel))
        fig.add_annotation(xref="paper",yref="paper",x=0.72,y=0.02,text=leg_txt,
            showarrow=False,align="left",bgcolor="rgba(255,255,255,0.85)",
            bordercolor="gray",borderwidth=1,borderpad=6,font=dict(size=9))
    for col,yref,lt in [(1,0.0,"Cm=0"),(2,0.25,"c/4"),(2,0.50,"c/2")]:
        fig.add_annotation(xref=f"x{col+3}",yref=f"y{col+3}",x=15.5,y=yref,
            text=lt,showarrow=False,font=dict(size=8,color="gray"))

    fig.update_layout(height=1100,width=1400,template="plotly_white",
        margin=dict(t=100,b=360,l=80,r=80),
        title=dict(text=(f"AsalabXYZ | AsaT: <b>{asat_sel}</b> | "
                         f"{n_perfis} perfil{'is' if n_perfis>1 else ''} | "
                         "<i>Fluid Mechanics — White 8ª Ed.</i>"),
                   x=0.5,font=dict(size=16)),
        legend=dict(orientation="h",yanchor="bottom",y=1.02,
                    xanchor="right",x=1,font=dict(size=10)))
    fig.add_annotation(xref="paper",yref="paper",x=0.5,y=-0.32,text=footer,
        showarrow=False,align="left",bgcolor="rgba(255,255,255,0.9)",
        bordercolor="black",borderwidth=1,borderpad=12)
    for col in [1,2,3]:
        fig.update_xaxes(title_text="α [°]",row=1,col=col)
        fig.update_xaxes(title_text="α [°]",row=2,col=col)
    fig.update_yaxes(title_text="CL",row=1,col=1); fig.update_yaxes(title_text="CD",row=1,col=2)
    fig.update_yaxes(title_text="L/D",row=1,col=3); fig.update_yaxes(title_text="Cm",row=2,col=1)
    fig.update_yaxes(title_text="XCp (x/c)",row=2,col=2,autorange="reversed")
    fig.update_xaxes(title_text="y — semi-envergadura [m]",row=2,col=3)
    fig.update_yaxes(title_text="x — corda [m]",row=2,col=3)
    fig.show()

    # Figura 2 — tabelas Módulo 4
    if cfg_mat is not None:
        print("\n  [Módulo 4] Calculando materiais/peso/stall...")
        d4=_calcular_mod4(cfg_mat,c,b)
        _plotar_tabelas_mod4(d4,cfg_mat)

# ================================================================= #
# PONTO DE ENTRADA                                                   #
# ================================================================= #
def simular_asa_aerodinamica():
    try:
        v,c,b,peso_kg,perfis_sel,asat_sel,cfg_mat=coletar_inputs()
        dados=calcular_asa(v,c,b,peso_kg,perfis_sel,asat_sel)
        plotar_resultados(dados,cfg_mat)
    except Exception as err:
        print(f"\n[ERRO]: {err}")
        import traceback; traceback.print_exc()

if __name__=="__main__":
    simular_asa_aerodinamica()

# ================================================================= #
# REFERÊNCIAS                                                        #
# White §7.3 (rugosidade) §7.4 (Michel) §8.1 (NACA,XCp) §8.3 (polar)
# §8.4 (Lifting Line) §8.7 (Prandtl-Glauert) §8.8 (delta)           #
# Sadraey §3.5–3.6 (CD0) §4.5 (CL_max,V_stall) Cap.5 Cap.6 (peso)  #
# Raymer 5ª Ed. 2012  |  Abbott & von Doenhoff, 1959                 #
# ================================================================= #
