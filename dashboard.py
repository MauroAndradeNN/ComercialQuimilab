import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(page_title="Dashboard de Vendas & CRM", layout="wide")

# Estilo CSS para melhorar a aparência
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# Função para carregar dados
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/13NzTFKbREosqD72c_qhZhUZLutGGkN430Oa-Ky7gnkc/export?format=csv"
    df = pd.read_csv(url)
    
    # 1. TRATAMENTO E ENGENHARIA DE DADOS
    
    # Unificação Comercial
    # Se Nome Vendedor estiver vazio, usa Nome Representante
    df['Responsável pela Venda'] = df['Nome Vendedor'].fillna(df['Nome Representante'])
    df['Responsável pela Venda'] = df['Responsável pela Venda'].replace('', np.nan).fillna(df['Nome Representante'])
    
    # Tipagem
    df['Data Emissão NF'] = pd.to_datetime(df['Data Emissão NF'], dayfirst=True)
    
    # Conversão de colunas numéricas (lidando com formato brasileiro de vírgula)
    def convert_numeric(val):
        if isinstance(val, str):
            val = val.replace('.', '').replace(',', '.')
        return pd.to_numeric(val, errors='coerce')

    df['Vlr Total'] = convert_numeric(df['Vlr Total'])
    df['Vlr Unitário'] = convert_numeric(df['Vlr Unitário'])
    df['Quantidade'] = convert_numeric(df['Quantidade'])
    
    # Segmentação Principal
    df['Categoria 1 Cliente'] = df['Categoria 1 Cliente'].str.upper().str.strip()
    
    return df

# Carregamento inicial
try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

# --- SIDEBAR (FILTROS) ---
st.sidebar.header("Filtros de Análise")

# Filtro de Tipo de Cliente
categorias = df_raw['Categoria 1 Cliente'].unique().tolist()
filtro_categoria = st.sidebar.multiselect("Tipo de Cliente", categorias, default=categorias)

# Filtro de Período
df_raw['Ano'] = df_raw['Data Emissão NF'].dt.year
df_raw['Mês'] = df_raw['Data Emissão NF'].dt.month
anos = sorted(df_raw['Ano'].unique().tolist(), reverse=True)
filtro_ano = st.sidebar.multiselect("Ano", anos, default=anos)

meses = sorted(df_raw['Mês'].unique().tolist())
filtro_mes = st.sidebar.multiselect("Mês", meses, default=meses)

# Filtro de Responsável
responsaveis = sorted(df_raw['Responsável pela Venda'].dropna().unique().tolist())
filtro_resp = st.sidebar.multiselect("Responsável pela Venda", responsaveis, default=responsaveis)

# Aplicação dos filtros
df = df_raw[
    (df_raw['Categoria 1 Cliente'].isin(filtro_categoria)) &
    (df_raw['Ano'].isin(filtro_ano)) &
    (df_raw['Mês'].isin(filtro_mes)) &
    (df_raw['Responsável pela Venda'].isin(filtro_resp))
]

# --- CÁLCULOS DE INTELIGÊNCIA DE CLIENTES (BACKEND) ---

def calculate_crm_metrics(df_full, df_filtered):
    # Data de referência para cálculos de recência (hoje ou última data da base)
    ref_date = df_full['Data Emissão NF'].max()
    
    # Métricas por cliente (usando a base completa para recência real)
    client_metrics = df_full.groupby(['Código Cliente', 'Nome Cliente']).agg(
        Ultima_Compra=('Data Emissão NF', 'max'),
        Total_Gasto=('Vlr Total', 'sum'),
        Qtd_Notas=('Nr.Nota Fiscal', 'nunique')
    ).reset_index()
    
    # Recência em dias
    client_metrics['Dias_Inativo'] = (ref_date - client_metrics['Ultima_Compra']).dt.days
    
    # Buckets de Recência
    def classify_recency(days):
        if days <= 30: return "Ativo (Até 30 dias)"
        elif days <= 60: return "Risco (1 a 2 meses)"
        elif days <= 90: return "Em Evasão (2 a 3 meses)"
        else: return "Perdido (3+ meses)"
    
    client_metrics['Status Inatividade'] = client_metrics['Dias_Inativo'].apply(classify_recency)
    
    # Frequência de Compra (Média de NFs por cliente na base filtrada)
    freq_data = df_filtered.groupby('Código Cliente')['Nr.Nota Fiscal'].nunique().mean()
    
    # Abandono de Produto
    # Lógica: Comprou o produto X no passado (antes de 2 meses atrás), mas não comprou nos últimos 2 meses.
    two_months_ago = ref_date - timedelta(days=60)
    
    # Produtos comprados antes de 2 meses
    past_purchases = df_full[df_full['Data Emissão NF'] < two_months_ago][['Código Cliente', 'Nome Cliente', 'Descrição Prod/Serv', 'Responsável pela Venda']].drop_duplicates()
    # Produtos comprados nos últimos 2 meses
    recent_purchases = df_full[df_full['Data Emissão NF'] >= two_months_ago][['Código Cliente', 'Descrição Prod/Serv']].drop_duplicates()
    
    # Join para identificar o que parou de ser comprado
    abandonment = past_purchases.merge(recent_purchases, on=['Código Cliente', 'Descrição Prod/Serv'], how='left', indicator=True)
    abandonment = abandonment[abandonment['_merge'] == 'left_only'].drop(columns=['_merge'])
    
    return client_metrics, freq_data, abandonment

client_metrics, avg_freq, abandonment_df = calculate_crm_metrics(df_raw, df)

# --- LAYOUT DO DASHBOARD ---
st.title("📊 BI Analytics & CRM Sales Dashboard")

tab1, tab2 = st.tabs(["Visão Geral e Segmentação", "Inteligência de Clientes e Risco"])

with tab1:
    # KPIs
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    faturamento_total = df['Vlr Total'].sum()
    volume_vendido = df['Quantidade'].sum()
    ticket_medio = faturamento_total / df['Nr.Nota Fiscal'].nunique() if df['Nr.Nota Fiscal'].nunique() > 0 else 0
    positivacao = df['Código Cliente'].nunique()
    
    kpi1.metric("Faturamento Total", f"R$ {faturamento_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    kpi2.metric("Volume Vendido", f"{volume_vendido:,.0f}".replace(',', '.'))
    kpi3.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    kpi4.metric("Positivação (Clientes)", positivacao)
    
    st.markdown("---")
    
    col_a, col_b = st.columns([2, 1])
    
    with col_a:
        st.subheader("Evolução de Faturamento por Categoria")
        evolucao = df.groupby([df['Data Emissão NF'].dt.to_period('M'), 'Categoria 1 Cliente'])['Vlr Total'].sum().reset_index()
        evolucao['Data Emissão NF'] = evolucao['Data Emissão NF'].dt.to_timestamp()
        fig_evol = px.line(evolucao, x='Data Emissão NF', y='Vlr Total', color='Categoria 1 Cliente',
                          labels={'Vlr Total': 'Faturamento (R$)', 'Data Emissão NF': 'Mês'},
                          template="plotly_white")
        st.plotly_chart(fig_evol, use_container_width=True)
        
    with col_b:
        st.subheader("Top 5 Responsáveis")
        ranking = df.groupby('Responsável pela Venda')['Vlr Total'].sum().nlargest(5).reset_index()
        fig_rank = px.bar(ranking, x='Vlr Total', y='Responsável pela Venda', orientation='h',
                         labels={'Vlr Total': 'Faturamento (R$)'},
                         color='Vlr Total', color_continuous_scale='Blues')
        fig_rank.update_layout(showlegend=False)
        st.plotly_chart(fig_rank, use_container_width=True)

with tab2:
    st.subheader("Análise de Retenção e Risco (CRM)")
    
    col_c, col_d = st.columns([1, 1])
    
    with col_c:
        st.markdown("**Funil de Retenção (Status de Inatividade)**")
        # Filtrar métricas de clientes apenas para os que pertencem aos filtros atuais (ou visão geral)
        current_clients = df['Código Cliente'].unique()
        filtered_metrics = client_metrics[client_metrics['Código Cliente'].isin(current_clients)]
        
        funil_data = filtered_metrics['Status Inatividade'].value_counts().reindex([
            "Ativo (Até 30 dias)", "Risco (1 a 2 meses)", "Em Evasão (2 a 3 meses)", "Perdido (3+ meses)"
        ]).reset_index()
        funil_data.columns = ['Status', 'Quantidade']
        
        fig_funil = px.funnel(funil_data, x='Quantidade', y='Status', color='Status')
        st.plotly_chart(fig_funil, use_container_width=True)
        
    with col_d:
        st.markdown("**Métricas de Fidelidade**")
        st.write(f"**Frequência Média de Compra:** {avg_freq:.2f} pedidos por cliente no período.")
        st.info("A frequência indica quantas vezes, em média, um cliente volta a comprar dentro do intervalo selecionado.")

    st.markdown("---")
    st.subheader("🎯 Lista de Alvo: Clientes em Risco (> 30 dias sem comprar)")
    
    # Preparar lista de alvo
    # Pegamos o ticket médio histórico do cliente na base filtrada
    ticket_cliente = df.groupby('Código Cliente')['Vlr Total'].sum() / df.groupby('Código Cliente')['Nr.Nota Fiscal'].nunique()
    
    alvo = filtered_metrics[filtered_metrics['Dias_Inativo'] > 30].copy()
    # Adicionar Responsável (pegando o último responsável conhecido)
    last_resp = df_raw.sort_values('Data Emissão NF').groupby('Código Cliente')['Responsável pela Venda'].last()
    alvo = alvo.merge(last_resp, on='Código Cliente', how='left')
    alvo['Ticket Médio Histórico'] = alvo['Código Cliente'].map(ticket_cliente)
    
    alvo_display = alvo[['Nome Cliente', 'Responsável pela Venda', 'Dias_Inativo', 'Ticket Médio Histórico', 'Status Inatividade']]
    alvo_display = alvo_display.sort_values('Dias_Inativo', ascending=False)
    
    st.dataframe(alvo_display.style.format({
        'Ticket Médio Histórico': 'R$ {:.2f}',
        'Dias_Inativo': '{:.0f} dias'
    }), use_container_width=True)

    st.markdown("---")
    st.subheader("💡 Oportunidades por Abandono de Produto")
    st.markdown("Clientes que compravam recorrentemente um produto e não o adquiriram nos últimos 2 meses.")
    
    # Filtrar abandono para os clientes e responsáveis selecionados
    abandonment_filtered = abandonment_df[
        (abandonment_df['Código Cliente'].isin(current_clients)) &
        (abandonment_df['Responsável pela Venda'].isin(filtro_resp))
    ]
    
    st.table(abandonment_filtered[['Nome Cliente', 'Responsável pela Venda', 'Descrição Prod/Serv']].head(20))

# Rodapé Informativo
st.sidebar.markdown("---")
st.sidebar.info("""
**Lógicas de CRM Aplicadas:**
- **Recência:** Calculada a partir da última data de emissão de NF em relação à data mais recente da base.
- **Frequência:** Média de Notas Fiscais únicas por cliente.
- **Abandono:** Identifica se um cliente comprou um SKU específico no passado, mas não houve registro de venda deste SKU para ele nos últimos 60 dias.
""")
