import streamlit as st
import yfinance as yf
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt

st.set_page_config(page_title="ProPicks IA Brasil", layout="wide")
st.title("ProPicks IA - Melhores Ações Brasileiras")

# =========================
# Coleta de dados financeiros
# =========================
@st.cache_data
def obter_dados(tickers):
    dados = {}
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
            dados[ticker] = {
                'ROE': info.get('returnOnEquity'),
                'Margem Líquida': info.get('netMargins'),
                'Dívida/Patrimônio': info.get('debtToEquity'),
                'EV/EBITDA': info.get('enterpriseToEbitda'),
                'Crescimento Receita 5a': info.get('revenueGrowth'),
                'Setor': info.get('sector')
            }
        except:
            pass
    return dados

def normalizar_dados(dados):
    df = pd.DataFrame.from_dict(dados, orient='index')
    df_num = df.select_dtypes(include=['float64', 'int64']).copy()
    scaler = MinMaxScaler()
    df_scaled = pd.DataFrame(scaler.fit_transform(df_num), columns=df_num.columns, index=df.index)
    df_final = df_scaled.copy()
    df_final['Setor'] = df['Setor']
    return df_final

def calcular_score(df):
    df['Score'] = df[['ROE', 'Margem Líquida', 'Dívida/Patrimônio', 'EV/EBITDA', 'Crescimento Receita 5a']].mean(axis=1)
    df['Classificação'] = pd.qcut(df['Score'], q=3, labels=['Inferior', 'Neutro', 'Superior'])
    return df.sort_values(by='Score', ascending=False)

# =========================
# Dados históricos e benchmark
# =========================
@st.cache_data
def get_monthly_prices(tickers, start, end):
    prices = yf.download(tickers, start=start, end=end, interval="1mo")["Adj Close"]
    return prices.dropna(how="all")

def simular_rebalanceamento(tickers, start, end, benchmark="^BVSP"):
    precos = get_monthly_prices(tickers, start, end).ffill()
    ibov = get_monthly_prices(benchmark, start, end).ffill()
    retornos = precos.pct_change().dropna()
    retorno_ibov = ibov.pct_change().dropna()
    alocacao = 1 / len(tickers)
    retorno_carteira = (retornos * alocacao).sum(axis=1)
    acumulado_carteira = (1 + retorno_carteira).cumprod()
    acumulado_ibov = (1 + retorno_ibov.squeeze()).cumprod()
    return acumulado_carteira, acumulado_ibov

# =========================
# Interface
# =========================
tickers_input = st.text_input("Digite os tickers (separados por vírgula)", "PETR4.SA,VALE3.SA,ITUB4.SA,WEGE3.SA,BBAS3.SA")
tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
start = st.date_input("Início da análise", pd.to_datetime("2022-01-01"))
end = st.date_input("Fim da análise", pd.to_datetime("2024-12-31"))

if st.button("Analisar Ações"):
    with st.spinner("Coletando e processando dados..."):
        dados_brutos = obter_dados(tickers)
        if not dados_brutos:
            st.error("Erro ao obter dados.")
        else:
            df_normalizado = normalizar_dados(dados_brutos)
            df_resultado = calcular_score(df_normalizado)

            st.subheader("Ranking ProPicks IA")
            st.dataframe(df_resultado.style.background_gradient(cmap="Greens", subset=["Score"]))

            st.download_button("Baixar Resultados CSV", data=df_resultado.to_csv().encode("utf-8"), file_name="propicks_ranking.csv")

            st.subheader("Simulação Histórica com Rebalanceamento Mensal")
            carteira, ibov = simular_rebalanceamento(list(df_resultado.index), start, end)

            df_plot = pd.DataFrame({
                "Carteira ProPicks": carteira,
                "Ibovespa": ibov
            })

            st.line_chart(df_plot)

            st.markdown(f"""
                - Retorno acumulado carteira: **{(carteira[-1] - 1)*100:.2f}%**
                - Retorno acumulado Ibovespa: **{(ibov[-1] - 1)*100:.2f}%**
            """)

st.markdown("---")
st.markdown("**Desenvolvido com dados públicos. Inspirado no ProPicks IA.**")
