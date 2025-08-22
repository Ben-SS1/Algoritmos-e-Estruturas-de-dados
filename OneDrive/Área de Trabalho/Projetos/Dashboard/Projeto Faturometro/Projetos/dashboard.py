import streamlit as st
import pandas as pd
import plotly.express as px
from numpy import polyfit

st.set_page_config(layout="wide")

# Carregamento da base com cache
@st.cache_data
def load_data():
    cols = ["DATA", "FATURAMENTO", "SEGMENTO", "COORDENADOR", "SUPERVISOR"]
    df = pd.read_excel("BASES FATUROMETRO.xlsx", "CALENDARIO", usecols=cols)
    df = df.dropna(subset=["DATA", "FATURAMENTO", "SEGMENTO", "COORDENADOR", "SUPERVISOR"])
    df["DATA"] = pd.to_datetime(df["DATA"])
    df = df.sort_values("DATA")
    df["MÊS"] = df["DATA"].dt.month.astype(str)
    return df

@st.cache_data
def load_glosas():
    sheets = ["INTRA-HORA CARTÃO", "INTRA-HORA CIDADÃO", "INTRA-HORA STE"]
    glosas = []
    for sheet in sheets:
        df_sheet = pd.read_excel("BASES FATUROMETRO.xlsx", sheet, usecols=["DATA", "GLOSAS"])
        df_sheet = df_sheet.dropna(subset=["DATA", "GLOSAS"])
        df_sheet["DATA"] = pd.to_datetime(df_sheet["DATA"])
        glosas.append(df_sheet)
    df_glosas = pd.concat(glosas)
    df_glosas = df_glosas.groupby("DATA", as_index=False).sum(numeric_only=True)
    return df_glosas

df = load_data()
df_glosas = load_glosas()

# Sidebar filtros
meses = sorted(df["MÊS"].unique().tolist())
segmentos = ["Todos"] + sorted(df["SEGMENTO"].unique().tolist())
coordenadores = ["Todos"] + sorted(df["COORDENADOR"].unique().tolist())

periodo = st.sidebar.date_input("Periodo", value=(df["DATA"].min(), df["DATA"].max()),
                                min_value=df["DATA"].min(), 
                                max_value=df["DATA"].max())

if isinstance(periodo, tuple) and len(periodo) == 2:
    data_inicio, data_fim = periodo
    data_inicio = pd.to_datetime(data_inicio)
    data_fim = pd.to_datetime(data_fim)
else:
    st.error("Selecione um intervalo de datas válido")
    st.stop()

segmento = st.sidebar.selectbox("Segmento", segmentos)
coord = st.sidebar.selectbox("Coordenador", coordenadores)

# Aplicação dos filtros
df_filtered = df[(df["DATA"] >= data_inicio) & (df["DATA"] <= data_fim)]
if segmento != "Todos":
    df_filtered = df_filtered[df_filtered["SEGMENTO"] == segmento]
if coord != "Todos":
    df_filtered = df_filtered[df_filtered["COORDENADOR"] == coord]

if df_filtered.empty:
    st.warning("Nenhum dado disponível para os filtros selecionados.")
    st.stop()

faturamento_total = df_filtered["FATURAMENTO"].sum()

# Comparação intervalo de dias
delta_dias = (data_fim - data_inicio).days
data_inicio_anterior = (data_inicio - pd.DateOffset(months=1)).date()
data_fim_anterior = data_inicio_anterior + pd.Timedelta(days=delta_dias)

df_anterior = df[(df["DATA"].dt.date >= data_inicio_anterior) & (df["DATA"].dt.date <= data_fim_anterior)]
if segmento != "Todos":
    df_anterior = df_anterior[df_anterior["SEGMENTO"] == segmento]
if coord != "Todos":
    df_anterior = df_anterior[df_anterior["COORDENADOR"] == coord]

faturamento_anterior = df_anterior["FATURAMENTO"].sum()
variacao = ((faturamento_total - faturamento_anterior) / faturamento_anterior) * 100 if faturamento_anterior > 0 else 0

top_col1, top_col2, top_col3 = st.columns([1.5, 2, 2])
with top_col1:
    st.markdown("### 📊 Faturamento Total")
    st.metric(
        label=f"{data_inicio.strftime('%d/%m')} até {data_fim.strftime('%d/%m')}",
        value=f"R$ {faturamento_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        delta=f"{variacao:.2f}%" if faturamento_anterior > 0 else "N/A",
        delta_color="normal"
    )

col1, col2 = st.columns(2)
col3, col4, col5 = st.columns(3)

with st.spinner("Gerando gráficos..."):
    # Faturamento + Glosas diário
    dia_total = df_filtered.groupby("DATA")[["FATURAMENTO"]].sum().reset_index()
    dia_total = dia_total.merge(df_glosas, on="DATA", how="left").fillna(0)

    # Verifica se o mês é incompleto
    ultimo_dia_filtro = df_filtered["DATA"].max()
    ultimo_dia_mes = pd.to_datetime(f"{ultimo_dia_filtro.year}-{ultimo_dia_filtro.month}-01") + pd.offsets.MonthEnd(0)
    mes_incompleto = ultimo_dia_filtro < ultimo_dia_mes

    fig_date = px.area(dia_total, x="DATA", y="FATURAMENTO", line_shape="linear",
                       title="Faturamento diário")

    if mes_incompleto and len(dia_total) > 1:
        x_numeric = (dia_total["DATA"] - dia_total["DATA"].min()).dt.days
        y = dia_total["GLOSAS"]
        slope, intercept = polyfit(x_numeric, y, 1)
        trend_y = slope * x_numeric + intercept
        fig_date.add_scatter(x=dia_total["DATA"], y=trend_y, mode="lines",
                             name="Tendência Glosas", line=dict(dash="dash", color="orange"))

    col1.plotly_chart(fig_date, use_container_width=True)

    seg_total = df_filtered.groupby("SEGMENTO")[["FATURAMENTO"]].sum().reset_index()
    fig_seg = px.bar(seg_total, x="SEGMENTO", y="FATURAMENTO", color="SEGMENTO", title="Faturamento por segmento")
    fig_seg.update_layout(transition=dict(duration=500, easing="cubic-in-out"))
    col2.plotly_chart(fig_seg, use_container_width=True)

    coord_total = df_filtered.groupby("COORDENADOR")[["FATURAMENTO"]].sum().reset_index()
    fig_coord = px.pie(coord_total, values="FATURAMENTO", names="COORDENADOR", title="Faturamento por coordenador")
    fig_coord.update_layout(transition=dict(duration=500, easing="cubic-in-out"))
    col3.plotly_chart(fig_coord, use_container_width=True)

    super_total = df_filtered.groupby("SUPERVISOR")[["FATURAMENTO"]].sum().reset_index()
    fig_super = px.bar(super_total, x="FATURAMENTO", y="SUPERVISOR", title="Faturamento por supervisor", orientation="h")
    fig_super.update_layout(transition=dict(duration=500, easing="cubic-in-out"))
    col4.plotly_chart(fig_super, use_container_width=True)

    faturamento_diario = df_filtered.groupby("DATA")["FATURAMENTO"].sum().reset_index()
    faturamento_diario["MEDIA_MOVEL"] = faturamento_diario["FATURAMENTO"].rolling(window=3).mean()
    faturamento_diario["DIA_SEMANA"] = faturamento_diario["DATA"].dt.day_name()

    dias_traduzidos = {
        "Monday": "Segunda", "Tuesday": "Terça", "Wednesday": "Quarta",
        "Thursday": "Quinta", "Friday": "Sexta", "Saturday": "Sábado", "Sunday": "Domingo"
    }
    faturamento_diario["DIA_SEMANA"] = faturamento_diario["DIA_SEMANA"].map(dias_traduzidos)

    media_movel_por_dia = faturamento_diario.groupby("DIA_SEMANA")["MEDIA_MOVEL"].mean().reset_index()
    dias_ordenados = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    media_movel_por_dia["DIA_SEMANA"] = pd.Categorical(media_movel_por_dia["DIA_SEMANA"], categories=dias_ordenados, ordered=True)
    media_movel_por_dia = media_movel_por_dia.sort_values("DIA_SEMANA")

    fig_movel = px.line(media_movel_por_dia, x="DIA_SEMANA", y="MEDIA_MOVEL",
                        title="Média Móvel do Faturamento por Dia da Semana", markers=True)
    fig_movel.update_layout(
        xaxis_title="Dia da Semana",
        yaxis_title="Faturamento (Média Móvel)",
        font=dict(color="white"),
        margin=dict(l=40, r=40, t=60, b=40),
        transition=dict(duration=500, easing="cubic-in-out")
    )
    col5.plotly_chart(fig_movel, use_container_width=True)
