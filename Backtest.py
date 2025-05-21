import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Definir os tickers da carteira
tickers = [
    'AGRO3.SA', 'BBAS3.SA', 'BBSE3.SA', 'BPAC11.SA', 'EGIE3.SA', 'ITUB3.SA',
    'PRIO3.SA', 'PSSA3.SA', 'SAPR3.SA', 'SBSP3.SA', 'VIVT3.SA', 'WEGE3.SA',
    'TOTS3.SA', 'B3SA3.SA', 'TAEE3.SA', 'CMIG3.SA'
]
benchmark = 'BOVA11.SA'

# Parâmetros do backtest
start_date = '2018-01-01'
end_date = pd.to_datetime('today').strftime('%Y-%m-%d')
aporte_mensal = 1000

# Baixar dados
precos = yf.download(tickers + [benchmark], start=start_date, end=end_date)['Adj Close'].dropna(how='all')
precos = precos.ffill()

# Gerar datas de aporte (primeiro dia útil de cada mês)
datas_aporte = pd.date_range(start=start_date, end=end_date, freq='BMS')
datas_aporte = [d for d in datas_aporte if d in precos.index]

# Inicializar carteira
carteira = {ticker: 0 for ticker in tickers}
historico_valor = []
historico_benchmark = []
registro_aportes = []

# Loop dos aportes
for data in datas_aporte:
    precos_dia = precos.loc[data, tickers]
    alocacao = 1 / len(tickers)

    # Valor para cada ativo
    valor_por_ativo = aporte_mensal * alocacao

    # Quantidade comprada de cada ativo
    for ticker in tickers:
        qtd = valor_por_ativo / precos_dia[ticker]
        carteira[ticker] += qtd
        registro_aportes.append({
            'Data': data,
            'Ticker': ticker,
            'Quantidade': qtd,
            'Preço': precos_dia[ticker],
            'Valor': qtd * precos_dia[ticker]
        })

    # Calcular valor da carteira na data
    precos_atuais = precos.loc[data, tickers]
    valor_carteira = sum([carteira[t] * precos_atuais[t] for t in tickers])
    valor_benchmark = (aporte_mensal * (datas_aporte.index(data) + 1)) * (precos.loc[data, benchmark] / precos.loc[datas_aporte[0], benchmark])

    historico_valor.append({'Data': data, 'Carteira': valor_carteira})
    historico_benchmark.append({'Data': data, 'Benchmark': valor_benchmark})

# Criar DataFrames dos históricos
df_valor = pd.DataFrame(historico_valor).set_index('Data')
df_benchmark = pd.DataFrame(historico_benchmark).set_index('Data')
df_aportes = pd.DataFrame(registro_aportes)

# Juntar os históricos
df_resultados = df_valor.join(df_benchmark)

# Calcular métricas
retornos = df_resultados['Carteira'].pct_change().dropna()
retornos_bench = df_resultados['Benchmark'].pct_change().dropna()

# CAGR
anos = (df_resultados.index[-1] - df_resultados.index[0]).days / 365
cagr_carteira = (df_resultados['Carteira'].iloc[-1] / aporte_mensal / len(datas_aporte)) ** (1/anos) - 1
cagr_bench = (df_resultados['Benchmark'].iloc[-1] / aporte_mensal / len(datas_aporte)) ** (1/anos) - 1

# Volatilidade anualizada
vol_carteira = retornos.std() * np.sqrt(12)
vol_bench = retornos_bench.std() * np.sqrt(12)

# Drawdown
def max_drawdown(serie):
    acumulado = serie.cummax()
    drawdown = (serie - acumulado) / acumulado
    return drawdown.min()

dd_carteira = max_drawdown(df_resultados['Carteira'])
dd_bench = max_drawdown(df_resultados['Benchmark'])

# Mostrar métricas
print("Métricas da Carteira:")
print(f"CAGR: {cagr_carteira:.2%}")
print(f"Volatilidade anualizada: {vol_carteira:.2%}")
print(f"Max Drawdown: {dd_carteira:.2%}")
print("\nMétricas do Benchmark (BOVA11):")
print(f"CAGR: {cagr_bench:.2%}")
print(f"Volatilidade anualizada: {vol_bench:.2%}")
print(f"Max Drawdown: {dd_bench:.2%}")

# Plotar evolução
plt.figure(figsize=(12, 6))
plt.plot(df_resultados.index, df_resultados['Carteira'], label='Carteira')
plt.plot(df_resultados.index, df_resultados['Benchmark'], label='BOVA11')
plt.title('Evolução do Valor da Carteira vs Benchmark')
plt.xlabel('Data')
plt.ylabel('Valor (R$)')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# Mostrar tabela de aportes
print("\nTabela de Aportes:")
print(df_aportes.groupby(['Data', 'Ticker'])[['Quantidade', 'Valor']].sum())
