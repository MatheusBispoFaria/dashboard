import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime

# 1. Configuração da Página
st.set_page_config(page_title="Dashboard Obras - Final", layout="wide", initial_sidebar_state="expanded")

# 2. Injeção de CSS Customizado (Responsivo Light/Dark Mode)
custom_css = """
<style>
    /* Usando variáveis nativas (var) para adaptar automaticamente ao tema claro ou escuro */
    div[data-testid="metric-container"] { 
        background-color: var(--secondary-background-color); 
        border: 1px solid rgba(128, 128, 128, 0.2); 
        padding: 20px 25px; 
        border-radius: 12px; 
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1); 
        transition: transform 0.2s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
    }
    div[data-testid="stMetricLabel"] { font-weight: 600; font-size: 0.9rem; }
    div[data-testid="stMetricValue"] { font-size: 2rem; font-weight: 700; }
    
    .stPlotlyChart { 
        border-radius: 12px; 
        background-color: var(--secondary-background-color); 
        padding: 10px; 
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1); 
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# 3. Carregamento e Tratamento de Dados
@st.cache_data
def load_data():
    df_p, df_d = None, None
    try:
        df_p = pd.read_csv('dados_produtividade_construcao.csv')
        df_p['CREATED'] = pd.to_datetime(df_p['CREATED'], errors='coerce')
    except Exception as e:
        st.sidebar.warning(f"Aviso CSV: {e}")
        
    try:
        df_d = pd.read_excel('df_diarios.xlsx')
        df_d['data'] = pd.to_datetime(df_d['data'], errors='coerce')
        if 'nome_obra' in df_d.columns:
            df_d['nome_obra'] = df_d['nome_obra'].astype(str).str.replace('_', ' ').str.title()
    except Exception as e:
        st.sidebar.warning(f"Aviso Excel: {e}")
        
    return df_p, df_d

df_prod, df_diarios = load_data()

# ==========================================
# SANITIZAÇÃO DE DADOS (ETL)
# ==========================================
obras_validas = ['Obra A', 'Obra B', 'Obra C']

if df_diarios is not None and not df_diarios.empty:
    df_diarios = df_diarios[df_diarios['nome_obra'].isin(obras_validas)].copy()

if df_prod is not None and not df_prod.empty:
    pass 

def get_mode(x):
    m = x.mode()
    return m.iloc[0] if not m.empty else np.nan

# 4. Construção da Interface Principal
st.title("Dashboard Integrado de Produtividade e Insumos")
st.markdown("Análise de desempenho e consumo de recursos nos canteiros de obra.")

df_diarios_mo = pd.DataFrame()
df_d_obra = pd.DataFrame()
df_p_obra = pd.DataFrame()

if df_diarios is not None and not df_diarios.empty:
    if 'tipo_insumo' in df_diarios.columns:
        tipo_limpo = df_diarios['tipo_insumo'].astype(str).str.strip().str.upper()
        filtro_mo = tipo_limpo.str.contains('MÃO DE OBRA|MAO DE OBRA', na=False, regex=True)
        df_diarios_mo = df_diarios[filtro_mo].copy()
    else:
        df_diarios_mo = df_diarios.copy()

# --- FILTROS DA BARRA LATERAL ---
st.sidebar.header("Filtros de Análise")

if df_prod is not None and not df_prod.empty and 'OBRA' in df_prod.columns:
    obras_disp = sorted(df_prod['OBRA'].dropna().unique())
elif not df_diarios_mo.empty and 'nome_obra' in df_diarios_mo.columns:
    obras_disp = sorted(df_diarios_mo['nome_obra'].dropna().unique())
else:
    obras_disp = []

if obras_disp:
    obra_sel = st.sidebar.selectbox("Selecione a Obra alvo:", obras_disp)
    nome_obra_padrao = obra_sel.replace('_', ' ').title()
    
    if df_prod is not None and not df_prod.empty:
        df_p_obra = df_prod[df_prod['OBRA'] == obra_sel]
    if not df_diarios_mo.empty:
        df_d_obra = df_diarios_mo[df_diarios_mo['nome_obra'] == nome_obra_padrao]

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Auditoria de Dados")
    remover_outliers = st.sidebar.checkbox("📉 Remover Picos Irreais (Outliers)")
    st.sidebar.markdown("---")

    if remover_outliers and not df_p_obra.empty and 'IP_D' in df_p_obra.columns:
        Q1 = df_p_obra['IP_D'].quantile(0.25)
        Q3 = df_p_obra['IP_D'].quantile(0.75)
        IQR = Q3 - Q1
        limite_superior = Q3 + 1.5 * IQR
        df_p_obra = df_p_obra[df_p_obra['IP_D'] <= limite_superior]
        st.warning(f"⚠️ Filtro Ativo: IPs > {limite_superior:.2f} removidos.")

    # --- MÉTRICAS ---
    c1, c2, c3 = st.columns(3)
    ip_medio = df_p_obra['IP_D'].mean() if not df_p_obra.empty and 'IP_D' in df_p_obra.columns else 0
    meta_siurb = df_p_obra['COEF_SIURB'].mean() if not df_p_obra.empty and 'COEF_SIURB' in df_p_obra.columns else 0
    qtd_registros = len(df_d_obra) if not df_d_obra.empty else 0
    
    c1.metric("Índice de Produtividade (IP) Médio", f"{ip_medio:.2f}")
    c2.metric("Meta do Orçamento (SIURB)", f"{meta_siurb:.2f}")
    c3.metric("Registros Diários (Mão de Obra)", qtd_registros)
    st.divider()

    # --- GRÁFICOS ---
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Distribuição da Produtividade (Boxplot)")
        if not df_p_obra.empty and 'IP_D' in df_p_obra.columns:
            # ATUALIZAÇÃO: template="plotly_white" foi removido para herdar o Dark Mode
            fig1 = px.box(
                df_p_obra, 
                x='CLASSE_COMP', 
                y='IP_D', 
                color='CLASSE_COMP', 
                points="outliers", 
                labels={'CLASSE_COMP': 'Classe de Serviço', 'IP_D': 'Índice de Produtividade (IP)'}
            )
            
            fig1.update_layout(
                showlegend=False, 
                margin=dict(l=40, r=20, t=30, b=80), 
                height=450, 
                xaxis_tickangle=-45 
            )
            # theme="streamlit" faz com que o Plotly respeite o botão de claro/escuro nativo
            st.plotly_chart(fig1, use_container_width=True, theme="streamlit")
        else:
            st.info("Sem dados de produtividade (CSV) para gerar o Boxplot.")
            
    with col_b:
        st.subheader("Consumo de Mão de Obra (Horas)")
        if not df_d_obra.empty and 'insumo' in df_d_obra.columns and 'qntd' in df_d_obra.columns:
            df_insumo = df_d_obra.groupby('insumo', as_index=False)['qntd'].sum().sort_values('qntd', ascending=False)
            
            # ATUALIZAÇÃO: template="plotly_white" removido
            fig2 = px.bar(df_insumo, x='insumo', y='qntd', color='insumo')
            fig2.update_layout(showlegend=False, xaxis_tickangle=-45)
            st.plotly_chart(fig2, use_container_width=True, theme="streamlit")
        else:
            st.info("Sem dados de diários (Excel) para gerar o gráfico de barras.")
    st.divider()

    # --- INTELIGÊNCIA ANALÍTICA ---
    st.subheader("Inteligência Analítica e Consistência Global")
    aba1, aba2 = st.tabs(["📊 Comparativo por Obra", "📅 Sazonalidade (Dias da Semana)"])

    with aba1:
        if not df_diarios_mo.empty and 'ip_d' in df_diarios_mo.columns:
            obra_stats = df_diarios_mo.dropna(subset=['nome_obra']).groupby('nome_obra')['ip_d'].agg(
                Média='mean',
                Mediana='median',
                Moda=get_mode,
                Variância='var',
                Desvio_Padrão='std',
                Amplitude=lambda x: x.max() - x.min()
            ).reset_index()
            
            obra_stats['CV (%)'] = (obra_stats['Desvio_Padrão'] / obra_stats['Média']) * 100
            obra_stats = obra_stats.sort_values('Mediana', ascending=False)
            
            st.dataframe(
                obra_stats,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Média": st.column_config.NumberColumn(format="%.2f"),
                    "Mediana": st.column_config.NumberColumn(format="%.2f"),
                    "Moda": st.column_config.NumberColumn(format="%.2f"),
                    "Variância": st.column_config.NumberColumn(format="%.2f"),
                    "Desvio_Padrão": st.column_config.NumberColumn(format="%.2f"),
                    "Amplitude": st.column_config.NumberColumn(format="%.2f"),
                    "CV (%)": st.column_config.NumberColumn("CV (%) - Risco", format="%.2f %%")
                }
            )
        else:
            st.info("Dados de Diários insuficientes para o Comparativo.")

    with aba2:
        obra_alvo_sazonal = st.radio("Selecione a obra para Sazonalidade:", options=['Obra A', 'Obra B', 'Obra C'], horizontal=True)
        if not df_diarios_mo.empty and 'ip_d' in df_diarios_mo.columns:
            df_d_sazonal = df_diarios_mo[df_diarios_mo['nome_obra'] == obra_alvo_sazonal].copy()
            if not df_d_sazonal.empty:
                dias_pt = {'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta', 'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'}
                df_d_sazonal['dia_semana'] = df_d_sazonal['data'].dt.day_name().map(dias_pt)
                
                dia_semana_stats = df_d_sazonal.groupby('dia_semana')['ip_d'].agg(
                    Média='mean', 
                    Mediana='median', 
                    Qtd_Lançamentos='count'
                ).reset_index()
                
                st.dataframe(
                    dia_semana_stats,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Média": st.column_config.NumberColumn(format="%.2f"),
                        "Mediana": st.column_config.NumberColumn(format="%.2f"),
                        "Qtd_Lançamentos": st.column_config.NumberColumn(format="%d")
                    }
                )
            else:
                st.warning(f"Sem lançamentos para a {obra_alvo_sazonal}.")
        else:
             st.info("Dados insuficientes para Sazonalidade.")
else:
    st.error("ERRO: Nenhuma obra válida encontrada nos bancos de dados para iniciar o painel.")