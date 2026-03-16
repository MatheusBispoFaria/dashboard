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

# 4. Construção da Interface
if df_prod is not None and not df_prod.empty:
    
    st.title("Dashboard Integrado de Produtividade e Insumos")
    st.markdown("Análise de desempenho e consumo de recursos nos canteiros de obra.")
    
    # Filtro estrutural de mão de obra (mantido)
    if 'tipo_insumo' in df_diarios.columns:
        tipo_limpo = df_diarios['tipo_insumo'].astype(str).str.strip().str.upper()
        filtro_mo = tipo_limpo.str.contains('MÃO DE OBRA|MAO DE OBRA', na=False, regex=True)
        df_diarios_mo = df_diarios[filtro_mo].copy()
        
        st.warning(
            "**Filtro Estrutural Aplicado:** A base de lançamentos diários foi filtrada para exibir apenas insumos de **Mão de Obra**, "
            "garantindo consistência na análise de produtividade (horas vs produção)."
        )
    else:
        df_diarios_mo = df_diarios.copy()
        st.error("Aviso: A coluna 'tipo_insumo' não foi encontrada. Os materiais não foram filtrados.")
    
    st.write("")
    
    # --- FILTROS INTERATIVOS NA BARRA LATERAL ---
    st.sidebar.header("Filtros de Análise")
    
    # Seleção da obra (mantido)
    obras = sorted(df_prod['OBRA'].dropna().unique())
    obra_sel = st.sidebar.selectbox("Selecione a Obra alvo:", obras)
    
    # Aplicação do filtro de obra
    df_p_obra = df_prod[df_prod['OBRA'] == obra_sel]
    nome_obra_padrao = obra_sel.replace('_', ' ').title()
    df_d_obra = df_diarios_mo[df_diarios_mo['nome_obra'] == nome_obra_padrao]
    
    # Filtros adicionais (aparecem somente se houver dados)
    if not df_p_obra.empty or not df_d_obra.empty:
        st.sidebar.markdown("### Filtros Avançados")
        
        # Filtro de data (baseado nas duas fontes)
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
                    # Aplica nas duas bases
                    if not df_p_obra.empty:
                        df_p_obra = df_p_obra[(df_p_obra['CREATED'] >= start_date) & (df_p_obra['CREATED'] <= end_date)]
                    if not df_d_obra.empty:
                        df_d_obra = df_d_obra[(df_d_obra['data'] >= start_date) & (df_d_obra['data'] <= end_date)]
        
        # Filtro de classe (apenas para produtividade)
        if not df_p_obra.empty and 'CLASSE_COMP' in df_p_obra.columns:
            classes = sorted(df_p_obra['CLASSE_COMP'].dropna().unique())
            if len(classes) > 0:
                classes_sel = st.sidebar.multiselect("Classes de serviço", classes, default=classes)
                df_p_obra = df_p_obra[df_p_obra['CLASSE_COMP'].isin(classes_sel)]
        
        # Filtro de insumo (apenas para diários)
        if not df_d_obra.empty and 'insumo' in df_d_obra.columns:
            insumos = sorted(df_d_obra['insumo'].dropna().unique())
            if len(insumos) > 0:
                insumos_sel = st.sidebar.multiselect("Insumos (mão de obra)", insumos, default=insumos)
                df_d_obra = df_d_obra[df_d_obra['insumo'].isin(insumos_sel)]
    else:
        st.sidebar.info("Nenhum dado disponível para esta obra.")
    
    # --- MÉTRICAS PRINCIPAIS (após todos os filtros) ---
    c1, c2, c3 = st.columns(3)
    ip_medio = df_p_obra['IP_D'].mean() if not df_p_obra.empty else 0
    meta_siurb = df_p_obra['COEF_SIURB'].mean() if not df_p_obra.empty else 0
    qtd_registros = len(df_d_obra)
    
    c1.metric("Índice de Produtividade (IP) Médio", f"{ip_medio:.3f}")
    c2.metric("Meta do Orçamento (SIURB)", f"{meta_siurb:.3f}")
    c3.metric("Registros Diários (Mão de Obra)", qtd_registros)
    
    st.divider()
    
    # --- GRÁFICOS ANALÍTICOS (aprimorados) ---
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("Evolução da Produtividade (IP)")
        if not df_p_obra.empty:
            # Paleta de cores moderna e mais contraste
            fig1 = px.line(
                df_p_obra, 
                x='CREATED', 
                y='IP_D', 
                color='CLASSE_COMP',
                markers=True,
                template="plotly_white",
                color_discrete_sequence=px.colors.qualitative.Bold,  # cores vibrantes
                labels={'CREATED': 'Data', 'IP_D': 'Índice de Produtividade', 'CLASSE_COMP': 'Classe'}
            )
            fig1.update_traces(line=dict(width=2.5), marker=dict(size=6))
            fig1.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=40, r=20, t=30, b=40),
                height=450,
                hovermode="x unified",
                title=None
            )
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("Sem dados de produtividade para os filtros selecionados.")
        
    with col_b:
        st.subheader("Consumo de Mão de Obra (Horas)")
        if not df_d_obra.empty:
            df_insumo = df_d_obra.groupby('insumo', as_index=False)['qntd'].sum()
            df_insumo = df_insumo.sort_values('qntd', ascending=False)
            
            fig2 = px.bar(
                df_insumo, 
                x='insumo', 
                y='qntd',
                color='insumo',
                template="plotly_white",
                color_discrete_sequence=px.colors.qualitative.Pastel,  # suave mas distinguível
                labels={'insumo': '', 'qntd': 'Horas trabalhadas'}
            )
            fig2.update_layout(
                showlegend=False,
                margin=dict(l=40, r=20, t=20, b=80),
                height=450,
                xaxis_tickangle=-45,
                hovermode="x"
            )
            fig2.update_traces(marker_line_width=0)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Sem dados de diários para os filtros selecionados.")
    
    st.divider()
    
    # --- TABELA DETALHADA ---
    st.subheader("Lançamentos Diários (Apenas Mão de Obra)")
    if not df_d_obra.empty:
        st.dataframe(
            df_d_obra.sort_values('data', ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "data": "Data",
                "insumo": "Insumo",
                "qntd": "Quantidade (h)",
                "nome_obra": "Obra"
            }
        )
    else:
        st.info("Nenhum registro de diário para os filtros selecionados.")
        
    st.divider()
    
    # ==========================================
    # --- CÓDIGO INSERIDO: RESUMO ESTATÍSTICO ---
    # ==========================================
    st.subheader("Resumo Estatístico das Variáveis (Base CSV)")
    
    try:
        # Carregar os dados conforme o código enviado
        df_csv = pd.read_csv('df_diarios.xlsx')

        # Filtrar pelas métricas contínuas de desempenho
        cols = ['qntd', 'qs', 'ip_d']

        # Calcular as medidas
        tabela_resumo = df_csv[cols].agg(['mean', 'median', lambda x: x.mode().iloc[0]]).T
        tabela_resumo.columns = ['Média', 'Mediana', 'Moda']
        
        # Exibir no dashboard em formato de tabela estilizada (substitui o print)
        st.dataframe(tabela_resumo, use_container_width=True)
        
    except Exception as e:
        st.warning(f"Atenção: Não foi possível calcular o resumo estatístico pois o arquivo CSV não foi encontrado ou falhou ao ler. Detalhes: {e}")

else:
    st.info("Aguardando o carregamento dos dados para gerar o dashboard.")