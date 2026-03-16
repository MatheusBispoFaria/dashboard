import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime

# 1. Configuração da Página (Deve ser a primeira chamada)
st.set_page_config(
    page_title="Dashboard Obras - Final", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Injeção de CSS Customizado (Tema Claro / Clean) aprimorado
custom_css = """
<style>
    /* Fundo geral da aplicação */
    .stApp {
        background-color: #F4F6F9;
    }
    
    /* Estilização dos cards de métrica */
    div[data-testid="metric-container"] {
        background-color: #FFFFFF;
        border: 1px solid #E0E6ED;
        padding: 20px 25px;
        border-radius: 12px;
        box-shadow: 0px 6px 12px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0px 10px 20px rgba(0, 0, 0, 0.08);
    }
    
    /* Texto dos rótulos e valores */
    div[data-testid="stMetricLabel"] {
        color: #5C6A79;
        font-weight: 600;
        font-size: 0.9rem;
    }
    div[data-testid="stMetricValue"] {
        color: #1E293B;
        font-size: 2rem;
        font-weight: 700;
    }
    
    /* Ajuste de espaçamento dos gráficos */
    .stPlotlyChart {
        border-radius: 12px;
        background-color: #FFFFFF;
        padding: 10px;
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.03);
    }
    
    /* Títulos das seções */
    h2, h3 {
        color: #1E293B;
        font-weight: 600;
        margin-top: 1rem;
    }
    
    /* Sidebar com fundo mais suave */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E0E6ED;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# 3. Carregamento e Tratamento de Dados
@st.cache_data
def load_data():
    try:
        df_p = pd.read_csv('dados_produtividade_construcao.csv')
        df_p['CREATED'] = pd.to_datetime(df_p['CREATED'], errors='coerce')

        df_d = pd.read_excel('df_diarios.xlsx')
        df_d['data'] = pd.to_datetime(df_d['data'], errors='coerce')
        
        if 'nome_obra' in df_d.columns:
            df_d['nome_obra'] = df_d['nome_obra'].astype(str).str.replace('_', ' ').str.title()
            
        return df_p, df_d
    except Exception as e:
        st.error(f"Erro crítico ao ler os arquivos: {e}")
        st.info("Certifique-se de que os arquivos 'dados_produtividade_construcao.csv' e 'df_diarios.xlsx' estão no mesmo diretório.")
        return None, None

df_prod, df_diarios = load_data()

# Função auxiliar para calcular Moda
def get_mode(x):
    m = x.mode()
    return m.iloc[0] if not m.empty else np.nan

# 4. Construção da Interface
if df_prod is not None and not df_prod.empty:
    
    st.title("Dashboard Integrado de Produtividade e Insumos")
    st.markdown("Análise de desempenho e consumo de recursos nos canteiros de obra.")
    
    # Filtro estrutural de mão de obra (mantido)
    if 'tipo_insumo' in df_diarios.columns:
        tipo_limpo = df_diarios['tipo_insumo'].astype(str).str.strip().str.upper()
        filtro_mo = tipo_limpo.str.contains('MÃO DE OBRA|MAO DE OBRA', na=False, regex=True)
        df_diarios_mo = df_diarios[filtro_mo].copy()
    else:
        df_diarios_mo = df_diarios.copy()
        st.error("Aviso: A coluna 'tipo_insumo' não foi encontrada. Os materiais não foram filtrados.")
    
    st.write("")
    
    # --- FILTROS INTERATIVOS NA BARRA LATERAL ---
    st.sidebar.header("Filtros de Análise")
    
    obras = sorted(df_prod['OBRA'].dropna().unique())
    obra_sel = st.sidebar.selectbox("Selecione a Obra alvo:", obras)
    
    # Aplicação do filtro de obra
    df_p_obra = df_prod[df_prod['OBRA'] == obra_sel]
    nome_obra_padrao = obra_sel.replace('_', ' ').title()
    df_d_obra = df_diarios_mo[df_diarios_mo['nome_obra'] == nome_obra_padrao]
    
    # Filtros adicionais (aparecem somente se houver dados)
    if not df_p_obra.empty or not df_d_obra.empty:
        st.sidebar.markdown("### Filtros Avançados")
        
        datas_prod = df_p_obra['CREATED'].dropna()
        datas_diarios = df_d_obra['data'].dropna()
        if not datas_prod.empty or not datas_diarios.empty:
            min_date = min(datas_prod.min() if not datas_prod.empty else pd.Timestamp.today(),
                           datas_diarios.min() if not datas_diarios.empty else pd.Timestamp.today())
            max_date = max(datas_prod.max() if not datas_prod.empty else pd.Timestamp.today(),
                           datas_diarios.max() if not datas_diarios.empty else pd.Timestamp.today())
            
            if min_date <= max_date:
                date_range = st.sidebar.date_input(
                    "Intervalo de datas",
                    value=(min_date.date(), max_date.date()),
                    min_value=min_date.date(),
                    max_value=max_date.date()
                )
                if len(date_range) == 2:
                    start_date, end_date = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
                    if not df_p_obra.empty:
                        df_p_obra = df_p_obra[(df_p_obra['CREATED'] >= start_date) & (df_p_obra['CREATED'] <= end_date)]
                    if not df_d_obra.empty:
                        df_d_obra = df_d_obra[(df_d_obra['data'] >= start_date) & (df_d_obra['data'] <= end_date)]
        
        if not df_p_obra.empty and 'CLASSE_COMP' in df_p_obra.columns:
            classes = sorted(df_p_obra['CLASSE_COMP'].dropna().unique())
            if len(classes) > 0:
                classes_sel = st.sidebar.multiselect("Classes de serviço", classes, default=classes)
                df_p_obra = df_p_obra[df_p_obra['CLASSE_COMP'].isin(classes_sel)]
        
        if not df_d_obra.empty and 'insumo' in df_d_obra.columns:
            insumos = sorted(df_d_obra['insumo'].dropna().unique())
            if len(insumos) > 0:
                insumos_sel = st.sidebar.multiselect("Insumos (mão de obra)", insumos, default=insumos)
                df_d_obra = df_d_obra[df_d_obra['insumo'].isin(insumos_sel)]
    else:
        st.sidebar.info("Nenhum dado disponível para esta obra.")
    
    # --- MÉTRICAS PRINCIPAIS ---
    c1, c2, c3 = st.columns(3)
    ip_medio = df_p_obra['IP_D'].mean() if not df_p_obra.empty else 0
    meta_siurb = df_p_obra['COEF_SIURB'].mean() if not df_p_obra.empty else 0
    qtd_registros = len(df_d_obra)
    
    c1.metric("Índice de Produtividade (IP) Médio", f"{ip_medio:.3f}")
    c2.metric("Meta do Orçamento (SIURB)", f"{meta_siurb:.3f}")
    c3.metric("Registros Diários (Mão de Obra)", qtd_registros)
    
    st.divider()
    
    # --- GRÁFICOS ANALÍTICOS ---
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("Evolução da Produtividade (IP)")
        if not df_p_obra.empty:
            fig1 = px.line(
                df_p_obra, x='CREATED', y='IP_D', color='CLASSE_COMP', markers=True,
                template="plotly_white", color_discrete_sequence=px.colors.qualitative.Bold,
                labels={'CREATED': 'Data', 'IP_D': 'Índice de Produtividade', 'CLASSE_COMP': 'Classe'}
            )
            fig1.update_traces(line=dict(width=2.5), marker=dict(size=6))
            fig1.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                               margin=dict(l=40, r=20, t=30, b=40), height=450, hovermode="x unified")
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("Sem dados de produtividade para os filtros selecionados.")
        
    with col_b:
        st.subheader("Consumo de Mão de Obra (Horas)")
        if not df_d_obra.empty:
            df_insumo = df_d_obra.groupby('insumo', as_index=False)['qntd'].sum().sort_values('qntd', ascending=False)
            fig2 = px.bar(
                df_insumo, x='insumo', y='qntd', color='insumo', template="plotly_white",
                color_discrete_sequence=px.colors.qualitative.Pastel, labels={'insumo': '', 'qntd': 'Horas trabalhadas'}
            )
            fig2.update_layout(showlegend=False, margin=dict(l=40, r=20, t=20, b=80), height=450, xaxis_tickangle=-45)
            fig2.update_traces(marker_line_width=0)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Sem dados de diários para os filtros selecionados.")
    
    st.divider()

    # ==========================================
    # --- NOVO BLOCO: INTELIGÊNCIA ANALÍTICA ---
    # ==========================================
    st.subheader("Inteligência Analítica e Consistência Global")
    st.markdown("Comparativo de previsibilidade e variância de rendimento, fundamental para calibração de orçamento.")

    # Criando abas para organizar o volume de informações matemáticas
    aba1, aba2 = st.tabs(["📊 Comparativo por Obra (Consistência)", "📅 Sazonalidade (Dias da Semana)"])

    with aba1:
        st.markdown("**Diagnóstico de Obras:** Analisa todas as obras do banco para descobrir qual é a mais consistente. "
                    "*(Obras com alto CV% são altamente instáveis e representam risco ao planejamento)*.")
        
        # Agrupamento de todas as obras originais (df_diarios_mo)
        obra_stats = df_diarios_mo.dropna(subset=['nome_obra']).groupby('nome_obra')['ip_d'].agg(
            Média='mean',
            Mediana='median',
            Moda=get_mode,
            Desvio_Padrão='std'
        ).reset_index()

        # Cálculo do Coeficiente de Variação
        obra_stats['CV (%)'] = (obra_stats['Desvio_Padrão'] / obra_stats['Média']) * 100
        # Ordenando da mais produtiva (real) para a menor
        obra_stats = obra_stats.sort_values('Mediana', ascending=False)

        # Aplicando estilo na tabela para ficar legível e profissional
        st.dataframe(
            obra_stats.style.format({
                'Média': '{:.3f}',
                'Mediana': '{:.3f}',
                'Moda': '{:.3f}',
                'Desvio_Padrão': '{:.3f}',
                'CV (%)': '{:.1f}%'
            }).background_gradient(subset=['CV (%)'], cmap='Reds'), # Destaca os maiores riscos em vermelho
            use_container_width=True,
            hide_index=True
        )

    with aba2:
        st.markdown("**Ritmo de Produção:** Evidencia em quais dias da semana ocorrem os maiores picos (ou gargalos) de produtividade e lançamentos atípicos.")
        
        df_d_sazonal = df_diarios_mo.copy()
        
        # Traduzindo dias da semana
        dias_pt = {
            'Monday': 'Segunda-feira', 'Tuesday': 'Terça-feira', 'Wednesday': 'Quarta-feira',
            'Thursday': 'Quinta-feira', 'Friday': 'Sexta-feira', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
        }
        df_d_sazonal['dia_semana'] = df_d_sazonal['data'].dt.day_name().map(dias_pt)

        # Agrupamento sazonal
        dia_semana_stats = df_d_sazonal.groupby('dia_semana')['ip_d'].agg(
            Média='mean',
            Mediana='median',
            Qtd_Lançamentos='count'
        ).reset_index()

        # Ordenando cronologicamente
        ordem_dias = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
        dia_semana_stats['dia_semana'] = pd.Categorical(dia_semana_stats['dia_semana'], categories=ordem_dias, ordered=True)
        dia_semana_stats = dia_semana_stats.sort_values('dia_semana')

        st.dataframe(
            dia_semana_stats.style.format({
                'Média': '{:.3f}',
                'Mediana': '{:.3f}',
                'Qtd_Lançamentos': '{:,.0f}'
            }).bar(subset=['Mediana'], color='#5C6A79'), # Adiciona pequenas barras dentro da célula da Mediana
            use_container_width=True,
            hide_index=True
        )

else:
    st.info("Aguardando o carregamento dos dados para gerar o dashboard.")