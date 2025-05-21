from Picks import (
    obter_lista_acoes,
    carregar_dados_acao,
    calcular_metricas_fundamentalistas,
    calcular_pontuacao,
    obter_pesos_padrao,
    classificar_acao,
)
import streamlit as st
import pandas as pd
import numpy as np
import datetime
import yfinance as yf

st.title("Backtest com Aportes Mensais – Modelo Picks")

# Configurações
valor_aporte = 1000.0
limite_porc_ativo = 0.2
start_date = pd.to_datetime("2018-01-01")
end_date = pd.to_datetime(datetime.date.today())

# Lista fixa ou personalizável
tickers = [
    "AGRO3.SA", "BBAS3.SA", "BBSE3.SA", "BPAC11.SA", "EGIE3.SA",
    "ITUB3.SA", "PRIO3.SA", "PSSA3.SA", "SAPR3.SA", "SBSP3.SA",
    "VIVT3.SA", "WEGE3.SA", "TOTS3.SA", "B3SA3.SA", "TAEE3.SA", "CMIG3.SA"
]

st.subheader("Carteira Base")
st.write(", ".join(tickers))

if st.button("Executar Backtest"):
    datas_aporte = pd.date_range(start_date, end_date, freq="MS")
    patrimonio = 0
    carteira = {t: 0 for t in tickers}
    valor_carteira = []
    datas_carteira = []
    historico_pesos = []

    bova11 = yf.download("BOVA11.SA", start=start_date, end=end_date)["Adj Close"].ffill()
    bova11_qtd = 0
    bova11_patrimonio = []

    for data_aporte in datas_aporte:
        metricas = {}
        pontuacoes = {}

        # Avaliar cada ativo
        for ticker in tickers:
            dados = carregar_dados_acao(ticker)
            if dados is None:
                continue
            m = calcular_metricas_fundamentalistas(dados)
            p, p_final = calcular_pontuacao(m, obter_pesos_padrao())
            metricas[ticker] = m
            pontuacoes[ticker] = p_final

        # Selecionar os melhores (top N)
        df_pont = pd.Series(pontuacoes).dropna().sort_values(ascending=False)
        selecionados = df_pont[df_pont > 6]  # Critério de filtro
        if selecionados.empty:
            selecionados = df_pont.head(5)  # fallback

        pesos = (selecionados / selecionados.sum()).clip(upper=limite_porc_ativo)
        pesos = pesos / pesos.sum()

        # Preços no dia do aporte
        precos = yf.download(selecionados.index.tolist(), start=data_aporte, end=data_aporte + pd.offsets.MonthEnd(0))["Adj Close"].ffill().iloc[-1]

        # Valor atual de cada ativo
        valores_atuais = {t: carteira.get(t, 0) * precos.get(t, 0) for t in selecionados.index}
        total_antes = sum(valores_atuais.values())
        total_novo = total_antes + valor_aporte

        # Calcular novas quantidades
        alocacao_alvo = {t: pesos[t] * total_novo for t in selecionados.index}
        aporte_necessario = {t: max(0, alocacao_alvo[t] - valores_atuais.get(t, 0)) for t in selecionados.index}

        for t in selecionados.index:
            if precos[t] > 0:
                qtd = int(aporte_necessario[t] // precos[t])
                carteira[t] = carteira.get(t, 0) + qtd

        # Atualizar patrimônio
        precos_fim = precos
        patrimonio = sum(carteira.get(t, 0) * precos_fim.get(t, 0) for t in selecionados.index)

        valor_carteira.append(patrimonio)
        datas_carteira.append(data_aporte)
        historico_pesos.append(pesos.to_dict())

        # Benchmark
        preco_bova = bova11.asof(data_aporte)
        qtd_bova = valor_aporte // preco_bova if preco_bova > 0 else 0
        bova11_qtd += qtd_bova
        bova11_patrimonio.append(bova11_qtd * preco_bova)

    # Resultado
    df_result = pd.DataFrame({
        "Carteira Picks": valor_carteira,
        "BOVA11": bova11_patrimonio
    }, index=datas_carteira)

    st.line_chart(df_result)

    n_years = (df_result.index[-1] - df_result.index[0]).days / 365.25
    total_aportado = valor_aporte * len(datas_aporte)

    cagr_carteira = (df_result["Carteira Picks"].iloc[-1] / total_aportado) ** (1 / n_years) - 1
    cagr_bova = (df_result["BOVA11"].iloc[-1] / total_aportado) ** (1 / n_years) - 1

    st.metric("CAGR Carteira", f"{cagr_carteira:.2%}")
    st.metric("CAGR BOVA11", f"{cagr_bova:.2%}")

    st.subheader("Pesos por mês")
    st.write(historico_pesos)

    st.subheader("Composição final")
    precos_atuais = yf.download(tickers, period="1d")["Adj Close"].iloc[-1]
    carteira_final = {t: carteira[t] * precos_atuais.get(t, 0) for t in carteira if carteira[t] > 0}
    df_final = pd.DataFrame.from_dict(carteira_final, orient='index', columns=['Valor (R$)'])
    df_final['% da Carteira'] = df_final['Valor (R$)'] / df_final['Valor (R$)'].sum() * 100
    st.dataframe(df_final)

st.caption("Backtest com modelo fundamentalista Picks, aportes mensais e comparação com BOVA11.")
