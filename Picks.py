import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("ProPicks IA - Melhores Ações Brasileiras")

TICKERS = [
    "ITUB4.SA", "PETR4.SA", "VALE3.SA", "BBDC4.SA", "ABEV3.SA",
    "MGLU3.SA", "BBAS3.SA", "WEGE3.SA", "LREN3.SA", "JBSS3.SA"
]

BENCHMARK = "^BVSP"  # IBOV

@st.cache_data(ttl=3600)
def get_fundamental_data(tickers):
    dados = {}
    for t in tickers:
        try:
            ticker = yf.Ticker(t)
            info = ticker.info
            
            dados[t] = {
                "ROE": info.get("returnOnEquity", np.nan),
                "Margem Líquida": info.get("netMargins", np.nan),
                "Dívida/Patrimônio": info.get("debtToEquity", np.nan),
                "EV/EBITDA": info.get("enterpriseToEbitda", np.nan),
                "Crescimento Receita 5a": info.get("revenueGrowth", np.nan),
                "Nome": info.get("shortName", t),
            }
        except Exception as e:
            st.warning(f"Erro ao obter dados de {t}: {e}")
            dados[t] = {
                "ROE": np.nan,
                "Margem Líquida": np.nan,
                "Dívida/Patrimônio": np.nan,
                "EV/EBITDA": np.nan,
                "Crescimento Receita 5a": np.nan,
                "Nome": t,
            }
    df = pd.DataFrame.from_dict(dados, orient="index")
    return df

def normalizar_dados(df):
    df_num = df[["ROE", "Margem Líquida", "Dívida/Patrimônio", "EV/EBITDA", "Crescimento Receita 5a"]].copy()
    df_num = df_num.fillna(df_num.median())  # preencher NaNs com mediana para evitar perda de dados
    scaler = MinMaxScaler()
    df_scaled = pd.DataFrame(scaler.fit_transform(df_num), columns=df_num.columns, index=df_num.index)
    return df_scaled

def calcular_score(df_normalizado):
    colunas_esperadas = ['ROE', 'Margem Líquida', 'Dívida/Patrimônio', 'EV/EBITDA', 'Crescimento Receita 5a']
    colunas_validas = [col for col in colunas_esperadas if col in df_normalizado.columns]
    if not colunas_validas:
        st.error("Nenhuma coluna válida para cálculo do score")
        return None
    # Para Dívida/Patrimônio e EV/EBITDA, menor é melhor, então invertemos o valor normalizado para que maior score seja melhor
    df_normalizado["Dívida/Patrimônio"] = 1 - df_normalizado["Dívida/Patrimônio"]
    df_normalizado["EV/EBITDA"] = 1 - df_normalizado["EV/EBITDA"]
    df_normalizado['Score'] = df_normalizado[colunas_validas].mean(axis=1)
    df_normalizado['Classificação'] = pd.qcut(df_normalizado['Score'], q=3, labels=['Inferior', 'Neutro', 'Superior'])
    return df_normalizado.sort_values(by='Score', ascending=False)

@st.cache_data(ttl=3600)
def get_historical_prices(tickers, start_date):
    df = yf.download(tickers, start=start_date, progress=False)['Adj Close']
    if isinstance(df, pd.Series):
        df = df.to_frame()
    return df

def calcula_retorno_mensal(df_precos):
    df_retorno = df_precos.resample('M').last().pct_change().dropna()
    return df_retorno

def rebalanceamento_mensal(ranking, precos_historicos, top_n=5):
    # Vai usar os top_n do ranking mais recente para montar portfólio mensal
    datas = precos_historicos.index.to_period('M').unique()
    pesos = pd.DataFrame(0, index=datas, columns=ranking.index)
    
    for mes in datas:
        # Usar ranking fixo para cada mês para simplificar
        top_ativos = ranking.head(top_n).index
        pesos.loc[mes, top_ativos] = 1 / top_n

    # Calcular retorno mensal do portfólio
    retorno_mensal = calcula_retorno_mensal(precos_historicos)
    retorno_portfolio = (pesos.shift(1) * retorno_mensal).sum(axis=1).dropna()
    retorno_acumulado = (1 + retorno_portfolio).cumprod() - 1
    return retorno_acumulado, retorno_portfolio

def main():
    st.sidebar.title("Configurações")
    top_n = st.sidebar.slider("Número de Ações no Portfólio", min_value=3, max_value=len(TICKERS), value=5)

    st.subheader("Buscando dados fundamentalistas...")
    df_fund = get_fundamental_data(TICKERS)
    st.write(df_fund)

    st.subheader("Normalizando dados...")
    df_norm = normalizar_dados(df_fund)
    st.write(df_norm)

    st.subheader("Calculando score e ranking...")
    df_score = calcular_score(df_norm)
    if df_score is None:
        st.stop()
    st.dataframe(df_score[['Score', 'Classificação']])

    st.subheader("Buscando dados históricos de preço para rebalanceamento...")
    data_inicio = '2018-01-01'
    precos = get_historical_prices(TICKERS, data_inicio)
    st.write(precos.tail())

    st.subheader("Rebalanceamento Mensal")
    retorno_acum, retorno_mens = rebalanceamento_mensal(df_score, precos, top_n=top_n)

    # Benchmark IBOV
    ibov = get_historical_prices(BENCHMARK, data_inicio)
    ibov_retorno = calcula_retorno_mensal(ibov)
    ibov_retorno_acum = (1 + ibov_retorno).cumprod() - 1

    st.line_chart(pd.DataFrame({
        "Portfólio ProPicks IA": retorno_acum,
        "IBOV": ibov_retorno_acum.squeeze()
    }))

    st.write("Retorno acumulado no período:")
    st.write(f"Portfólio: {retorno_acum[-1]:.2%}")
    st.write(f"IBOV: {ibov_retorno_acum[-1]:.2%}")

if __name__ == "__main__":
    main()
