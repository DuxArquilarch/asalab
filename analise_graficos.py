# ================================================================= #
# AsalabXYZ — MÓDULO 3: ANÁLISE E GRÁFICOS AERODINÂMICOS            #
#                                                                    #
# Figura 1 (sempre): layout 2×3 aerodinâmico — CL, CD, L/D, Cm,    #
# XCp e silhueta da asa.                                             #
#                                                                    #
# White, F.M. Fluid Mechanics, 8ª Ed., 2016                         #
# ================================================================= #

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from calculos import calcular_asa


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
# FIGURA 1 — GRÁFICOS AERODINÂMICOS                                  #
# ================================================================= #
def plotar_resultados(dados, cfg_mat=None):
    """
    Gera a Figura 1 (layout 2×3) com CL, CD, L/D, Cm, XCp e silhueta.
    O argumento cfg_mat é mantido apenas para retrocompatibilidade
    (não produz mais tabelas de materiais/peso/stall).
    """
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


# ================================================================= #
# REFERÊNCIAS                                                        #
# White §7.3 (rugosidade) §7.4 (Michel) §8.1 (NACA,XCp) §8.3 (polar)
# §8.4 (Lifting Line) §8.7 (Prandtl-Glauert) §8.8 (delta)           #
# ================================================================= #