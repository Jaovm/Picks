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
                dados['income_statement'] = acao.income_stmt.to_dict()
            except:
                dados['income_statement'] = {}
                
            try:
                dados['balance_sheet'] = acao.balance_sheet.to_dict()
            except:
                dados['balance_sheet'] = {}
                
            try:
                dados['cash_flow'] = acao.cashflow.to_dict()
            except:
                dados['cash_flow'] = {}
            
            # 3. Dados históricos (2 anos)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=2*365)
            try:
                hist = acao.history(start=start_date, end=end_date, interval="1d")
                dados['historical'] = hist.to_dict('records')
            except:
                dados['historical'] = []
            
            # 4. Dividendos
            try:
                dividends = acao.dividends.to_dict()
                dados['dividends'] = dividends
            except:
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
        if 'netIncome' in info and 'totalStockholderEquity' in info and info['totalStockholderEquity'] != 0:
            metricas['ROE'] = (info['netIncome'] / info['totalStockholderEquity']) * 100
        else:
            metricas['ROE'] = None
        
        # ROIC (Retorno sobre Capital Investido)
        if 'ebit' in info and 'totalAssets' in info and 'totalCurrentLiabilities' in info:
            capital_investido = info['totalAssets'] - info['totalCurrentLiabilities']
            if capital_investido != 0:
                metricas['ROIC'] = (info['ebit'] * (1 - 0.34)) / capital_investido * 100  # Considerando alíquota de 34%
            else:
                metricas['ROIC'] = None
        else:
            metricas['ROIC'] = None
        
        # Margem Líquida
        if 'netIncome' in info and 'totalRevenue' in info and info['totalRevenue'] != 0:
            metricas['MargemLiquida'] = (info['netIncome'] / info['totalRevenue']) * 100
        else:
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
        if 'totalDebt' in info and 'totalStockholderEquity' in info and info['totalStockholderEquity'] != 0:
            metricas['DividaPatrimonio'] = info['totalDebt'] / info['totalStockholderEquity']
        else:
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
    mostrar_ajuste_pesos = st.sidebar.checkbox("Personalizar Pesos", value=False)
    
    # Obter pesos padrão
    pesos = obter_pesos_padrao()
    
    # Permitir ajuste de pesos
    if mostrar_ajuste_pesos:
        st.sidebar.markdown("**Lucratividade (25%)**")
        pesos['ROE'] = st.sidebar.slider("ROE (Retorno sobre Patrimônio)", 0, 10, 6)
        pesos['ROIC'] = st.sidebar.slider("ROIC (Retorno sobre Capital Investido)", 0, 10, 6)
        pesos['MargemLiquida'] = st.sidebar.slider("Margem Líquida", 0, 10, 7)
        pesos['CrescimentoLucros'] = st.sidebar.slider("Crescimento de Lucros", 0, 10, 6)
        
        st.sidebar.markdown("**Avaliação (20%)**")
        pesos['PL'] = st.sidebar.slider("P/L (Preço/Lucro)", 0, 10, 7)
        pesos['PVP'] = st.sidebar.slider("P/VP (Preço/Valor Patrimonial)", 0, 10, 5)
        pesos['EV_EBITDA'] = st.sidebar.slider("EV/EBITDA", 0, 10, 5)
        pesos['DividendYield'] = st.sidebar.slider("Dividend Yield", 0, 10, 3)
        
        st.sidebar.markdown("**Saúde Financeira (20%)**")
        pesos['DividaPatrimonio'] = st.sidebar.slider("Dívida/Patrimônio", 0, 10, 7)
        pesos['LiquidezCorrente'] = st.sidebar.slider("Liquidez Corrente", 0, 10, 5)
        pesos['Payout'] = st.sidebar.slider("Payout", 0, 10, 3)
    
    # Número de ações a analisar
    num_acoes = st.sidebar.slider(
        "Número de Ações a Analisar",
        min_value=10,
        max_value=100,
        value=30,
        step=10,
        help="Selecione quantas ações serão analisadas (mais ações = mais tempo de processamento)"
    )
    
    # Botão para iniciar análise
    iniciar_analise = st.sidebar.button("Iniciar Análise")
    
    # Exibir informações sobre o cenário macroeconômico
    st.subheader(f"Cenário Macroeconômico: {cenario}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if cenario == "Expansão":
            st.info("Crescimento econômico forte, inflação controlada. Favorece empresas cíclicas e de crescimento.")
        elif cenario == "Desaceleração":
            st.warning("Crescimento econômico em queda, inflação ainda presente. Favorece empresas de qualidade e setores defensivos.")
        elif cenario == "Recessão":
            st.error("Crescimento negativo, pressões deflacionárias. Favorece empresas com balanços sólidos e baixo endividamento.")
        elif cenario == "Recuperação":
            st.success("Retomada do crescimento após período de contração. Favorece empresas cíclicas de qualidade e setores mais sensíveis.")
    
    with col2:
        st.subheader(f"Perfil do Investidor: {perfil}")
        if perfil == "Conservador":
            st.info("Prioriza preservação de capital e renda. Preferência por empresas estáveis e pagadoras de dividendos.")
        elif perfil == "Moderado":
            st.info("Busca equilíbrio entre crescimento e segurança. Diversificação entre diferentes tipos de empresas.")
        elif perfil == "Agressivo":
            st.info("Foco em crescimento e valorização. Maior tolerância a risco e volatilidade.")
    
    # Alocação sugerida
    alocacao = sugerir_alocacao(perfil, cenario)
    
    # Gráfico de alocação sugerida
    fig_alocacao = gerar_grafico_alocacao(
        alocacao, 
        f"Alocação Sugerida para Perfil {perfil} em Cenário de {cenario}"
    )
    st.plotly_chart(fig_alocacao, use_container_width=True)
    
    # Iniciar análise quando solicitado
    if iniciar_analise:
        # Obter lista de ações
        acoes = obter_lista_acoes()
        
        # Limitar ao número selecionado
        acoes = acoes[:num_acoes]
        
        # Barra de progresso
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Resultados
        resultados = []
        
        # Analisar cada ação
        for i, ticker in enumerate(acoes):
            # Atualizar progresso
            progress = (i + 1) / len(acoes)
            progress_bar.progress(progress)
            status_text.text(f"Analisando {ticker} ({i+1}/{len(acoes)})")
            
            # Carregar dados
            dados = carregar_dados_acao(ticker)
            
            if dados:
                # Calcular métricas
                metricas = calcular_metricas_fundamentalistas(dados)
                
                if metricas:
                    # Calcular pontuação
                    pontuacoes, pontuacao_final = calcular_pontuacao(metricas, pesos)
                    
                    # Classificar ação
                    categorias = classificar_acao(pontuacao_final, metricas)
                    
                    # Adicionar aos resultados
                    resultados.append({
                        'Ticker': ticker,
                        'Nome': metricas.get('Nome', 'N/A'),
                        'Setor': metricas.get('Setor', 'N/A'),
                        'Metricas': metricas,
                        'Pontuacoes': pontuacoes,
                        'PontuacaoFinal': pontuacao_final,
                        'Categorias': categorias
                    })
        
        # Limpar barra de progresso e status
        progress_bar.empty()
        status_text.empty()
        
        # Exibir resultados
        if resultados:
            st.subheader("Resultados da Análise")
            
            # Ordenar resultados por pontuação
            resultados_ordenados = sorted(resultados, key=lambda x: x['PontuacaoFinal'], reverse=True)
            
            # Criar abas para diferentes visualizações
            tab1, tab2, tab3, tab4 = st.tabs(["Ranking Geral", "Carteiras Recomendadas", "Análise por Setor", "Detalhes por Ação"])
            
            with tab1:
                # Criar dataframe para exibição
                df_ranking = pd.DataFrame([
                    {
                        'Ticker': r['Ticker'],
                        'Nome': r['Nome'],
                        'Setor': r['Setor'],
                        'Pontuação': round(r['PontuacaoFinal'], 2),
                        'Categorias': ', '.join(r['Categorias']),
                        'P/L': formatar_metrica(r['Metricas'].get('PL'), 'decimal'),
                        'P/VP': formatar_metrica(r['Metricas'].get('PVP'), 'decimal'),
                        'ROE': formatar_metrica(r['Metricas'].get('ROE'), 'percentual'),
                        'Div. Yield': formatar_metrica(r['Metricas'].get('DividendYield'), 'percentual'),
                        'Dív/Pat': formatar_metrica(r['Metricas'].get('DividaPatrimonio'), 'decimal')
                    }
                    for r in resultados_ordenados
                ])
                
                # Exibir tabela
                st.dataframe(df_ranking, use_container_width=True)
                
                # Gráfico de pontuações
                pontuacoes_finais = {r['Ticker']: r['PontuacaoFinal'] for r in resultados_ordenados[:15]}
                fig = px.bar(
                    x=list(pontuacoes_finais.keys()),
                    y=list(pontuacoes_finais.values()),
                    title="Top 15 Ações por Pontuação",
                    labels={'x': 'Ticker', 'y': 'Pontuação (0-10)'},
                    color=list(pontuacoes_finais.values()),
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with tab2:
                # Criar carteiras recomendadas
                st.subheader("Carteiras Recomendadas")
                
                # Melhores Ações Brasileiras
                st.markdown("### 🏆 Melhores Ações Brasileiras")
                carteira_melhores = criar_carteira_recomendada(resultados_ordenados, "Melhores Ações Brasileiras")
                
                if carteira_melhores:
                    df_melhores = pd.DataFrame([
                        {
                            'Ticker': r['Ticker'],
                            'Nome': r['Nome'],
                            'Setor': r['Setor'],
                            'Pontuação': round(r['PontuacaoFinal'], 2),
                            'P/L': formatar_metrica(r['Metricas'].get('PL'), 'decimal'),
                            'ROE': formatar_metrica(r['Metricas'].get('ROE'), 'percentual'),
                            'Div. Yield': formatar_metrica(r['Metricas'].get('DividendYield'), 'percentual')
                        }
                        for r in carteira_melhores
                    ])
                    st.dataframe(df_melhores, use_container_width=True)
                else:
                    st.info("Nenhuma ação classificada nesta categoria.")
                
                # Empresas Sólidas
                st.markdown("### 🏢 Empresas Sólidas do Brasil")
                carteira_solidas = criar_carteira_recomendada(resultados_ordenados, "Empresas Sólidas")
                
                if carteira_solidas:
                    df_solidas = pd.DataFrame([
                        {
                            'Ticker': r['Ticker'],
                            'Nome': r['Nome'],
                            'Setor': r['Setor'],
                            'Pontuação': round(r['PontuacaoFinal'], 2),
                            'ROE': formatar_metrica(r['Metricas'].get('ROE'), 'percentual'),
                            'ROIC': formatar_metrica(r['Metricas'].get('ROIC'), 'percentual'),
                            'Dív/Pat': formatar_metrica(r['Metricas'].get('DividaPatrimonio'), 'decimal')
                        }
                        for r in carteira_solidas
                    ])
                    st.dataframe(df_solidas, use_container_width=True)
                else:
                    st.info("Nenhuma ação classificada nesta categoria.")
                
                # Ações Defensivas
                st.markdown("### 🛡️ Ações Defensivas do Brasil")
                carteira_defensivas = criar_carteira_recomendada(resultados_ordenados, "Ações Defensivas")
                
                if carteira_defensivas:
                    df_defensivas = pd.DataFrame([
                        {
                            'Ticker': r['Ticker'],
                            'Nome': r['Nome'],
                            'Setor': r['Setor'],
                            'Pontuação': round(r['PontuacaoFinal'], 2),
                            'Div. Yield': formatar_metrica(r['Metricas'].get('DividendYield'), 'percentual'),
                            'Payout': formatar_metrica(r['Metricas'].get('Payout'), 'percentual'),
                            'Liq. Corrente': formatar_metrica(r['Metricas'].get('LiquidezCorrente'), 'decimal')
                        }
                        for r in carteira_defensivas
                    ])
                    st.dataframe(df_defensivas, use_container_width=True)
                else:
                    st.info("Nenhuma ação classificada nesta categoria.")
                
                # Ações Baratas
                st.markdown("### 💰 Ações Baratas do Brasil")
                carteira_baratas = criar_carteira_recomendada(resultados_ordenados, "Ações Baratas")
                
                if carteira_baratas:
                    df_baratas = pd.DataFrame([
                        {
                            'Ticker': r['Ticker'],
                            'Nome': r['Nome'],
                            'Setor': r['Setor'],
                            'Pontuação': round(r['PontuacaoFinal'], 2),
                            'P/L': formatar_metrica(r['Metricas'].get('PL'), 'decimal'),
                            'P/VP': formatar_metrica(r['Metricas'].get('PVP'), 'decimal'),
                            'EV/EBITDA': formatar_metrica(r['Metricas'].get('EV_EBITDA'), 'decimal')
                        }
                        for r in carteira_baratas
                    ])
                    st.dataframe(df_baratas, use_container_width=True)
                else:
                    st.info("Nenhuma ação classificada nesta categoria.")
                
                # Carteira Personalizada para o Perfil
                st.markdown(f"### 🎯 Carteira Personalizada para Perfil {perfil}")
                
                # Criar carteira personalizada com base no perfil e cenário
                carteira_personalizada = []
                
                # Determinar número de ações por categoria com base na alocação sugerida
                num_melhores = max(1, int(float(alocacao.get("Melhores Ações", "0%").replace("%", "")) / 100 * 10))
                num_solidas = max(1, int(float(alocacao.get("Empresas Sólidas", "0%").replace("%", "")) / 100 * 10))
                num_defensivas = max(1, int(float(alocacao.get("Ações Defensivas", "0%").replace("%", "")) / 100 * 10))
                num_baratas = max(1, int(float(alocacao.get("Ações Baratas", "0%").replace("%", "")) / 100 * 10))
                
                # Adicionar ações de cada categoria
                for r in carteira_melhores[:num_melhores]:
                    if r not in carteira_personalizada:
                        carteira_personalizada.append(r)
                
                for r in carteira_solidas[:num_solidas]:
                    if r not in carteira_personalizada:
                        carteira_personalizada.append(r)
                
                for r in carteira_defensivas[:num_defensivas]:
                    if r not in carteira_personalizada:
                        carteira_personalizada.append(r)
                
                for r in carteira_baratas[:num_baratas]:
                    if r not in carteira_personalizada:
                        carteira_personalizada.append(r)
                
                # Exibir carteira personalizada
                if carteira_personalizada:
                    df_personalizada = pd.DataFrame([
                        {
                            'Ticker': r['Ticker'],
                            'Nome': r['Nome'],
                            'Setor': r['Setor'],
                            'Categorias': ', '.join(r['Categorias']),
                            'Pontuação': round(r['PontuacaoFinal'], 2),
                            'P/L': formatar_metrica(r['Metricas'].get('PL'), 'decimal'),
                            'Div. Yield': formatar_metrica(r['Metricas'].get('DividendYield'), 'percentual'),
                            'ROE': formatar_metrica(r['Metricas'].get('ROE'), 'percentual')
                        }
                        for r in carteira_personalizada
                    ])
                    st.dataframe(df_personalizada, use_container_width=True)
                    
                    # Gráfico de distribuição setorial
                    setores = df_personalizada['Setor'].value_counts()
                    fig_setores = px.pie(
                        names=setores.index,
                        values=setores.values,
                        title="Distribuição Setorial da Carteira Personalizada"
                    )
                    st.plotly_chart(fig_setores, use_container_width=True)
                else:
                    st.info("Não foi possível criar uma carteira personalizada com os dados disponíveis.")
            
            with tab3:
                # Análise por setor
                st.subheader("Análise por Setor")
                
                # Agrupar resultados por setor
                setores = {}
                for r in resultados:
                    setor = r['Setor']
                    if setor not in setores:
                        setores[setor] = []
                    setores[setor].append(r)
                
                # Pontuação média por setor
                pontuacoes_setor = {
                    setor: sum(r['PontuacaoFinal'] for r in acoes) / len(acoes)
                    for setor, acoes in setores.items() if setor != 'N/A'
                }
                
                # Ordenar setores por pontuação
                setores_ordenados = sorted(pontuacoes_setor.items(), key=lambda x: x[1], reverse=True)
                
                # Gráfico de pontuações por setor
                fig_setores = px.bar(
                    x=[s[0] for s in setores_ordenados],
                    y=[s[1] for s in setores_ordenados],
                    title="Pontuação Média por Setor",
                    labels={'x': 'Setor', 'y': 'Pontuação Média (0-10)'},
                    color=[s[1] for s in setores_ordenados],
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig_setores, use_container_width=True)
                
                # Melhor ação por setor
                st.subheader("Melhor Ação por Setor")
                
                melhores_por_setor = []
                for setor, acoes in setores.items():
                    if setor != 'N/A' and acoes:
                        # Ordenar ações do setor por pontuação
                        acoes_ordenadas = sorted(acoes, key=lambda x: x['PontuacaoFinal'], reverse=True)
                        # Adicionar a melhor ação do setor
                        melhores_por_setor.append(acoes_ordenadas[0])
                
                # Ordenar por pontuação
                melhores_por_setor = sorted(melhores_por_setor, key=lambda x: x['PontuacaoFinal'], reverse=True)
                
                # Criar dataframe
                df_melhores_setor = pd.DataFrame([
                    {
                        'Ticker': r['Ticker'],
                        'Nome': r['Nome'],
                        'Setor': r['Setor'],
                        'Pontuação': round(r['PontuacaoFinal'], 2),
                        'Categorias': ', '.join(r['Categorias']),
                        'P/L': formatar_metrica(r['Metricas'].get('PL'), 'decimal'),
                        'ROE': formatar_metrica(r['Metricas'].get('ROE'), 'percentual')
                    }
                    for r in melhores_por_setor
                ])
                
                st.dataframe(df_melhores_setor, use_container_width=True)
                
                # Distribuição de categorias por setor
                st.subheader("Distribuição de Categorias por Setor")
                
                # Contar categorias por setor
                categorias_por_setor = {}
                for r in resultados:
                    setor = r['Setor']
                    if setor != 'N/A':
                        if setor not in categorias_por_setor:
                            categorias_por_setor[setor] = {
                                'Melhores Ações Brasileiras': 0,
                                'Empresas Sólidas': 0,
                                'Ações Defensivas': 0,
                                'Ações Baratas': 0,
                                'Outras': 0
                            }
                        
                        # Incrementar contadores de categorias
                        categorias_encontradas = False
                        for categoria in ['Melhores Ações Brasileiras', 'Empresas Sólidas', 'Ações Defensivas', 'Ações Baratas']:
                            if categoria in r['Categorias']:
                                categorias_por_setor[setor][categoria] += 1
                                categorias_encontradas = True
                        
                        if not categorias_encontradas:
                            categorias_por_setor[setor]['Outras'] += 1
                
                # Criar dataframe para heatmap
                setores_list = []
                categorias_list = []
                valores_list = []
                
                for setor, categorias in categorias_por_setor.items():
                    for categoria, valor in categorias.items():
                        setores_list.append(setor)
                        categorias_list.append(categoria)
                        valores_list.append(valor)
                
                df_heatmap = pd.DataFrame({
                    'Setor': setores_list,
                    'Categoria': categorias_list,
                    'Valor': valores_list
                })
                
                # Criar heatmap
                fig_heatmap = px.density_heatmap(
                    df_heatmap,
                    x='Setor',
                    y='Categoria',
                    z='Valor',
                    title="Distribuição de Categorias por Setor",
                    color_continuous_scale='YlGnBu'
                )
                
                fig_heatmap.update_layout(
                    xaxis_title="Setor",
                    yaxis_title="Categoria",
                    height=500
                )
                
                st.plotly_chart(fig_heatmap, use_container_width=True)
            
            with tab4:
                # Detalhes por ação
                st.subheader("Detalhes por Ação")
                
                # Seleção de ação
                opcoes_acoes = [(f"{r['Ticker']} - {r['Nome']}") for r in resultados_ordenados]
                acao_selecionada = st.selectbox("Selecione uma ação para ver detalhes", opcoes_acoes)
                
                if acao_selecionada:
                    # Extrair ticker da seleção
                    ticker_selecionado = acao_selecionada.split(" - ")[0]
                    
                    # Encontrar ação nos resultados
                    acao = next((r for r in resultados if r['Ticker'] == ticker_selecionado), None)
                    
                    if acao:
                        # Exibir detalhes da ação
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown(f"### {acao['Nome']} ({acao['Ticker']})")
                            st.markdown(f"**Setor:** {acao['Setor']}")
                            st.markdown(f"**Categorias:** {', '.join(acao['Categorias'])}")
                            st.markdown(f"**Pontuação Final:** {acao['PontuacaoFinal']:.2f}/10")
                            
                            # Gráfico de radar das pontuações
                            fig_radar = gerar_grafico_radar(
                                acao['Pontuacoes'],
                                f"Pontuações por Critério - {acao['Ticker']}"
                            )
                            st.plotly_chart(fig_radar, use_container_width=True)
                        
                        with col2:
                            # Métricas principais
                            st.markdown("### Métricas Principais")
                            
                            metricas = acao['Metricas']
                            
                            # Lucratividade
                            st.markdown("#### Lucratividade")
                            col_a, col_b = st.columns(2)
                            col_a.metric("ROE", formatar_metrica(metricas.get('ROE'), 'percentual'))
                            col_b.metric("ROIC", formatar_metrica(metricas.get('ROIC'), 'percentual'))
                            col_a.metric("Margem Líquida", formatar_metrica(metricas.get('MargemLiquida'), 'percentual'))
                            col_b.metric("Cresc. Lucros", formatar_metrica(metricas.get('CrescimentoLucros'), 'percentual'))
                            
                            # Avaliação
                            st.markdown("#### Avaliação")
                            col_a, col_b = st.columns(2)
                            col_a.metric("P/L", formatar_metrica(metricas.get('PL'), 'decimal'))
                            col_b.metric("P/VP", formatar_metrica(metricas.get('PVP'), 'decimal'))
                            col_a.metric("EV/EBITDA", formatar_metrica(metricas.get('EV_EBITDA'), 'decimal'))
                            col_b.metric("Div. Yield", formatar_metrica(metricas.get('DividendYield'), 'percentual'))
                            
                            # Saúde Financeira
                            st.markdown("#### Saúde Financeira")
                            col_a, col_b = st.columns(2)
                            col_a.metric("Dívida/Patrimônio", formatar_metrica(metricas.get('DividaPatrimonio'), 'decimal'))
                            col_b.metric("Liquidez Corrente", formatar_metrica(metricas.get('LiquidezCorrente'), 'decimal'))
                            col_a.metric("Payout", formatar_metrica(metricas.get('Payout'), 'percentual'))
                        
                        # Gráfico de barras das pontuações
                        st.markdown("### Pontuações Detalhadas")
                        fig_barras = gerar_grafico_pontuacao(
                            acao['Pontuacoes'],
                            f"Pontuações por Critério - {acao['Ticker']}"
                        )
                        st.plotly_chart(fig_barras, use_container_width=True)
                        
                        # Histórico de preços
                        st.markdown("### Histórico de Preços")
                        
                        try:
                            # Obter dados históricos
                            dados_historicos = yf.Ticker(acao['Ticker']).history(period="1y")
                            
                            if not dados_historicos.empty:
                                # Criar gráfico de preços
                                fig_precos = px.line(
                                    dados_historicos,
                                    y='Close',
                                    title=f"Preço de Fechamento - {acao['Ticker']} (Último Ano)",
                                    labels={'Close': 'Preço de Fechamento (R$)', 'index': 'Data'}
                                )
                                
                                st.plotly_chart(fig_precos, use_container_width=True)
                            else:
                                st.info("Dados históricos não disponíveis para esta ação.")
                        except Exception as e:
                            st.error(f"Erro ao obter dados históricos: {e}")
        else:
            st.warning("Nenhum resultado encontrado. Tente ajustar os parâmetros ou selecionar outras ações.")
    
    # Explicação da metodologia
    with st.expander("Metodologia de Análise"):
        st.markdown("""
        ### Como Funciona o Pro Picks IA

        O Pro Picks IA utiliza uma combinação de inteligência artificial e análise fundamentalista para identificar as melhores oportunidades de investimento no mercado brasileiro. O sistema analisa mais de 250 métricas financeiras de centenas de empresas brasileiras para criar carteiras otimizadas.

        #### Categorias de Critérios e Pesos

        1. **Demonstrações Financeiras e Lucratividade (25%)**
           - ROE (Retorno sobre Patrimônio): Avalia a eficiência da empresa em gerar lucros
           - ROIC (Retorno sobre Capital Investido): Mede o retorno gerado por todo o capital investido
           - Margem Líquida: Indica a eficiência operacional e capacidade de conversão de receitas em lucros
           - Crescimento de Lucros: Avalia a tendência de crescimento dos lucros ao longo do tempo

        2. **Avaliação e Múltiplos (20%)**
           - P/L (Preço/Lucro): Relaciona o preço da ação com o lucro por ação
           - P/VP (Preço/Valor Patrimonial): Relaciona o preço da ação com seu valor patrimonial
           - EV/EBITDA: Avalia o valor da empresa em relação ao seu EBITDA
           - Dividend Yield: Mede o retorno em dividendos em relação ao preço da ação

        3. **Saúde Financeira e Liquidez (20%)**
           - Dívida/Patrimônio: Avalia o nível de alavancagem financeira da empresa
           - Liquidez Corrente: Mede a capacidade da empresa de pagar suas obrigações de curto prazo
           - Payout: Percentual do lucro distribuído como dividendos

        4. **Momento e Tendências de Preço (15%)**
           - Performance Relativa: Compara o desempenho da ação com o Ibovespa
           - Volatilidade: Avalia a estabilidade do preço da ação
           - Volume de Negociação: Mede a liquidez da ação no mercado

        5. **Qualidade e Eficiência (10%)**
           - Giro de Ativos: Mede a eficiência com que a empresa utiliza seus ativos
           - Consistência de Resultados: Avalia a previsibilidade e estabilidade dos resultados financeiros
           - Qualidade dos Lucros: Compara o lucro contábil com o fluxo de caixa operacional

        6. **Fatores Setoriais e Macroeconômicos (10%)**
           - Sensibilidade ao Ciclo Econômico: Avalia como o setor responde a mudanças no cenário macroeconômico
           - Posição Competitiva no Setor: Avalia a posição da empresa em relação aos concorrentes
           - Exposição a Tendências de Longo Prazo: Avalia o alinhamento do negócio com tendências estruturais

        #### Carteiras Temáticas

        O sistema cria quatro tipos principais de carteiras:

        1. **Melhores Ações Brasileiras**: Ações com melhor pontuação geral, que podem liderar o mercado
        2. **Empresas Sólidas**: Empresas altamente lucrativas, com histórico de resultados consistentes e forte solidez financeira
        3. **Ações Defensivas**: Empresas estáveis e pagadoras de dividendos, em setores mais resilientes a ciclos econômicos
        4. **Ações Baratas**: Ações descontadas com fundamentos sólidos, buscando capturar oportunidades de valor

        #### Ajuste ao Cenário Macroeconômico

        O sistema ajusta as recomendações com base no cenário macroeconômico atual:

        - **Expansão**: Favorece empresas cíclicas e de crescimento
        - **Desaceleração**: Favorece empresas de qualidade e setores defensivos
        - **Recessão**: Favorece empresas com balanços sólidos e baixo endividamento
        - **Recuperação**: Favorece empresas cíclicas de qualidade e setores mais sensíveis
        """)
    
    # Rodapé
    st.markdown("---")
    st.markdown("""
    **Pro Picks IA - Simulação** | Desenvolvido com base na metodologia do Pro Picks IA do Investing.com
    
    *Aviso: Esta aplicação é apenas uma simulação e não constitui recomendação de investimento. Consulte um profissional financeiro antes de tomar decisões de investimento.*
    """)

if __name__ == "__main__":
    main()
