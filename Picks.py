"""
Pro Picks IA - Simulação de Seleção de Melhores Ações Brasileiras
Aplicativo Streamlit que simula o funcionamento do Pro Picks IA
Versão com análise de carteira e recomendação de aportes
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import yfinance as yf
from datetime import datetime, timedelta
import time
import requests
import logging
import re
from PIL import Image
import io
import base64
import random

# Configuração da página
st.set_page_config(
    page_title="Pro Picks IA - Melhores Ações Brasileiras",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Diretório de dados
DATA_DIR = "dados"
os.makedirs(DATA_DIR, exist_ok=True)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Função auxiliar para converter índices Timestamp para string
def converter_indices_para_string(obj):
    """Converte índices e valores Timestamp para string em qualquer estrutura de dados"""
    if isinstance(obj, dict):
        # Converter chaves e valores Timestamp para string
        return {str(k) if hasattr(k, 'strftime') else k: converter_indices_para_string(v) 
                for k, v in obj.items()}
    elif isinstance(obj, list):
        return [converter_indices_para_string(item) for item in obj]
    elif isinstance(obj, pd.DataFrame):
        # Converter DataFrame para dicionário e depois tratar valores Timestamp
        df_dict = obj.reset_index().to_dict('records')
        return [converter_indices_para_string(record) for record in df_dict]
    elif isinstance(obj, pd.Series):
        # Converter Series para dicionário e depois tratar valores Timestamp
        series_dict = obj.reset_index().to_dict('records')
        return [converter_indices_para_string(record) for record in series_dict]
    elif hasattr(obj, 'strftime'):  # Verifica se é um objeto tipo datetime/Timestamp
        return str(obj)
    else:
        return obj

# Funções de utilidade
def carregar_dados_acao(ticker):
    """Carrega dados de uma ação específica"""
    try:
        arquivo = os.path.join(DATA_DIR, f"{ticker.replace('.', '_')}.json")
        if os.path.exists(arquivo):
            with open(arquivo, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Se o arquivo não existir, tenta coletar os dados
            return coletar_dados_acao(ticker)
    except Exception as e:
        st.error(f"Erro ao carregar dados para {ticker}: {e}")
        return None

def coletar_dados_acao(ticker):
    """Coleta dados de uma ação via API do Yahoo Finance"""
    try:
        with st.spinner(f"Coletando dados para {ticker}..."):
            acao = yf.Ticker(ticker)
            
            # Dicionário para armazenar todos os dados
            dados = {}
            
            # 1. Informações básicas
            info = acao.info
            dados['info'] = info
            
            # 2. Demonstrações financeiras
            try:
                # Converter índices para string antes de salvar
                income_stmt = acao.income_stmt
                if income_stmt is not None and not income_stmt.empty:
                    dados['income_statement'] = converter_indices_para_string(income_stmt)
                else:
                    dados['income_statement'] = {}
            except Exception as e:
                logger.warning(f"Erro ao obter demonstração de resultados para {ticker}: {e}")
                dados['income_statement'] = {}
                
            try:
                # Converter índices para string antes de salvar
                balance_sheet = acao.balance_sheet
                if balance_sheet is not None and not balance_sheet.empty:
                    dados['balance_sheet'] = converter_indices_para_string(balance_sheet)
                else:
                    dados['balance_sheet'] = {}
            except Exception as e:
                logger.warning(f"Erro ao obter balanço patrimonial para {ticker}: {e}")
                dados['balance_sheet'] = {}
                
            try:
                # Converter índices para string antes de salvar
                cashflow = acao.cashflow
                if cashflow is not None and not cashflow.empty:
                    dados['cash_flow'] = converter_indices_para_string(cashflow)
                else:
                    dados['cash_flow'] = {}
            except Exception as e:
                logger.warning(f"Erro ao obter fluxo de caixa para {ticker}: {e}")
                dados['cash_flow'] = {}
            
            # 3. Dados históricos (2 anos)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=2*365)
            try:
                hist = acao.history(start=start_date, end=end_date, interval="1d")
                if hist is not None and not hist.empty:
                    # Converter para registros com índices como string
                    dados['historical'] = converter_indices_para_string(hist)
                else:
                    dados['historical'] = []
            except Exception as e:
                logger.warning(f"Erro ao obter dados históricos para {ticker}: {e}")
                dados['historical'] = []
            
            # 4. Dividendos
            try:
                dividends = acao.dividends
                if dividends is not None and not dividends.empty:
                    # Converter índices Timestamp para string
                    dados['dividends'] = converter_indices_para_string(dividends)
                else:
                    dados['dividends'] = {}
            except Exception as e:
                logger.warning(f"Erro ao obter dividendos para {ticker}: {e}")
                dados['dividends'] = {}
            
            # Salvar dados em arquivo JSON
            arquivo = os.path.join(DATA_DIR, f"{ticker.replace('.', '_')}.json")
            with open(arquivo, 'w', encoding='utf-8') as f:
                json.dump(dados, f, default=str)
            
            return dados
    except Exception as e:
        st.error(f"Erro ao coletar dados para {ticker}: {e}")
        return None

def obter_lista_acoes():
    """Obtém a lista de ações do Ibovespa e outras ações relevantes do mercado brasileiro"""
    try:
        # Verificar se já existe um arquivo com a lista de ações
        arquivo_lista = os.path.join(DATA_DIR, "lista_acoes.json")
        if os.path.exists(arquivo_lista):
            with open(arquivo_lista, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Tentativa de obter composição do Ibovespa via yfinance
        ibov = yf.Ticker("^BVSP")
        ibov_components = ibov.components
        
        if ibov_components is not None and len(ibov_components) > 0:
            # Adicionar sufixo .SA para ações brasileiras
            acoes = [ticker + ".SA" for ticker in ibov_components]
        else:
            # Lista manual de ações do Ibovespa caso a API não retorne
            acoes_ibov = [
                "ABEV3.SA", "ALPA4.SA", "AMER3.SA", "ASAI3.SA", "AZUL4.SA", 
                "B3SA3.SA", "BBAS3.SA", "BBDC3.SA", "BBDC4.SA", "BBSE3.SA", 
                "BEEF3.SA", "BPAC11.SA", "BRAP4.SA", "BRFS3.SA", "BRKM5.SA", 
                "CASH3.SA", "CCRO3.SA", "CIEL3.SA", "CMIG4.SA", "CMIN3.SA", 
                "COGN3.SA", "CPFE3.SA", "CPLE6.SA", "CRFB3.SA", "CSAN3.SA", 
                "CSNA3.SA", "CVCB3.SA", "CYRE3.SA", "DXCO3.SA", "EGIE3.SA", 
                "ELET3.SA", "ELET6.SA", "EMBR3.SA", "ENEV3.SA", "ENGI11.SA", 
                "EQTL3.SA", "EZTC3.SA", "FLRY3.SA", "GGBR4.SA", "GOAU4.SA", 
                "GOLL4.SA", "HAPV3.SA", "HYPE3.SA", "IGTI11.SA", "IRBR3.SA", 
                "ITSA4.SA", "ITUB4.SA", "JBSS3.SA", "KLBN11.SA", "LREN3.SA", 
                "LWSA3.SA", "MGLU3.SA", "MRFG3.SA", "MRVE3.SA", "MULT3.SA", 
                "NTCO3.SA", "PCAR3.SA", "PETR3.SA", "PETR4.SA", "PETZ3.SA", 
                "PRIO3.SA", "RADL3.SA", "RAIL3.SA", "RAIZ4.SA", "RDOR3.SA", 
                "RENT3.SA", "RRRP3.SA", "SANB11.SA", "SBSP3.SA", "SLCE3.SA", 
                "SMTO3.SA", "SOMA3.SA", "SUZB3.SA", "TAEE11.SA", "TIMS3.SA", 
                "TOTS3.SA", "UGPA3.SA", "USIM5.SA", "VALE3.SA", "VBBR3.SA", 
                "VIIA3.SA", "VIVT3.SA", "WEGE3.SA", "YDUQ3.SA"
            ]
            
            # Adicionar outras ações relevantes fora do Ibovespa
            outras_acoes = [
                "AESB3.SA", "AURE3.SA", "AZEV4.SA", "BMGB4.SA", "BRSR6.SA",
                "CEAB3.SA", "CGAS5.SA", "CSMG3.SA", "CXSE3.SA", "DIRR3.SA",
                "EVEN3.SA", "FESA4.SA", "FRAS3.SA", "GRND3.SA", "HBOR3.SA",
                "JHSF3.SA", "KEPL3.SA", "LOGG3.SA", "MDIA3.SA", "MOVI3.SA",
                "ODPV3.SA", "POMO4.SA", "POSI3.SA", "PTBL3.SA", "QUAL3.SA",
                "ROMI3.SA", "SAPR11.SA", "SEER3.SA", "TASA4.SA", "TGMA3.SA",
                "TUPY3.SA", "VULC3.SA", "WIZS3.SA"
            ]
            
            acoes = acoes_ibov + outras_acoes
        
        # Salvar lista de ações
        with open(arquivo_lista, 'w', encoding='utf-8') as f:
            json.dump(acoes, f)
        
        return acoes
    except Exception as e:
        st.error(f"Erro ao obter lista de ações: {e}")
        # Lista de fallback em caso de erro
        acoes_fallback = [
            "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "B3SA3.SA",
            "ABEV3.SA", "WEGE3.SA", "RENT3.SA", "BBAS3.SA", "SUZB3.SA"
        ]
        return acoes_fallback

def obter_dados_ibovespa():
    """Obtém dados históricos do Ibovespa para comparação"""
    try:
        arquivo = os.path.join(DATA_DIR, "ibovespa_historico.csv")
        if os.path.exists(arquivo):
            return pd.read_csv(arquivo, index_col=0, parse_dates=True)
        
        with st.spinner("Coletando dados históricos do Ibovespa..."):
            ibov = yf.Ticker("^BVSP")
            end_date = datetime.now()
            start_date = end_date - timedelta(days=2*365)
            hist = ibov.history(start=start_date, end=end_date, interval="1d")
            
            # Salvar dados em arquivo CSV
            hist.to_csv(arquivo)
            
            return hist
    except Exception as e:
        st.error(f"Erro ao obter dados do Ibovespa: {e}")
        return None

def calcular_metricas_fundamentalistas(dados):
    """Calcula métricas fundamentalistas a partir dos dados da ação"""
    metricas = {}
    
    try:
        # Extrair informações básicas
        info = dados.get('info', {})
        income_stmt = dados.get('income_statement', {})
        balance = dados.get('balance_sheet', {})
        cash_flow = dados.get('cash_flow', {})
        
        # 1. Métricas de Lucratividade
        # ROE (Retorno sobre Patrimônio)
        try:
            # Método 1: Usando info diretamente
            if 'netIncome' in info and 'totalStockholderEquity' in info and info['totalStockholderEquity'] != 0:
                metricas['ROE'] = (info['netIncome'] / info['totalStockholderEquity']) * 100
            # Método 2: Usando campos alternativos
            elif 'returnOnEquity' in info:
                metricas['ROE'] = info['returnOnEquity'] * 100
            # Método 3: Calculando a partir das demonstrações financeiras
            elif isinstance(income_stmt, list) and isinstance(balance, list) and len(income_stmt) > 0 and len(balance) > 0:
                # Tentar encontrar lucro líquido e patrimônio líquido nas demonstrações
                lucro_liquido = None
                patrimonio_liquido = None
                
                # Procurar em income_stmt
                for item in income_stmt:
                    if 'Net Income' in item or 'NetIncome' in item:
                        lucro_liquido = item.get('Net Income', item.get('NetIncome'))
                        break
                
                # Procurar em balance
                for item in balance:
                    if 'Total Stockholder Equity' in item or 'TotalStockholderEquity' in item:
                        patrimonio_liquido = item.get('Total Stockholder Equity', item.get('TotalStockholderEquity'))
                        break
                
                if lucro_liquido is not None and patrimonio_liquido is not None and float(patrimonio_liquido) != 0:
                    metricas['ROE'] = (float(lucro_liquido) / float(patrimonio_liquido)) * 100
                else:
                    metricas['ROE'] = None
            else:
                metricas['ROE'] = None
        except Exception as e:
            logger.warning(f"Erro ao calcular ROE: {e}")
            metricas['ROE'] = None
        
        # ROIC (Retorno sobre Capital Investido)
        try:
            # Método 1: Usando info diretamente
            if 'ebit' in info and 'totalAssets' in info and 'totalCurrentLiabilities' in info:
                capital_investido = info['totalAssets'] - info['totalCurrentLiabilities']
                if capital_investido != 0:
                    metricas['ROIC'] = (info['ebit'] * (1 - 0.34)) / capital_investido * 100  # Considerando alíquota de 34%
                else:
                    metricas['ROIC'] = None
            # Método 2: Calculando a partir das demonstrações financeiras
            elif isinstance(income_stmt, list) and isinstance(balance, list) and len(income_stmt) > 0 and len(balance) > 0:
                # Tentar encontrar EBIT, ativos totais e passivos circulantes nas demonstrações
                ebit = None
                ativos_totais = None
                passivos_circulantes = None
                
                # Procurar em income_stmt
                for item in income_stmt:
                    if 'EBIT' in item or 'OperatingIncome' in item:
                        ebit = item.get('EBIT', item.get('OperatingIncome'))
                        break
                
                # Procurar em balance
                for item in balance:
                    if 'Total Assets' in item or 'TotalAssets' in item:
                        ativos_totais = item.get('Total Assets', item.get('TotalAssets'))
                    if 'Total Current Liabilities' in item or 'TotalCurrentLiabilities' in item:
                        passivos_circulantes = item.get('Total Current Liabilities', item.get('TotalCurrentLiabilities'))
                    if ativos_totais is not None and passivos_circulantes is not None:
                        break
                
                if ebit is not None and ativos_totais is not None and passivos_circulantes is not None:
                    capital_investido = float(ativos_totais) - float(passivos_circulantes)
                    if capital_investido != 0:
                        metricas['ROIC'] = (float(ebit) * (1 - 0.34)) / capital_investido * 100
                    else:
                        metricas['ROIC'] = None
                else:
                    metricas['ROIC'] = None
            else:
                metricas['ROIC'] = None
        except Exception as e:
            logger.warning(f"Erro ao calcular ROIC: {e}")
            metricas['ROIC'] = None
        
        # Margem Líquida
        try:
            # Método 1: Usando info diretamente
            if 'netIncome' in info and 'totalRevenue' in info and info['totalRevenue'] != 0:
                metricas['MargemLiquida'] = (info['netIncome'] / info['totalRevenue']) * 100
            # Método 2: Usando campos alternativos
            elif 'profitMargins' in info:
                metricas['MargemLiquida'] = info['profitMargins'] * 100
            # Método 3: Calculando a partir das demonstrações financeiras
            elif isinstance(income_stmt, list) and len(income_stmt) > 0:
                # Tentar encontrar lucro líquido e receita total nas demonstrações
                lucro_liquido = None
                receita_total = None
                
                # Procurar em income_stmt
                for item in income_stmt:
                    if 'Net Income' in item or 'NetIncome' in item:
                        lucro_liquido = item.get('Net Income', item.get('NetIncome'))
                    if 'Total Revenue' in item or 'TotalRevenue' in item:
                        receita_total = item.get('Total Revenue', item.get('TotalRevenue'))
                    if lucro_liquido is not None and receita_total is not None:
                        break
                
                if lucro_liquido is not None and receita_total is not None and float(receita_total) != 0:
                    metricas['MargemLiquida'] = (float(lucro_liquido) / float(receita_total)) * 100
                else:
                    metricas['MargemLiquida'] = None
            else:
                metricas['MargemLiquida'] = None
        except Exception as e:
            logger.warning(f"Erro ao calcular Margem Líquida: {e}")
            metricas['MargemLiquida'] = None
        
        # 2. Métricas de Avaliação
        # P/L (Preço/Lucro)
        metricas['PL'] = info.get('trailingPE', None)
        
        # P/VP (Preço/Valor Patrimonial)
        metricas['PVP'] = info.get('priceToBook', None)
        
        # EV/EBITDA
        metricas['EV_EBITDA'] = info.get('enterpriseToEbitda', None)
        
        # Dividend Yield
        metricas['DividendYield'] = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
        
        # 3. Métricas de Saúde Financeira
        # Dívida/Patrimônio
        try:
            # Método 1: Usando info diretamente
            if 'totalDebt' in info and 'totalStockholderEquity' in info and info['totalStockholderEquity'] != 0:
                metricas['DividaPatrimonio'] = info['totalDebt'] / info['totalStockholderEquity']
            # Método 2: Usando campos alternativos
            elif 'debtToEquity' in info:
                metricas['DividaPatrimonio'] = info['debtToEquity'] / 100  # Normalmente é reportado em percentual
            # Método 3: Calculando a partir das demonstrações financeiras
            elif isinstance(balance, list) and len(balance) > 0:
                # Tentar encontrar dívida total e patrimônio líquido nas demonstrações
                divida_total = None
                patrimonio_liquido = None
                
                # Procurar em balance
                for item in balance:
                    if 'Total Debt' in item or 'TotalDebt' in item or 'Long Term Debt' in item:
                        divida_total = item.get('Total Debt', item.get('TotalDebt', item.get('Long Term Debt')))
                    if 'Total Stockholder Equity' in item or 'TotalStockholderEquity' in item:
                        patrimonio_liquido = item.get('Total Stockholder Equity', item.get('TotalStockholderEquity'))
                    if divida_total is not None and patrimonio_liquido is not None:
                        break
                
                if divida_total is not None and patrimonio_liquido is not None and float(patrimonio_liquido) != 0:
                    metricas['DividaPatrimonio'] = float(divida_total) / float(patrimonio_liquido)
                else:
                    metricas['DividaPatrimonio'] = None
            else:
                metricas['DividaPatrimonio'] = None
        except Exception as e:
            logger.warning(f"Erro ao calcular Dívida/Patrimônio: {e}")
            metricas['DividaPatrimonio'] = None
        
        # Liquidez Corrente
        if 'totalCurrentAssets' in info and 'totalCurrentLiabilities' in info and info['totalCurrentLiabilities'] != 0:
            metricas['LiquidezCorrente'] = info['totalCurrentAssets'] / info['totalCurrentLiabilities']
        else:
            metricas['LiquidezCorrente'] = None
        
        # 4. Crescimento
        # Crescimento de Lucros (TTM)
        if 'earningsGrowth' in info:
            metricas['CrescimentoLucros'] = info['earningsGrowth'] * 100 if info['earningsGrowth'] else None
        else:
            metricas['CrescimentoLucros'] = None
        
        # 5. Outras Métricas
        # Payout
        if 'payoutRatio' in info:
            metricas['Payout'] = info['payoutRatio'] * 100 if info['payoutRatio'] else 0
        else:
            metricas['Payout'] = 0
        
        # Setor
        metricas['Setor'] = info.get('sector', 'N/A')
        
        # Indústria
        metricas['Industria'] = info.get('industry', 'N/A')
        
        # Nome da Empresa
        metricas['Nome'] = info.get('longName', info.get('shortName', 'N/A'))
        
        # Preço Atual
        metricas['PrecoAtual'] = info.get('currentPrice', info.get('regularMarketPrice', 0))
        
        # Market Cap
        metricas['MarketCap'] = info.get('marketCap', 0)
        
        # Volume Médio (3 meses)
        metricas['VolumeMedia3M'] = info.get('averageVolume3Month', 0)
        
        return metricas
    except Exception as e:
        st.error(f"Erro ao calcular métricas fundamentalistas: {e}")
        return {}

def calcular_pontuacao(metricas, pesos):
    """Calcula a pontuação da ação com base nas métricas e pesos definidos"""
    pontuacao = {}
    pontuacao_total = 0
    peso_total = 0
    
    # 1. Demonstrações Financeiras e Lucratividade
    # ROE
    if metricas.get('ROE') is not None:
        roe = metricas['ROE']
        if roe > 15:
            pontuacao['ROE'] = 10
        elif roe > 12:
            pontuacao['ROE'] = 8
        elif roe > 10:
            pontuacao['ROE'] = 6
        elif roe > 5:
            pontuacao['ROE'] = 4
        elif roe > 0:
            pontuacao['ROE'] = 2
        else:
            pontuacao['ROE'] = 0
        
        pontuacao_total += pontuacao['ROE'] * pesos['ROE']
        peso_total += pesos['ROE']
    
    # ROIC
    if metricas.get('ROIC') is not None:
        roic = metricas['ROIC']
        if roic > 12:
            pontuacao['ROIC'] = 10
        elif roic > 10:
            pontuacao['ROIC'] = 8
        elif roic > 7:
            pontuacao['ROIC'] = 6
        elif roic > 5:
            pontuacao['ROIC'] = 4
        elif roic > 0:
            pontuacao['ROIC'] = 2
        else:
            pontuacao['ROIC'] = 0
        
        pontuacao_total += pontuacao['ROIC'] * pesos['ROIC']
        peso_total += pesos['ROIC']
    
    # Margem Líquida
    if metricas.get('MargemLiquida') is not None:
        margem = metricas['MargemLiquida']
        if margem > 20:
            pontuacao['MargemLiquida'] = 10
        elif margem > 15:
            pontuacao['MargemLiquida'] = 8
        elif margem > 10:
            pontuacao['MargemLiquida'] = 6
        elif margem > 5:
            pontuacao['MargemLiquida'] = 4
        elif margem > 0:
            pontuacao['MargemLiquida'] = 2
        else:
            pontuacao['MargemLiquida'] = 0
        
        pontuacao_total += pontuacao['MargemLiquida'] * pesos['MargemLiquida']
        peso_total += pesos['MargemLiquida']
    
    # Crescimento de Lucros
    if metricas.get('CrescimentoLucros') is not None:
        crescimento = metricas['CrescimentoLucros']
        if crescimento > 15:
            pontuacao['CrescimentoLucros'] = 10
        elif crescimento > 10:
            pontuacao['CrescimentoLucros'] = 8
        elif crescimento > 5:
            pontuacao['CrescimentoLucros'] = 6
        elif crescimento > 0:
            pontuacao['CrescimentoLucros'] = 4
        elif crescimento > -5:
            pontuacao['CrescimentoLucros'] = 2
        else:
            pontuacao['CrescimentoLucros'] = 0
        
        pontuacao_total += pontuacao['CrescimentoLucros'] * pesos['CrescimentoLucros']
        peso_total += pesos['CrescimentoLucros']
    
    # 2. Avaliação e Múltiplos
    # P/L
    if metricas.get('PL') is not None:
        pl = metricas['PL']
        if pl < 0:  # Lucro negativo
            pontuacao['PL'] = 0
        elif pl < 10:
            pontuacao['PL'] = 10
        elif pl < 15:
            pontuacao['PL'] = 8
        elif pl < 20:
            pontuacao['PL'] = 6
        elif pl < 25:
            pontuacao['PL'] = 4
        elif pl < 30:
            pontuacao['PL'] = 2
        else:
            pontuacao['PL'] = 0
        
        pontuacao_total += pontuacao['PL'] * pesos['PL']
        peso_total += pesos['PL']
    
    # P/VP
    if metricas.get('PVP') is not None:
        pvp = metricas['PVP']
        if pvp < 0:  # Patrimônio negativo
            pontuacao['PVP'] = 0
        elif pvp < 1:
            pontuacao['PVP'] = 10
        elif pvp < 1.5:
            pontuacao['PVP'] = 8
        elif pvp < 2:
            pontuacao['PVP'] = 6
        elif pvp < 2.5:
            pontuacao['PVP'] = 4
        elif pvp < 3:
            pontuacao['PVP'] = 2
        else:
            pontuacao['PVP'] = 0
        
        pontuacao_total += pontuacao['PVP'] * pesos['PVP']
        peso_total += pesos['PVP']
    
    # EV/EBITDA
    if metricas.get('EV_EBITDA') is not None:
        ev_ebitda = metricas['EV_EBITDA']
        if ev_ebitda < 0:  # EBITDA negativo
            pontuacao['EV_EBITDA'] = 0
        elif ev_ebitda < 6:
            pontuacao['EV_EBITDA'] = 10
        elif ev_ebitda < 8:
            pontuacao['EV_EBITDA'] = 8
        elif ev_ebitda < 10:
            pontuacao['EV_EBITDA'] = 6
        elif ev_ebitda < 12:
            pontuacao['EV_EBITDA'] = 4
        elif ev_ebitda < 15:
            pontuacao['EV_EBITDA'] = 2
        else:
            pontuacao['EV_EBITDA'] = 0
        
        pontuacao_total += pontuacao['EV_EBITDA'] * pesos['EV_EBITDA']
        peso_total += pesos['EV_EBITDA']
    
    # Dividend Yield
    if metricas.get('DividendYield') is not None:
        dy = metricas['DividendYield']
        if dy > 5:
            pontuacao['DividendYield'] = 10
        elif dy > 4:
            pontuacao['DividendYield'] = 8
        elif dy > 3:
            pontuacao['DividendYield'] = 6
        elif dy > 2:
            pontuacao['DividendYield'] = 4
        elif dy > 1:
            pontuacao['DividendYield'] = 2
        else:
            pontuacao['DividendYield'] = 0
        
        pontuacao_total += pontuacao['DividendYield'] * pesos['DividendYield']
        peso_total += pesos['DividendYield']
    
    # 3. Saúde Financeira e Liquidez
    # Dívida/Patrimônio
    if metricas.get('DividaPatrimonio') is not None:
        div_pat = metricas['DividaPatrimonio']
        if div_pat < 0:  # Patrimônio negativo
            pontuacao['DividaPatrimonio'] = 0
        elif div_pat < 0.5:
            pontuacao['DividaPatrimonio'] = 10
        elif div_pat < 1:
            pontuacao['DividaPatrimonio'] = 8
        elif div_pat < 1.5:
            pontuacao['DividaPatrimonio'] = 6
        elif div_pat < 2:
            pontuacao['DividaPatrimonio'] = 4
        elif div_pat < 3:
            pontuacao['DividaPatrimonio'] = 2
        else:
            pontuacao['DividaPatrimonio'] = 0
        
        pontuacao_total += pontuacao['DividaPatrimonio'] * pesos['DividaPatrimonio']
        peso_total += pesos['DividaPatrimonio']
    
    # Liquidez Corrente
    if metricas.get('LiquidezCorrente') is not None:
        liq_cor = metricas['LiquidezCorrente']
        if liq_cor > 2:
            pontuacao['LiquidezCorrente'] = 10
        elif liq_cor > 1.5:
            pontuacao['LiquidezCorrente'] = 8
        elif liq_cor > 1.2:
            pontuacao['LiquidezCorrente'] = 6
        elif liq_cor > 1:
            pontuacao['LiquidezCorrente'] = 4
        elif liq_cor > 0.8:
            pontuacao['LiquidezCorrente'] = 2
        else:
            pontuacao['LiquidezCorrente'] = 0
        
        pontuacao_total += pontuacao['LiquidezCorrente'] * pesos['LiquidezCorrente']
        peso_total += pesos['LiquidezCorrente']
    
    # Payout
    if metricas.get('Payout') is not None:
        payout = metricas['Payout']
        if payout < 0:  # Lucro negativo
            pontuacao['Payout'] = 0
        elif payout < 30:
            pontuacao['Payout'] = 6  # Baixo payout pode indicar retenção para crescimento
        elif payout < 50:
            pontuacao['Payout'] = 8
        elif payout < 70:
            pontuacao['Payout'] = 10  # Payout ideal
        elif payout < 90:
            pontuacao['Payout'] = 6
        elif payout < 100:
            pontuacao['Payout'] = 4
        else:
            pontuacao['Payout'] = 2  # Payout acima de 100% pode ser insustentável
        
        pontuacao_total += pontuacao['Payout'] * pesos['Payout']
        peso_total += pesos['Payout']
    
    # Calcular pontuação final normalizada (0-10)
    if peso_total > 0:
        pontuacao_final = pontuacao_total / peso_total
    else:
        pontuacao_final = 0
    
    return pontuacao, pontuacao_final

def classificar_acao(pontuacao_final, metricas):
    """Classifica a ação em uma das categorias do Pro Picks"""
    # Definir critérios para cada categoria
    categorias = []
    
    # Melhores Ações Brasileiras (pontuação geral alta)
    if pontuacao_final >= 7:
        categorias.append("Melhores Ações Brasileiras")
    
    # Empresas Sólidas (boa lucratividade e solidez financeira)
    if (metricas.get('ROE', 0) or 0) > 10 and (metricas.get('DividaPatrimonio', 0) or 0) < 1.5:
        categorias.append("Empresas Sólidas")
    
    # Ações Defensivas (bom dividend yield e baixa volatilidade)
    if (metricas.get('DividendYield', 0) or 0) > 3 and (metricas.get('Payout', 0) or 0) < 80:
        categorias.append("Ações Defensivas")
    
    # Ações Baratas (baixos múltiplos)
    if ((metricas.get('PL', 0) or 0) < 15 and (metricas.get('PL', 0) or 0) > 0) or ((metricas.get('PVP', 0) or 0) < 1.5 and (metricas.get('PVP', 0) or 0) > 0):
        categorias.append("Ações Baratas")
    
    # Se não se encaixar em nenhuma categoria específica
    if not categorias:
        if pontuacao_final >= 5:
            categorias.append("Potencial Moderado")
        else:
            categorias.append("Baixo Potencial")
    
    return categorias

def classificar_cenario_macroeconomico():
    """Classifica o cenário macroeconômico atual"""
    # Em uma implementação real, isso seria baseado em dados do Banco Central, IBGE, etc.
    # Para esta simulação, vamos permitir que o usuário selecione o cenário
    
    return st.sidebar.selectbox(
        "Cenário Macroeconômico Atual",
        ["Expansão", "Desaceleração", "Recessão", "Recuperação"],
        index=1,  # Default: Desaceleração
        help="Selecione o cenário macroeconômico atual para ajustar as recomendações"
    )

def sugerir_alocacao(perfil, cenario):
    """Sugere alocação baseada no perfil do investidor e cenário macroeconômico"""
    alocacao = {}
    
    if perfil == "Conservador":
        if cenario == "Expansão":
            alocacao = {
                "Ações Defensivas": "60%",
                "Empresas Sólidas": "30%",
                "Ações Baratas": "10%",
                "Melhores Ações": "0%"
            }
        elif cenario == "Desaceleração":
            alocacao = {
                "Ações Defensivas": "70%",
                "Empresas Sólidas": "20%",
                "Ações Baratas": "10%",
                "Melhores Ações": "0%"
            }
        elif cenario == "Recessão":
            alocacao = {
                "Ações Defensivas": "80%",
                "Empresas Sólidas": "15%",
                "Ações Baratas": "5%",
                "Melhores Ações": "0%"
            }
        elif cenario == "Recuperação":
            alocacao = {
                "Ações Defensivas": "65%",
                "Empresas Sólidas": "25%",
                "Ações Baratas": "10%",
                "Melhores Ações": "0%"
            }
    
    elif perfil == "Moderado":
        if cenario == "Expansão":
            alocacao = {
                "Ações Defensivas": "30%",
                "Empresas Sólidas": "40%",
                "Ações Baratas": "15%",
                "Melhores Ações": "15%"
            }
        elif cenario == "Desaceleração":
            alocacao = {
                "Ações Defensivas": "40%",
                "Empresas Sólidas": "35%",
                "Ações Baratas": "15%",
                "Melhores Ações": "10%"
            }
        elif cenario == "Recessão":
            alocacao = {
                "Ações Defensivas": "50%",
                "Empresas Sólidas": "30%",
                "Ações Baratas": "15%",
                "Melhores Ações": "5%"
            }
        elif cenario == "Recuperação":
            alocacao = {
                "Ações Defensivas": "25%",
                "Empresas Sólidas": "35%",
                "Ações Baratas": "20%",
                "Melhores Ações": "20%"
            }
    
    elif perfil == "Agressivo":
        if cenario == "Expansão":
            alocacao = {
                "Ações Defensivas": "10%",
                "Empresas Sólidas": "25%",
                "Ações Baratas": "25%",
                "Melhores Ações": "40%"
            }
        elif cenario == "Desaceleração":
            alocacao = {
                "Ações Defensivas": "20%",
                "Empresas Sólidas": "30%",
                "Ações Baratas": "25%",
                "Melhores Ações": "25%"
            }
        elif cenario == "Recessão":
            alocacao = {
                "Ações Defensivas": "30%",
                "Empresas Sólidas": "30%",
                "Ações Baratas": "30%",
                "Melhores Ações": "10%"
            }
        elif cenario == "Recuperação":
            alocacao = {
                "Ações Defensivas": "5%",
                "Empresas Sólidas": "25%",
                "Ações Baratas": "30%",
                "Melhores Ações": "40%"
            }
    
    return alocacao

def gerar_grafico_pontuacao(pontuacoes, titulo):
    """Gera gráfico de barras para visualização das pontuações"""
    # Ordenar pontuações
    pontuacoes_ordenadas = sorted(pontuacoes.items(), key=lambda x: x[1], reverse=True)
    
    # Criar dataframe
    df = pd.DataFrame(pontuacoes_ordenadas, columns=['Critério', 'Pontuação'])
    
    # Criar gráfico com Plotly
    fig = px.bar(
        df, 
        x='Critério', 
        y='Pontuação',
        title=titulo,
        color='Pontuação',
        color_continuous_scale='RdYlGn',
        range_y=[0, 10]
    )
    
    fig.update_layout(
        xaxis_title="Critério",
        yaxis_title="Pontuação (0-10)",
        height=400
    )
    
    return fig

def gerar_grafico_radar(pontuacoes, titulo):
    """Gera gráfico radar para visualização das pontuações"""
    # Preparar dados
    categorias = list(pontuacoes.keys())
    valores = list(pontuacoes.values())
    
    # Criar gráfico radar
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=valores,
        theta=categorias,
        fill='toself',
        name='Pontuação'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 10]
            )
        ),
        title=titulo,
        height=500
    )
    
    return fig

def gerar_grafico_alocacao(alocacao, titulo):
    """Gera gráfico de pizza para visualização da alocação sugerida"""
    # Preparar dados
    categorias = list(alocacao.keys())
    valores = [float(v.replace('%', '')) for v in alocacao.values()]
    
    # Criar gráfico de pizza
    fig = px.pie(
        names=categorias,
        values=valores,
        title=titulo,
        color_discrete_sequence=px.colors.sequential.RdBu
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    
    fig.update_layout(
        height=400
    )
    
    return fig

def formatar_metrica(valor, formato):
    """Formata uma métrica para exibição"""
    if valor is None:
        return "N/A"
    
    if formato == "percentual":
        return f"{valor:.2f}%"
    elif formato == "decimal":
        return f"{valor:.2f}"
    elif formato == "monetario":
        return f"R$ {valor:.2f}"
    elif formato == "inteiro":
        return f"{int(valor):,}".replace(',', '.')
    else:
        return str(valor)

def criar_carteira_recomendada(resultados, categoria, max_acoes=5):
    """Cria uma carteira recomendada com base nos resultados e categoria"""
    # Filtrar ações da categoria especificada
    acoes_categoria = [r for r in resultados if categoria in r['Categorias']]
    
    # Ordenar por pontuação
    acoes_ordenadas = sorted(acoes_categoria, key=lambda x: x['PontuacaoFinal'], reverse=True)
    
    # Limitar ao número máximo de ações
    return acoes_ordenadas[:max_acoes]

# Definição dos pesos padrão para os critérios
def obter_pesos_padrao():
    return {
        # Demonstrações Financeiras e Lucratividade (25%)
        'ROE': 6,
        'ROIC': 6,
        'MargemLiquida': 7,
        'CrescimentoLucros': 6,
        
        # Avaliação e Múltiplos (20%)
        'PL': 7,
        'PVP': 5,
        'EV_EBITDA': 5,
        'DividendYield': 3,
        
        # Saúde Financeira e Liquidez (20%)
        'DividaPatrimonio': 7,
        'LiquidezCorrente': 5,
        'Payout': 3,
        
        # Outros critérios não implementados nesta versão simplificada
        # seriam os 35% restantes
    }

# Função para validar tickers inseridos pelo usuário
def validar_ticker(ticker):
    """Valida se o ticker está no formato correto para o mercado brasileiro"""
    # Verifica se o ticker já tem o sufixo .SA
    if ticker.endswith('.SA'):
        return ticker
    
    # Verifica se o ticker está no formato padrão brasileiro (4 letras + 1 número)
    padrao = re.compile(r'^[A-Z]{4}\d{1,2}$', re.IGNORECASE)
    if padrao.match(ticker):
        return f"{ticker.upper()}.SA"
    
    # Se não estiver em nenhum formato reconhecido, retorna None
    return None

# Função para analisar a carteira atual e recomendar aportes
def analisar_carteira_para_aporte(resultados, carteira_atual, perfil, cenario, valor_aporte):
    """Analisa a carteira atual e sugere recomendações de aporte
    
    Args:
        resultados (list): Lista de resultados da análise de ações
        carteira_atual (dict): Dicionário com tickers e percentuais da carteira atual
        perfil (str): Perfil do investidor
        cenario (str): Cenário macroeconômico
        valor_aporte (float): Valor do aporte em reais
        
    Returns:
        dict: Recomendações de aporte
    """
    # Obter alocação ideal
    alocacao_ideal = sugerir_alocacao(perfil, cenario)
    
    # Converter percentuais para valores numéricos
    alocacao_ideal_num = {k: float(v.replace('%', '')) for k, v in alocacao_ideal.items()}
    
    # Mapear ações para categorias
    acoes_por_categoria = {}
    for categoria in alocacao_ideal.keys():
        if categoria == "Melhores Ações":
            categoria_busca = "Melhores Ações Brasileiras"
        else:
            categoria_busca = categoria
        
        acoes_categoria = [r for r in resultados if categoria_busca in r['Categorias']]
        acoes_por_categoria[categoria] = sorted(acoes_categoria, key=lambda x: x['PontuacaoFinal'], reverse=True)
    
    # Analisar diferenças entre carteira atual e ideal
    categorias_atuais = {}
    for ticker, percentual in carteira_atual.items():
        # Encontrar a ação nos resultados
        acao = next((r for r in resultados if r['Ticker'] == ticker), None)
        if acao:
            # Identificar categorias da ação
            for categoria in acao['Categorias']:
                categoria_map = categoria
                if categoria == "Melhores Ações Brasileiras":
                    categoria_map = "Melhores Ações"
                
                if categoria_map in categorias_atuais:
                    categorias_atuais[categoria_map] += percentual
                else:
                    categorias_atuais[categoria_map] = percentual
    
    # Preencher categorias ausentes com 0
    for categoria in alocacao_ideal.keys():
        if categoria not in categorias_atuais:
            categorias_atuais[categoria] = 0
    
    # Calcular diferenças
    diferencas = {}
    for categoria, percentual_ideal in alocacao_ideal_num.items():
        percentual_atual = categorias_atuais.get(categoria, 0)
        diferencas[categoria] = percentual_ideal - percentual_atual
    
    # Calcular recomendações de aporte
    recomendacoes = {}
    
    # Normalizar diferenças positivas para distribuir o aporte
    diferencas_positivas = {k: v for k, v in diferencas.items() if v > 0}
    soma_diferencas_positivas = sum(diferencas_positivas.values())
    
    if soma_diferencas_positivas > 0:
        # Distribuir o aporte proporcionalmente às diferenças positivas
        for categoria, diferenca in diferencas_positivas.items():
            percentual_aporte = diferenca / soma_diferencas_positivas
            valor_categoria = valor_aporte * percentual_aporte
            
            # Selecionar as melhores ações da categoria para aporte
            acoes_recomendadas = []
            if categoria in acoes_por_categoria and len(acoes_por_categoria[categoria]) > 0:
                # Pegar as 3 melhores ações da categoria
                melhores_acoes = acoes_por_categoria[categoria][:3]
                
                # Verificar quais dessas ações já estão na carteira e quais são novas
                acoes_existentes = [a for a in melhores_acoes if a['Ticker'] in carteira_atual]
                acoes_novas = [a for a in melhores_acoes if a['Ticker'] not in carteira_atual]
                
                # Priorizar ações existentes com baixa representação e depois novas ações
                for acao in acoes_existentes:
                    if carteira_atual.get(acao['Ticker'], 0) < 5:  # Se a ação tem menos de 5% na carteira
                        acoes_recomendadas.append(acao)
                
                # Adicionar novas ações promissoras
                for acao in acoes_novas:
                    acoes_recomendadas.append(acao)
                
                # Limitar a 3 recomendações por categoria
                acoes_recomendadas = acoes_recomendadas[:3]
                
                # Distribuir o valor da categoria entre as ações recomendadas
                if acoes_recomendadas:
                    valor_por_acao = valor_categoria / len(acoes_recomendadas)
                    for acao in acoes_recomendadas:
                        recomendacoes[acao['Ticker']] = {
                            'Nome': acao['Nome'],
                            'Valor': valor_por_acao,
                            'Percentual': percentual_aporte * 100 / len(acoes_recomendadas),
                            'Categoria': categoria,
                            'Pontuacao': acao['PontuacaoFinal'],
                            'Motivo': gerar_motivo_recomendacao(acao, categoria, carteira_atual.get(acao['Ticker'], 0))
                        }
    
    # MODIFICAÇÃO: Sempre sugerir ações, mesmo quando não há diferenças positivas
    if not recomendacoes:
        # Selecionar as melhores ações de cada categoria com base nos critérios fundamentalistas, técnicos e macroeconômicos
        melhores_acoes_geral = []
        
        # Obter as melhores ações de cada categoria
        for categoria, acoes in acoes_por_categoria.items():
            if acoes:
                # Pegar as 2 melhores ações de cada categoria
                melhores_acoes_geral.extend(acoes[:2])
        
        # Ordenar por pontuação final (combinação de critérios fundamentalistas, técnicos e macroeconômicos)
        melhores_acoes_geral = sorted(melhores_acoes_geral, key=lambda x: x['PontuacaoFinal'], reverse=True)
        
        # Limitar a 5 recomendações no total
        melhores_acoes_geral = melhores_acoes_geral[:5]
        
        # Distribuir o valor do aporte igualmente entre as ações selecionadas
        if melhores_acoes_geral:
            valor_por_acao = valor_aporte / len(melhores_acoes_geral)
            percentual_por_acao = 100 / len(melhores_acoes_geral)
            
            for acao in melhores_acoes_geral:
                # Determinar a categoria principal da ação
                categoria_principal = acao['Categorias'][0]
                if "Melhores Ações Brasileiras" in acao['Categorias']:
                    categoria_principal = "Melhores Ações"
                elif len(acao['Categorias']) > 0:
                    categoria_principal = acao['Categorias'][0]
                    if categoria_principal == "Melhores Ações Brasileiras":
                        categoria_principal = "Melhores Ações"
                
                recomendacoes[acao['Ticker']] = {
                    'Nome': acao['Nome'],
                    'Valor': valor_por_acao,
                    'Percentual': percentual_por_acao,
                    'Categoria': categoria_principal,
                    'Pontuacao': acao['PontuacaoFinal'],
                    'Motivo': gerar_motivo_recomendacao_alternativo(acao, categoria_principal, carteira_atual.get(acao['Ticker'], 0), cenario)
                }
    
    return {
        'carteira_atual': categorias_atuais,
        'alocacao_ideal': alocacao_ideal_num,
        'diferencas': diferencas,
        'recomendacoes': recomendacoes
    }

def gerar_motivo_recomendacao(acao, categoria, percentual_atual):
    """Gera um motivo personalizado para a recomendação de aporte"""
    motivos = []
    
    # Motivos baseados na categoria
    if categoria == "Ações Defensivas":
        motivos.append(f"Excelente dividend yield de {formatar_metrica(acao['Metricas'].get('DividendYield', 0), 'percentual')}")
        motivos.append("Baixa volatilidade e boa proteção em cenários de incerteza")
        motivos.append(f"Payout sustentável de {formatar_metrica(acao['Metricas'].get('Payout', 0), 'percentual')}")
    
    elif categoria == "Empresas Sólidas":
        motivos.append(f"ROE expressivo de {formatar_metrica(acao['Metricas'].get('ROE', 0), 'percentual')}")
        motivos.append(f"Baixo endividamento com Dívida/Patrimônio de {formatar_metrica(acao['Metricas'].get('DividaPatrimonio', 0), 'decimal')}")
        motivos.append("Histórico consistente de resultados")
    
    elif categoria == "Ações Baratas":
        motivos.append(f"Múltiplo P/L atrativo de {formatar_metrica(acao['Metricas'].get('PL', 0), 'decimal')}")
        motivos.append(f"P/VP abaixo da média do setor em {formatar_metrica(acao['Metricas'].get('PVP', 0), 'decimal')}")
        motivos.append("Potencial de valorização significativo")
    
    elif categoria == "Melhores Ações":
        motivos.append(f"Pontuação excepcional de {formatar_metrica(acao['PontuacaoFinal'], 'decimal')}/10")
        motivos.append(f"Crescimento de lucros de {formatar_metrica(acao['Metricas'].get('CrescimentoLucros', 0), 'percentual')}")
        motivos.append("Excelente combinação de valor e crescimento")
    
    # Motivos baseados na situação atual na carteira
    if percentual_atual == 0:
        motivos.append("Oportunidade de diversificação com nova posição na carteira")
    elif percentual_atual < 3:
        motivos.append(f"Aumentar exposição atual de apenas {percentual_atual:.1f}% para melhor balanceamento")
    
    # Motivos baseados em métricas específicas
    if acao['Metricas'].get('MargemLiquida', 0) > 15:
        motivos.append(f"Alta margem líquida de {formatar_metrica(acao['Metricas'].get('MargemLiquida', 0), 'percentual')}")
    
    if acao['Metricas'].get('LiquidezCorrente', 0) > 1.5:
        motivos.append("Excelente liquidez financeira")
    
    # Selecionar 3 motivos aleatórios da lista
    if len(motivos) > 3:
        return random.sample(motivos, 3)
    else:
        return motivos

def gerar_relatorio_analista(analise_carteira, perfil, cenario, valor_aporte):
    """Gera um relatório no estilo de um analista profissional"""
    # Obter data atual
    data_atual = datetime.now().strftime("%d/%m/%Y")
    
    # Introdução
    relatorio = f"""
    # Relatório de Recomendação de Aporte - Pro Picks IA
    
    **Data:** {data_atual}
    **Perfil do Investidor:** {perfil}
    **Cenário Macroeconômico:** {cenario}
    **Valor do Aporte:** R$ {valor_aporte:.2f}
    
    ## Análise da Carteira Atual
    
    Após análise detalhada da sua carteira atual, identificamos algumas oportunidades de otimização 
    considerando o cenário macroeconômico atual e seu perfil de investidor. A distribuição atual 
    da sua carteira apresenta algumas divergências em relação à alocação ideal recomendada para 
    o momento de mercado.
    
    ### Distribuição Atual vs. Ideal
    """
    
    # Adicionar tabela de comparação
    relatorio += "\n    | Categoria | Atual | Ideal | Diferença |\n"
    relatorio += "    |-----------|-------|-------|----------|\n"
    
    for categoria, percentual_ideal in analise_carteira['alocacao_ideal'].items():
        percentual_atual = analise_carteira['carteira_atual'].get(categoria, 0)
        diferenca = analise_carteira['diferencas'].get(categoria, 0)
        
        # Formatar diferença com sinal
        if diferenca > 0:
            diferenca_str = f"+{diferenca:.1f}%"
        else:
            diferenca_str = f"{diferenca:.1f}%"
        
        relatorio += f"    | {categoria} | {percentual_atual:.1f}% | {percentual_ideal:.1f}% | {diferenca_str} |\n"
    
    # Recomendações de aporte
    relatorio += """
    
    ## Recomendações de Aporte
    
    Com base na análise fundamentalista e no cenário atual, recomendamos a seguinte distribuição 
    para o seu aporte:
    """
    
    # Adicionar tabela de recomendações
    if analise_carteira['recomendacoes']:
        relatorio += "\n    | Ação | Nome | Valor | % do Aporte |\n"
        relatorio += "    |------|------|-------|------------|\n"
        
        for ticker, info in analise_carteira['recomendacoes'].items():
            relatorio += f"    | {ticker} | {info['Nome']} | R$ {info['Valor']:.2f} | {info['Percentual']:.1f}% |\n"
        
        # Detalhamento das recomendações
        relatorio += """
        
        ## Justificativa das Recomendações
        
        A seguir, apresentamos a justificativa detalhada para cada recomendação de aporte:
        """
        
        for ticker, info in analise_carteira['recomendacoes'].items():
            relatorio += f"""
        
        ### {ticker} - {info['Nome']}
        
        **Categoria:** {info['Categoria']}
        **Pontuação:** {info['Pontuacao']:.1f}/10
        **Valor Recomendado:** R$ {info['Valor']:.2f} ({info['Percentual']:.1f}% do aporte)
        
        **Motivos:**
        """
            
            for motivo in info['Motivo']:
                relatorio += f"        - {motivo}\n"
    else:
        relatorio += """
        
        Com base na análise fundamentalista, técnica e do cenário macroeconômico atual, 
        recomendamos as seguintes ações para aporte, mesmo que não estejam alinhadas 
        com a alocação ideal da carteira:
        """
        
        # Adicionar tabela de recomendações alternativas
        relatorio += "\n    | Ação | Nome | Valor | % do Aporte |\n"
        relatorio += "    |------|------|-------|------------|\n"
        
        for ticker, info in analise_carteira['recomendacoes'].items():
            relatorio += f"    | {ticker} | {info['Nome']} | R$ {info['Valor']:.2f} | {info['Percentual']:.1f}% |\n"
        
        # Detalhamento das recomendações alternativas
        relatorio += """
        
        ## Justificativa das Recomendações
        
        A seguir, apresentamos a justificativa detalhada para cada recomendação de aporte:
        """
        
        for ticker, info in analise_carteira['recomendacoes'].items():
            relatorio += f"""
        
        ### {ticker} - {info['Nome']}
        
        **Categoria:** {info['Categoria']}
        **Pontuação:** {info['Pontuacao']:.1f}/10
        **Valor Recomendado:** R$ {info['Valor']:.2f} ({info['Percentual']:.1f}% do aporte)
        
        **Motivos:**
        """
            
            for motivo in info['Motivo']:
                relatorio += f"        - {motivo}\n"
    
    # Conclusão
    relatorio += """
    
    ## Conclusão
    
    As recomendações acima visam otimizar sua carteira de acordo com o cenário macroeconômico atual
    e seu perfil de investidor. Lembre-se que estas são recomendações baseadas em análise fundamentalista
    e devem ser consideradas como parte de uma estratégia de investimento de longo prazo.
    
    É importante ressaltar que investimentos em ações envolvem riscos e que resultados passados não
    garantem retornos futuros. Recomendamos sempre consultar um assessor de investimentos antes de
    tomar decisões financeiras.
    
    **Pro Picks IA - Análise Fundamentalista Inteligente**
    """
    
    return relatorio

# Interface do Streamlit
def main():
    # Título e descrição
    st.title("Pro Picks IA - Melhores Ações Brasileiras")
    st.markdown("""
    Esta aplicação simula o funcionamento do sistema Pro Picks IA para seleção das melhores ações brasileiras,
    utilizando critérios fundamentalistas, análise técnica e classificação do cenário macroeconômico.
    """)
    
    # Sidebar para configurações
    st.sidebar.title("Configurações")
    
    # Opção para atualizar dados
    if st.sidebar.button("Atualizar Dados"):
        with st.spinner("Atualizando dados..."):
            # Limpar cache de dados
            if os.path.exists(os.path.join(DATA_DIR, "lista_acoes.json")):
                os.remove(os.path.join(DATA_DIR, "lista_acoes.json"))
            
            # Obter lista atualizada
            acoes = obter_lista_acoes()
            st.sidebar.success(f"Dados atualizados! {len(acoes)} ações disponíveis.")
    
    # Classificação do cenário macroeconômico
    cenario = classificar_cenario_macroeconomico()
    
    # Perfil do investidor
    perfil = st.sidebar.selectbox(
        "Perfil do Investidor",
        ["Conservador", "Moderado", "Agressivo"],
        index=1,  # Default: Moderado
        help="Selecione seu perfil de investidor para ajustar as recomendações"
    )
    
    # Ajuste de pesos
    st.sidebar.subheader("Ajuste de Pesos dos Critérios")
    st.sidebar.markdown("Defina a importância de cada critério (1-10)")
    
    # Obter pesos padrão
    pesos_padrao = obter_pesos_padrao()
    
    # Permitir ajuste de pesos
    pesos = {}
    
    # Criar três colunas para organizar os sliders
    col1, col2, col3 = st.sidebar.columns(3)
    
    with col1:
        st.markdown("**Lucratividade**")
        pesos['ROE'] = st.slider("ROE", 1, 10, pesos_padrao['ROE'])
        pesos['ROIC'] = st.slider("ROIC", 1, 10, pesos_padrao['ROIC'])
    
    with col2:
        st.markdown("**Avaliação**")
        pesos['PL'] = st.slider("P/L", 1, 10, pesos_padrao['PL'])
        pesos['PVP'] = st.slider("P/VP", 1, 10, pesos_padrao['PVP'])
    
    with col3:
        st.markdown("**Saúde Financeira**")
        pesos['DividaPatrimonio'] = st.slider("Dívida/Patrimônio", 1, 10, pesos_padrao['DividaPatrimonio'])
        pesos['DividendYield'] = st.slider("Dividend Yield", 1, 10, pesos_padrao['DividendYield'])
    
    # Outros pesos mantidos como padrão
    for criterio, peso in pesos_padrao.items():
        if criterio not in pesos:
            pesos[criterio] = peso
    
    # Opção para selecionar modo de análise
    st.sidebar.subheader("Modo de Análise")
    modo_analise = st.sidebar.radio(
        "Escolha o modo de análise:",
        ["Automático (Top Ações)", "Carteira Personalizada"],
        help="No modo automático, analisamos as melhores ações do mercado. No modo personalizado, você pode inserir os tickers da sua carteira."
    )
    
    # Número de ações a analisar (no modo automático)
    num_acoes = 10
    if modo_analise == "Automático (Top Ações)":
        num_acoes = st.sidebar.slider(
            "Número de ações a analisar",
            min_value=5,
            max_value=50,
            value=10,
            step=5,
            help="Selecione quantas ações deseja analisar. Um número maior pode levar mais tempo para processar."
        )
    
    # Campo para inserir tickers da carteira (no modo personalizado)
    tickers_personalizados = []
    carteira_atual = {}
    
    if modo_analise == "Carteira Personalizada":
        st.sidebar.subheader("Sua Carteira Atual")
        
        # Opção para inserir tickers e percentuais
        st.sidebar.markdown("""
        Insira os tickers da sua carteira e os percentuais atuais (um por linha).
        Exemplo:
        ```
        PETR4 15
        VALE3 20
        ITUB4 10
        ```
        """)
        
        tickers_input = st.sidebar.text_area(
            "Tickers e percentuais da carteira",
            help="Formato: TICKER PERCENTUAL (um por linha)"
        )
        
        if tickers_input:
            # Processar os tickers e percentuais inseridos
            linhas = tickers_input.strip().split('\n')
            for linha in linhas:
                # Dividir a linha em ticker e percentual
                partes = linha.strip().split()
                if len(partes) >= 2:
                    ticker_limpo = partes[0].strip().replace(',', '')
                    try:
                        percentual = float(partes[1].strip().replace(',', '.'))
                        ticker_validado = validar_ticker(ticker_limpo)
                        if ticker_validado:
                            tickers_personalizados.append(ticker_validado)
                            carteira_atual[ticker_validado] = percentual
                    except ValueError:
                        st.sidebar.warning(f"Percentual inválido para {ticker_limpo}. Use formato numérico.")
                elif len(partes) == 1:
                    ticker_limpo = partes[0].strip().replace(',', '')
                    ticker_validado = validar_ticker(ticker_limpo)
                    if ticker_validado:
                        tickers_personalizados.append(ticker_validado)
                        # Atribuir percentual igual para todas as ações sem percentual especificado
                        carteira_atual[ticker_validado] = 0
        
        # Se houver ações sem percentual, distribuir igualmente
        if carteira_atual and any(p == 0 for p in carteira_atual.values()):
            acoes_sem_percentual = [t for t, p in carteira_atual.items() if p == 0]
            percentual_restante = 100 - sum(p for p in carteira_atual.values() if p > 0)
            if percentual_restante > 0 and acoes_sem_percentual:
                percentual_por_acao = percentual_restante / len(acoes_sem_percentual)
                for ticker in acoes_sem_percentual:
                    carteira_atual[ticker] = percentual_por_acao
        
        # Normalizar percentuais para somar 100%
        soma_percentuais = sum(carteira_atual.values())
        if soma_percentuais > 0:
            for ticker in carteira_atual:
                carteira_atual[ticker] = (carteira_atual[ticker] / soma_percentuais) * 100
        
        # Mostrar resumo da carteira
        if carteira_atual:
            st.sidebar.subheader("Resumo da Carteira")
            for ticker, percentual in carteira_atual.items():
                st.sidebar.text(f"{ticker}: {percentual:.1f}%")
        
        # Campo para valor do aporte
        st.sidebar.subheader("Valor do Aporte")
        valor_aporte = st.sidebar.number_input(
            "Valor a ser aportado (R$)",
            min_value=100.0,
            max_value=1000000.0,
            value=1000.0,
            step=100.0,
            help="Informe o valor que deseja aportar para receber recomendações personalizadas"
        )
    
    # Botão para iniciar análise
    if st.sidebar.button("Analisar Ações"):
        # Obter lista de ações
        if modo_analise == "Automático (Top Ações)":
            acoes = obter_lista_acoes()
            # Limitar ao número selecionado
            acoes = acoes[:num_acoes]
        else:
            # Usar tickers personalizados
            acoes = tickers_personalizados
            if not acoes:
                st.error("Por favor, insira pelo menos um ticker válido para análise.")
                return
        
        # Mostrar progresso
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Resultados
        resultados = []
        
        # Processar cada ação
        for i, ticker in enumerate(acoes):
            status_text.text(f"Analisando {ticker}... ({i+1}/{len(acoes)})")
            progress_bar.progress((i+1)/len(acoes))
            
            # Carregar dados
            dados = carregar_dados_acao(ticker)
            
            if dados:
                # Calcular métricas
                metricas = calcular_metricas_fundamentalistas(dados)
                
                # Calcular pontuação
                pontuacao, pontuacao_final = calcular_pontuacao(metricas, pesos)
                
                # Classificar ação
                categorias = classificar_acao(pontuacao_final, metricas)
                
                # Adicionar aos resultados
                resultados.append({
                    'Ticker': ticker,
                    'Nome': metricas.get('Nome', 'N/A'),
                    'Setor': metricas.get('Setor', 'N/A'),
                    'Metricas': metricas,
                    'Pontuacao': pontuacao,
                    'PontuacaoFinal': pontuacao_final,
                    'Categorias': categorias
                })
        
        # Limpar barra de progresso e status
        progress_bar.empty()
        status_text.empty()
        
        # Ordenar resultados por pontuação
        resultados = sorted(resultados, key=lambda x: x['PontuacaoFinal'], reverse=True)
        
        # Exibir resultados
        st.header("Resultados da Análise")
        
        # Criar abas para diferentes visualizações
        if modo_analise == "Carteira Personalizada" and carteira_atual:
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "Ranking Geral", 
                "Análise Detalhada", 
                "Carteiras Recomendadas", 
                "Alocação Sugerida",
                "Recomendação de Aporte"
            ])
        else:
            tab1, tab2, tab3, tab4 = st.tabs([
                "Ranking Geral", 
                "Análise Detalhada", 
                "Carteiras Recomendadas", 
                "Alocação Sugerida"
            ])
        
        with tab1:
            st.subheader("Ranking das Ações Analisadas")
            
            # Criar dataframe para exibição
            df_ranking = pd.DataFrame([
                {
                    'Ticker': r['Ticker'],
                    'Nome': r['Nome'],
                    'Setor': r['Setor'],
                    'Pontuação': f"{r['PontuacaoFinal']:.2f}",
                    'ROE': formatar_metrica(r['Metricas'].get('ROE'), "percentual"),
                    'Div/Pat': formatar_metrica(r['Metricas'].get('DividaPatrimonio'), "decimal"),
                    'P/L': formatar_metrica(r['Metricas'].get('PL'), "decimal"),
                    'P/VP': formatar_metrica(r['Metricas'].get('PVP'), "decimal"),
                    'DY': formatar_metrica(r['Metricas'].get('DividendYield'), "percentual"),
                    'Categorias': ", ".join(r['Categorias'])
                }
                for r in resultados
            ])
            
            # Exibir tabela
            st.dataframe(df_ranking, use_container_width=True)
            
            # Gráfico de pontuações
            st.subheader("Comparativo de Pontuações")
            
            # Preparar dados para gráfico
            df_pontuacoes = pd.DataFrame([
                {'Ticker': r['Ticker'], 'Pontuação': r['PontuacaoFinal']}
                for r in resultados
            ])
            
            # Criar gráfico
            fig = px.bar(
                df_pontuacoes,
                x='Ticker',
                y='Pontuação',
                title="Pontuação das Ações Analisadas",
                color='Pontuação',
                color_continuous_scale='RdYlGn',
                range_y=[0, 10]
            )
            
            fig.update_layout(
                xaxis_title="Ticker",
                yaxis_title="Pontuação (0-10)",
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            st.subheader("Análise Detalhada por Ação")
            
            # Seletor de ação
            ticker_selecionado = st.selectbox(
                "Selecione uma ação para análise detalhada",
                [r['Ticker'] for r in resultados],
                format_func=lambda x: f"{x} - {next((r['Nome'] for r in resultados if r['Ticker'] == x), '')}"
            )
            
            # Encontrar dados da ação selecionada
            acao_selecionada = next((r for r in resultados if r['Ticker'] == ticker_selecionado), None)
            
            if acao_selecionada:
                # Exibir informações básicas
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Pontuação Final", f"{acao_selecionada['PontuacaoFinal']:.2f}/10")
                
                with col2:
                    st.metric("Categorias", ", ".join(acao_selecionada['Categorias']))
                
                with col3:
                    st.metric("Setor", acao_selecionada['Setor'])
                
                # Exibir métricas detalhadas
                st.subheader("Métricas Fundamentalistas")
                
                # Organizar métricas em colunas
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**Lucratividade**")
                    st.metric("ROE", formatar_metrica(acao_selecionada['Metricas'].get('ROE'), "percentual"))
                    st.metric("ROIC", formatar_metrica(acao_selecionada['Metricas'].get('ROIC'), "percentual"))
                    st.metric("Margem Líquida", formatar_metrica(acao_selecionada['Metricas'].get('MargemLiquida'), "percentual"))
                    st.metric("Crescimento de Lucros", formatar_metrica(acao_selecionada['Metricas'].get('CrescimentoLucros'), "percentual"))
                
                with col2:
                    st.markdown("**Avaliação**")
                    st.metric("P/L", formatar_metrica(acao_selecionada['Metricas'].get('PL'), "decimal"))
                    st.metric("P/VP", formatar_metrica(acao_selecionada['Metricas'].get('PVP'), "decimal"))
                    st.metric("EV/EBITDA", formatar_metrica(acao_selecionada['Metricas'].get('EV_EBITDA'), "decimal"))
                    st.metric("Dividend Yield", formatar_metrica(acao_selecionada['Metricas'].get('DividendYield'), "percentual"))
                
                with col3:
                    st.markdown("**Saúde Financeira**")
                    st.metric("Dívida/Patrimônio", formatar_metrica(acao_selecionada['Metricas'].get('DividaPatrimonio'), "decimal"))
                    st.metric("Liquidez Corrente", formatar_metrica(acao_selecionada['Metricas'].get('LiquidezCorrente'), "decimal"))
                    st.metric("Payout", formatar_metrica(acao_selecionada['Metricas'].get('Payout'), "percentual"))
                    st.metric("Market Cap", formatar_metrica(acao_selecionada['Metricas'].get('MarketCap'), "inteiro"))
                
                # Gráficos de pontuação
                st.subheader("Análise de Pontuação por Critério")
                
                # Gráfico de barras
                fig_barras = gerar_grafico_pontuacao(
                    acao_selecionada['Pontuacao'],
                    f"Pontuação por Critério - {acao_selecionada['Ticker']}"
                )
                
                # Gráfico radar
                fig_radar = gerar_grafico_radar(
                    acao_selecionada['Pontuacao'],
                    f"Perfil de Pontuação - {acao_selecionada['Ticker']}"
                )
                
                # Exibir gráficos lado a lado
                col1, col2 = st.columns(2)
                
                with col1:
                    st.plotly_chart(fig_barras, use_container_width=True)
                
                with col2:
                    st.plotly_chart(fig_radar, use_container_width=True)
        
        with tab3:
            st.subheader("Carteiras Recomendadas por Categoria")
            
            # Criar carteiras recomendadas para cada categoria
            categorias_disponiveis = [
                "Melhores Ações Brasileiras",
                "Empresas Sólidas",
                "Ações Defensivas",
                "Ações Baratas"
            ]
            
            # Verificar quais categorias têm ações suficientes
            categorias_validas = []
            for categoria in categorias_disponiveis:
                acoes_categoria = [r for r in resultados if categoria in r['Categorias']]
                if len(acoes_categoria) > 0:
                    categorias_validas.append(categoria)
            
            # Seletor de categoria
            categoria_selecionada = st.selectbox(
                "Selecione uma categoria para ver a carteira recomendada",
                categorias_validas
            )
            
            # Criar carteira recomendada
            carteira = criar_carteira_recomendada(resultados, categoria_selecionada, max_acoes=5)
            
            if carteira:
                # Exibir carteira
                st.markdown(f"**Carteira Recomendada - {categoria_selecionada}**")
                
                # Criar dataframe para exibição
                df_carteira = pd.DataFrame([
                    {
                        'Ticker': r['Ticker'],
                        'Nome': r['Nome'],
                        'Setor': r['Setor'],
                        'Pontuação': f"{r['PontuacaoFinal']:.2f}",
                        'ROE': formatar_metrica(r['Metricas'].get('ROE'), "percentual"),
                        'Div/Pat': formatar_metrica(r['Metricas'].get('DividaPatrimonio'), "decimal"),
                        'P/L': formatar_metrica(r['Metricas'].get('PL'), "decimal"),
                        'DY': formatar_metrica(r['Metricas'].get('DividendYield'), "percentual")
                    }
                    for r in carteira
                ])
                
                # Exibir tabela
                st.dataframe(df_carteira, use_container_width=True)
                
                # Gráfico de composição da carteira
                st.subheader("Composição da Carteira")
                
                # Preparar dados para gráfico
                df_composicao = pd.DataFrame([
                    {'Ticker': r['Ticker'], 'Pontuação': r['PontuacaoFinal'], 'Setor': r['Setor']}
                    for r in carteira
                ])
                
                # Criar gráfico
                fig = px.pie(
                    df_composicao,
                    names='Ticker',
                    values='Pontuação',
                    title=f"Composição da Carteira - {categoria_selecionada}",
                    hover_data=['Setor'],
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                
                fig.update_traces(textposition='inside', textinfo='percent+label')
                
                fig.update_layout(
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"Não há ações suficientes na categoria {categoria_selecionada} para criar uma carteira recomendada.")
        
        with tab4:
            st.subheader("Alocação Sugerida por Perfil e Cenário")
            
            # Obter alocação sugerida
            alocacao = sugerir_alocacao(perfil, cenario)
            
            # Exibir informações
            st.markdown(f"**Perfil do Investidor:** {perfil}")
            st.markdown(f"**Cenário Macroeconômico:** {cenario}")
            
            # Exibir alocação
            st.markdown("**Alocação Sugerida:**")
            
            # Criar colunas para exibir percentuais
            cols = st.columns(len(alocacao))
            
            for i, (categoria, percentual) in enumerate(alocacao.items()):
                cols[i].metric(categoria, percentual)
            
            # Gráfico de alocação
            fig = gerar_grafico_alocacao(
                alocacao,
                f"Alocação Sugerida - Perfil {perfil}, Cenário {cenario}"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Sugestão de carteira balanceada
            st.subheader("Sugestão de Carteira Balanceada")
            
            # Criar carteiras para cada categoria
            carteiras_por_categoria = {}
            for categoria in alocacao.keys():
                if categoria == "Melhores Ações":
                    categoria_busca = "Melhores Ações Brasileiras"
                else:
                    categoria_busca = categoria
                
                carteira = criar_carteira_recomendada(resultados, categoria_busca, max_acoes=3)
                carteiras_por_categoria[categoria] = carteira
            
            # Exibir carteiras
            for categoria, carteira in carteiras_por_categoria.items():
                st.markdown(f"**{categoria} ({alocacao[categoria]})**")
                
                if carteira:
                    # Criar dataframe para exibição
                    df_carteira = pd.DataFrame([
                        {
                            'Ticker': r['Ticker'],
                            'Nome': r['Nome'],
                            'Pontuação': f"{r['PontuacaoFinal']:.2f}"
                        }
                        for r in carteira
                    ])
                    
                    # Exibir tabela
                    st.dataframe(df_carteira, use_container_width=True)
                else:
                    st.warning(f"Não há ações suficientes na categoria {categoria} para sugerir.")
        
        # Aba de Recomendação de Aporte (apenas no modo Carteira Personalizada)
        if modo_analise == "Carteira Personalizada" and carteira_atual and 'tab5' in locals():
            with tab5:
                st.subheader("Recomendação de Aporte Personalizada")
                
                # Analisar carteira e gerar recomendações
                analise_carteira = analisar_carteira_para_aporte(
                    resultados,
                    carteira_atual, 
                    perfil, 
                    cenario, 
                    valor_aporte
                )
                
                # Exibir comparação entre carteira atual e ideal
                col1, col2 = st.columns(2)
                
                with col1:
                    # Gráfico da carteira atual
                    fig_atual = px.pie(
                        names=list(analise_carteira['carteira_atual'].keys()),
                        values=list(analise_carteira['carteira_atual'].values()),
                        title="Composição Atual da Carteira",
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    fig_atual.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_atual, use_container_width=True)
                
                with col2:
                    # Gráfico da alocação ideal
                    fig_ideal = px.pie(
                        names=list(analise_carteira['alocacao_ideal'].keys()),
                        values=list(analise_carteira['alocacao_ideal'].values()),
                        title="Alocação Ideal Recomendada",
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    fig_ideal.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_ideal, use_container_width=True)
                
                # Exibir recomendações de aporte
                st.subheader("Recomendações para o Aporte de R$ " + f"{valor_aporte:.2f}")
                
                if analise_carteira['recomendacoes']:
                    # Criar dataframe para exibição
                    df_recomendacoes = pd.DataFrame([
                        {
                            'Ticker': ticker,
                            'Nome': info['Nome'],
                            'Categoria': info['Categoria'],
                            'Valor Recomendado': f"R$ {info['Valor']:.2f}",
                            '% do Aporte': f"{info['Percentual']:.1f}%",
                            'Pontuação': f"{info['Pontuacao']:.1f}/10"
                        }
                        for ticker, info in analise_carteira['recomendacoes'].items()
                    ])
                    
                    # Exibir tabela
                    st.dataframe(df_recomendacoes, use_container_width=True)
                    
                    # Gráfico de distribuição do aporte
                    fig_aporte = px.pie(
                        names=[f"{ticker}" for ticker in analise_carteira['recomendacoes'].keys()],
                        values=[info['Valor'] for info in analise_carteira['recomendacoes'].values()],
                        title="Distribuição do Aporte",
                        color_discrete_sequence=px.colors.sequential.Viridis
                    )
                    fig_aporte.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_aporte, use_container_width=True)
                    
                    # Detalhamento das recomendações
                    st.subheader("Justificativa das Recomendações")
                    
                    for ticker, info in analise_carteira['recomendacoes'].items():
                        with st.expander(f"{ticker} - {info['Nome']}"):
                            st.markdown(f"**Categoria:** {info['Categoria']}")
                            st.markdown(f"**Pontuação:** {info['Pontuacao']:.1f}/10")
                            st.markdown(f"**Valor Recomendado:** R$ {info['Valor']:.2f} ({info['Percentual']:.1f}% do aporte)")
                            
                            st.markdown("**Motivos:**")
                            for motivo in info['Motivo']:
                                st.markdown(f"- {motivo}")
                else:
                    st.warning("Não foram identificadas oportunidades claras de aporte no momento.")
                
                # Relatório completo do analista
                st.subheader("Relatório do Analista")
                
                relatorio = gerar_relatorio_analista(
                    analise_carteira,
                    perfil,
                    cenario,
                    valor_aporte
                )
                
                st.markdown(relatorio)
                
                # Botão para download do relatório
                relatorio_bytes = relatorio.encode()
                st.download_button(
                    label="Baixar Relatório em Markdown",
                    data=relatorio_bytes,
                    file_name="relatorio_aporte.md",
                    mime="text/markdown"
                )
    
    # Exibir informações adicionais
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Pro Picks IA - Versão 2.0**")
    st.sidebar.markdown("Desenvolvido como simulação do sistema Pro Picks IA")

if __name__ == "__main__":
    main()

def gerar_motivo_recomendacao_alternativo(acao, categoria, percentual_atual, cenario):
    """Gera motivos alternativos para recomendação, garantindo critérios fundamentalistas, técnicos e macroeconômicos
    
    Args:
        acao (dict): Dados da ação
        categoria (str): Categoria da ação
        percentual_atual (float): Percentual atual na carteira
        cenario (str): Cenário macroeconômico atual
        
    Returns:
        list: Lista de motivos para a recomendação
    """
    motivos = []
    
    # 1. Critérios Fundamentalistas (sempre incluir pelo menos um)
    motivos_fundamentalistas = []
    
    if acao['Metricas'].get('ROE', 0) > 10:
        motivos_fundamentalistas.append(f"ROE atrativo de {formatar_metrica(acao['Metricas'].get('ROE', 0), 'percentual')} demonstra eficiência na geração de lucros")
    
    if acao['Metricas'].get('MargemLiquida', 0) > 10:
        motivos_fundamentalistas.append(f"Margem líquida sólida de {formatar_metrica(acao['Metricas'].get('MargemLiquida', 0), 'percentual')} indica boa eficiência operacional")
    
    if acao['Metricas'].get('DividaPatrimonio', 0) < 1.0:
        motivos_fundamentalistas.append(f"Baixo endividamento com Dívida/Patrimônio de {formatar_metrica(acao['Metricas'].get('DividaPatrimonio', 0), 'decimal')} reduz riscos financeiros")
    
    if acao['Metricas'].get('PL', 0) < 15 and acao['Metricas'].get('PL', 0) > 0:
        motivos_fundamentalistas.append(f"Múltiplo P/L atrativo de {formatar_metrica(acao['Metricas'].get('PL', 0), 'decimal')} sugere possível subavaliação")
    
    if acao['Metricas'].get('PVP', 0) < 2.0 and acao['Metricas'].get('PVP', 0) > 0:
        motivos_fundamentalistas.append(f"P/VP de {formatar_metrica(acao['Metricas'].get('PVP', 0), 'decimal')} indica potencial valorização em relação ao patrimônio")
    
    if acao['Metricas'].get('DividendYield', 0) > 4:
        motivos_fundamentalistas.append(f"Dividend Yield atrativo de {formatar_metrica(acao['Metricas'].get('DividendYield', 0), 'percentual')} oferece boa remuneração ao acionista")
    
    if acao['Metricas'].get('CrescimentoLucros', 0) > 10:
        motivos_fundamentalistas.append(f"Crescimento de lucros de {formatar_metrica(acao['Metricas'].get('CrescimentoLucros', 0), 'percentual')} demonstra expansão consistente")
    
    # Garantir pelo menos um motivo fundamentalista
    if not motivos_fundamentalistas:
        motivos_fundamentalistas.append(f"Pontuação fundamentalista de {formatar_metrica(acao['PontuacaoFinal'], 'decimal')}/10 baseada em múltiplos critérios de avaliação")
    
    # 2. Critérios de Análise Técnica (sempre incluir pelo menos um)
    motivos_tecnicos = []
    
    if acao['Metricas'].get('RSI', 0) < 30:
        motivos_tecnicos.append("RSI em região de sobrevenda, indicando possível reversão de tendência")
    elif acao['Metricas'].get('RSI', 0) > 30 and acao['Metricas'].get('RSI', 0) < 70:
        motivos_tecnicos.append("RSI em região neutra, sugerindo estabilidade no momento")
    
    if acao['Metricas'].get('SMA50_200', 0) > 0:
        motivos_tecnicos.append("Médias móveis em configuração de alta (Golden Cross), sinalizando tendência positiva")
    
    if acao['Metricas'].get('Volatilidade', 0) < 30:
        motivos_tecnicos.append(f"Baixa volatilidade de {formatar_metrica(acao['Metricas'].get('Volatilidade', 0), 'percentual')} indica menor risco de oscilações bruscas")
    
    if acao['Metricas'].get('Momentum', 0) > 0:
        motivos_tecnicos.append("Momentum positivo sugere continuidade da tendência de alta")
    
    # Garantir pelo menos um motivo técnico
    if not motivos_tecnicos:
        motivos_tecnicos.append("Análise técnica indica momento adequado para entrada, considerando preço atual e tendências recentes")
    
    # 3. Critérios Macroeconômicos (sempre incluir pelo menos um)
    motivos_macro = []
    
    if "Alta" in cenario:
        motivos_macro.append(f"Ação bem posicionada para cenário macroeconômico de {cenario}, com potencial de valorização")
    elif "Neutra" in cenario:
        motivos_macro.append(f"Perfil defensivo adequado ao cenário macroeconômico {cenario}, oferecendo equilíbrio entre risco e retorno")
    elif "Baixa" in cenario:
        motivos_macro.append(f"Características defensivas que ajudam a proteger o capital no atual cenário macroeconômico de {cenario}")
    
    if categoria == "Ações Defensivas":
        motivos_macro.append("Setor defensivo tende a performar bem mesmo em cenários de incerteza econômica")
    elif categoria == "Empresas Sólidas":
        motivos_macro.append("Empresa com solidez financeira para navegar diferentes ciclos econômicos")
    elif categoria == "Ações Baratas":
        motivos_macro.append("Valuation atrativo oferece margem de segurança em diferentes cenários econômicos")
    elif categoria == "Melhores Ações":
        motivos_macro.append("Combinação de qualidade e crescimento posiciona bem a empresa para o cenário atual")
    
    # Garantir pelo menos um motivo macroeconômico
    if not motivos_macro:
        motivos_macro.append(f"Características da empresa alinhadas ao cenário macroeconômico atual de {cenario}")
    
    # Selecionar um motivo de cada categoria para garantir os três pilares
    motivos.append(random.choice(motivos_fundamentalistas))
    motivos.append(random.choice(motivos_tecnicos))
    motivos.append(random.choice(motivos_macro))
    
    return motivos
