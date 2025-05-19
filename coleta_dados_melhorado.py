"""
Coleta de Dados Fundamentalistas para Simulação do Pro Picks IA
Este script coleta dados fundamentalistas de ações brasileiras via Yahoo Finance API
"""

import sys
import os
import pandas as pd
import numpy as np
import time
import json
from datetime import datetime, timedelta
import requests
import yfinance as yf
import logging
import re

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("coleta_dados.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Diretório para salvar os dados
DATA_DIR = "dados"
os.makedirs(DATA_DIR, exist_ok=True)

# Função auxiliar para converter índices Timestamp para string
def converter_indices_para_string(obj):
    """Converte índices Timestamp para string em dicionários, listas e DataFrames"""
    if isinstance(obj, dict):
        # Converter chaves Timestamp para string
        return {str(k) if hasattr(k, 'strftime') else k: converter_indices_para_string(v) 
                for k, v in obj.items()}
    elif isinstance(obj, list):
        return [converter_indices_para_string(item) for item in obj]
    elif isinstance(obj, pd.DataFrame):
        # Para DataFrames, converter para dicionário com índices como string
        return obj.reset_index().to_dict('records')
    elif isinstance(obj, pd.Series):
        # Para Series, converter para dicionário com índices como string
        return obj.reset_index().to_dict('records')
    else:
        return obj

# Função para validar ticker
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

# Lista de ações brasileiras do Ibovespa e outras relevantes
def obter_lista_acoes(limite=None, incluir_small_caps=True, incluir_mid_caps=True):
    """Obtém a lista de ações do Ibovespa e outras ações relevantes do mercado brasileiro
    
    Args:
        limite (int, optional): Limitar o número de ações retornadas. None para todas.
        incluir_small_caps (bool, optional): Incluir ações de small caps. Default True.
        incluir_mid_caps (bool, optional): Incluir ações de mid caps. Default True.
    
    Returns:
        list: Lista de tickers no formato XXXX3.SA
    """
    try:
        # Tentativa de obter composição do Ibovespa via yfinance
        ibov = yf.Ticker("^BVSP")
        ibov_components = ibov.components
        
        if ibov_components is not None and len(ibov_components) > 0:
            logger.info(f"Obtidas {len(ibov_components)} ações do Ibovespa via yfinance")
            # Adicionar sufixo .SA para ações brasileiras
            acoes = [ticker + ".SA" for ticker in ibov_components]
        else:
            # Lista manual de ações do Ibovespa caso a API não retorne
            logger.warning("Não foi possível obter componentes do Ibovespa via API. Usando lista manual.")
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
            
            acoes = acoes_ibov
            
            # Adicionar outras ações relevantes fora do Ibovespa
            if incluir_mid_caps:
                mid_caps = [
                    "AESB3.SA", "AURE3.SA", "AZEV4.SA", "BMGB4.SA", "BRSR6.SA",
                    "CEAB3.SA", "CGAS5.SA", "CSMG3.SA", "CXSE3.SA", "DIRR3.SA",
                    "EVEN3.SA", "FESA4.SA", "FRAS3.SA", "GRND3.SA", "HBOR3.SA",
                    "JHSF3.SA", "KEPL3.SA", "LOGG3.SA", "MDIA3.SA", "MOVI3.SA",
                    "ODPV3.SA", "POMO4.SA", "POSI3.SA", "PTBL3.SA", "QUAL3.SA",
                    "ROMI3.SA", "SAPR11.SA", "SEER3.SA", "TASA4.SA", "TGMA3.SA",
                    "TUPY3.SA", "VULC3.SA", "WIZS3.SA"
                ]
                acoes.extend(mid_caps)
            
            # Adicionar small caps
            if incluir_small_caps:
                small_caps = [
                    "AGRO3.SA", "ALLD3.SA", "ALPK3.SA", "ALUP11.SA", "AMAR3.SA",
                    "AMBP3.SA", "ARZZ3.SA", "ATOM3.SA", "AVLL3.SA", "BAHI3.SA",
                    "BAUH4.SA", "BEES3.SA", "BLAU3.SA", "BMOB3.SA", "BOAS3.SA",
                    "BPAN4.SA", "BRBI11.SA", "BRPR3.SA", "BRQB3.SA", "BSEV3.SA",
                    "CAML3.SA", "CARD3.SA", "CBAV3.SA", "CEDO4.SA", "CEPE5.SA",
                    "CGRA4.SA", "CLSC4.SA", "CMIN3.SA", "COCE5.SA", "CPRE3.SA",
                    "CRDE3.SA", "CSED3.SA", "CTKA4.SA", "CTSA4.SA", "DASA3.SA",
                    "DEXP3.SA", "DEXP4.SA", "DMMO3.SA", "DTCY3.SA", "EALT4.SA",
                    "ECOR3.SA", "ENAT3.SA", "EUCA4.SA", "EZTC3.SA", "FHER3.SA",
                    "FIGE3.SA", "FIQE3.SA", "FRAS3.SA", "FRTA3.SA", "GEPA4.SA",
                    "GFSA3.SA", "GGPS3.SA", "GMAT3.SA", "GPCP3.SA", "GSHP3.SA",
                    "HAGA4.SA", "HBTS5.SA", "HETA4.SA", "HOOT4.SA", "IDVL4.SA",
                    "IFCM3.SA", "IGBR3.SA", "IGTA3.SA", "INEP4.SA", "JFEN3.SA",
                    "JOPA3.SA", "JSLG3.SA", "KEPL3.SA", "LAME4.SA", "LCAM3.SA",
                    "LEVE3.SA", "LIGT3.SA", "LINX3.SA", "LIPR3.SA", "LLIS3.SA",
                    "LOGN3.SA", "LPSB3.SA", "LUPA3.SA", "LUXM4.SA", "LVTC3.SA",
                    "MDNE3.SA", "MEAL3.SA", "MEND5.SA", "MILS3.SA", "MLAS3.SA",
                    "MNPR3.SA", "MTIG4.SA", "MTSA4.SA", "MWET4.SA", "MYPK3.SA",
                    "NEOE3.SA", "NORD3.SA", "OIBR3.SA", "OIBR4.SA", "OSXB3.SA",
                    "PATI4.SA", "PDGR3.SA", "PFRM3.SA", "PGMN3.SA", "PINE4.SA",
                    "PLPL3.SA", "PMAM3.SA", "PNVL3.SA", "POWE3.SA", "PRIO3.SA",
                    "PSSA3.SA", "PTNT4.SA", "QUSW3.SA", "RAPT4.SA", "RCSL4.SA",
                    "RECV3.SA", "REDE3.SA", "RNEW11.SA", "ROMI3.SA", "RPMG3.SA",
                    "RSID3.SA", "RSUL4.SA", "SANB11.SA", "SCAR3.SA", "SEER3.SA",
                    "SEQL3.SA", "SGPS3.SA", "SHOW3.SA", "SHUL4.SA", "SIMH3.SA",
                    "SLCE3.SA", "SLED3.SA", "SNSY5.SA", "SOJA3.SA", "SQIA3.SA",
                    "STBP3.SA", "STTR3.SA", "TCNO4.SA", "TCSA3.SA", "TECN3.SA",
                    "TEKA4.SA", "TELB4.SA", "TESA3.SA", "TGMA3.SA", "TIET11.SA",
                    "TKNO4.SA", "TOTS3.SA", "TPIS3.SA", "TRIS3.SA", "TRPL4.SA",
                    "TXRX4.SA", "UCAS3.SA", "UNIP6.SA", "USIM3.SA", "VAMO3.SA",
                    "VIVA3.SA", "VIVR3.SA", "VLID3.SA", "VSPT3.SA", "VULC3.SA",
                    "WLMM4.SA", "YDUQ3.SA", "ZAMP3.SA"
                ]
                acoes.extend(small_caps)
        
        # Remover duplicatas
        acoes = list(set(acoes))
        
        # Limitar o número de ações se solicitado
        if limite is not None and limite > 0 and limite < len(acoes):
            acoes = acoes[:limite]
        
        logger.info(f"Lista final com {len(acoes)} ações")
        return acoes
    except Exception as e:
        logger.error(f"Erro ao obter lista de ações: {e}")
        # Lista de fallback em caso de erro
        acoes_fallback = [
            "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "B3SA3.SA",
            "ABEV3.SA", "WEGE3.SA", "RENT3.SA", "BBAS3.SA", "SUZB3.SA"
        ]
        return acoes_fallback

def obter_dados_fundamentalistas(ticker):
    """Obtém dados fundamentalistas para um ticker específico"""
    logger.info(f"Coletando dados fundamentalistas para {ticker}")
    try:
        # Validar ticker
        ticker_validado = validar_ticker(ticker)
        if not ticker_validado:
            logger.warning(f"Ticker inválido: {ticker}")
            return False
        
        ticker = ticker_validado
        
        # Obter objeto ticker
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
                dividends_dict = {}
                for timestamp, value in dividends.items():
                    # Converter timestamp para string ISO
                    dividends_dict[str(timestamp)] = value
                dados['dividends'] = dividends_dict
            else:
                dados['dividends'] = {}
        except Exception as e:
            logger.warning(f"Erro ao obter dividendos para {ticker}: {e}")
            dados['dividends'] = {}
        
        # 5. Recomendações de analistas
        try:
            recommendations = acao.recommendations
            if recommendations is not None and not recommendations.empty:
                dados['recommendations'] = converter_indices_para_string(recommendations)
            else:
                dados['recommendations'] = []
        except Exception as e:
            logger.warning(f"Erro ao obter recomendações para {ticker}: {e}")
            dados['recommendations'] = []
        
        # 6. Ações institucionais
        try:
            institutional_holders = acao.institutional_holders
            if institutional_holders is not None and not institutional_holders.empty:
                dados['institutional_holders'] = converter_indices_para_string(institutional_holders)
            else:
                dados['institutional_holders'] = []
        except Exception as e:
            logger.warning(f"Erro ao obter ações institucionais para {ticker}: {e}")
            dados['institutional_holders'] = []
        
        # Salvar dados em arquivo JSON
        arquivo = os.path.join(DATA_DIR, f"{ticker.replace('.', '_')}.json")
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados, f, default=str)
        
        logger.info(f"Dados de {ticker} salvos com sucesso")
        return True
    
    except Exception as e:
        logger.error(f"Erro ao coletar dados para {ticker}: {e}")
        return False

def obter_dados_ibovespa():
    """Obtém dados históricos do Ibovespa para comparação"""
    logger.info("Coletando dados históricos do Ibovespa")
    try:
        ibov = yf.Ticker("^BVSP")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=2*365)
        hist = ibov.history(start=start_date, end=end_date, interval="1d")
        
        # Salvar dados em arquivo CSV
        arquivo = os.path.join(DATA_DIR, "ibovespa_historico.csv")
        hist.to_csv(arquivo)
        
        logger.info("Dados do Ibovespa salvos com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao coletar dados do Ibovespa: {e}")
        return False

def obter_dados_macroeconomicos():
    """Obtém dados macroeconômicos do Brasil"""
    logger.info("Coletando dados macroeconômicos")
    try:
        # Dados do PIB brasileiro (ticker do Yahoo Finance)
        pib = yf.Ticker("BRLUSD=X")  # Taxa de câmbio como proxy
        
        # Dados de inflação (IPCA)
        ipca = yf.Ticker("BZ=F")  # Futuros do Brasil como proxy
        
        # Dados da taxa Selic
        selic = yf.Ticker("IRBRP=X")  # Taxa interbancária como proxy
        
        # Salvar dados em arquivos separados
        dados_macro = {
            "cambio": converter_indices_para_string(pib.history(period="2y")),
            "inflacao": converter_indices_para_string(ipca.history(period="2y")),
            "juros": converter_indices_para_string(selic.history(period="2y"))
        }
        
        arquivo = os.path.join(DATA_DIR, "dados_macroeconomicos.json")
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados_macro, f, default=str)
        
        logger.info("Dados macroeconômicos salvos com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao coletar dados macroeconômicos: {e}")
        return False

def obter_dados_setoriais():
    """Classifica as ações por setor e obtém dados setoriais"""
    logger.info("Coletando dados setoriais")
    try:
        acoes = obter_lista_acoes()
        setores = {}
        
        for ticker in acoes:
            try:
                acao = yf.Ticker(ticker)
                info = acao.info
                
                if 'sector' in info and info['sector'] is not None:
                    setor = info['sector']
                    if setor not in setores:
                        setores[setor] = []
                    setores[setor].append(ticker)
            except Exception as e:
                logger.warning(f"Não foi possível obter setor para {ticker}: {e}")
        
        # Salvar classificação setorial
        arquivo = os.path.join(DATA_DIR, "classificacao_setorial.json")
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(setores, f)
        
        logger.info(f"Classificação setorial concluída: {len(setores)} setores identificados")
        return True
    except Exception as e:
        logger.error(f"Erro ao coletar dados setoriais: {e}")
        return False

def coletar_todos_dados(limite=None, incluir_small_caps=True, incluir_mid_caps=True, tickers_personalizados=None):
    """Função principal para coletar todos os dados necessários
    
    Args:
        limite (int, optional): Limitar o número de ações retornadas. None para todas.
        incluir_small_caps (bool, optional): Incluir ações de small caps. Default True.
        incluir_mid_caps (bool, optional): Incluir ações de mid caps. Default True.
        tickers_personalizados (list, optional): Lista de tickers personalizados para coleta.
    
    Returns:
        tuple: (sucessos, falhas, total)
    """
    logger.info("Iniciando coleta de todos os dados")
    
    # 1. Obter lista de ações
    if tickers_personalizados:
        acoes = tickers_personalizados
        logger.info(f"Usando lista personalizada com {len(acoes)} ações")
    else:
        acoes = obter_lista_acoes(limite, incluir_small_caps, incluir_mid_caps)
        logger.info(f"Total de {len(acoes)} ações para coleta")
    
    # 2. Coletar dados do Ibovespa
    obter_dados_ibovespa()
    
    # 3. Coletar dados macroeconômicos
    obter_dados_macroeconomicos()
    
    # 4. Coletar dados setoriais
    obter_dados_setoriais()
    
    # 5. Coletar dados fundamentalistas para cada ação
    sucessos = 0
    falhas = 0
    
    for ticker in acoes:
        try:
            resultado = obter_dados_fundamentalistas(ticker)
            if resultado:
                sucessos += 1
            else:
                falhas += 1
            # Pausa para evitar limitações de API
            time.sleep(1)
        except Exception as e:
            logger.error(f"Erro não tratado ao processar {ticker}: {e}")
            falhas += 1
    
    logger.info(f"Coleta concluída. Sucessos: {sucessos}, Falhas: {falhas}")
    
    # 6. Gerar relatório de coleta
    gerar_relatorio_coleta(sucessos, falhas, acoes)
    
    return sucessos, falhas, len(acoes)

def gerar_relatorio_coleta(sucessos, falhas, acoes):
    """Gera um relatório da coleta de dados"""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    relatorio = {
        "data_coleta": agora,
        "total_acoes": len(acoes),
        "sucessos": sucessos,
        "falhas": falhas,
        "taxa_sucesso": round(sucessos / len(acoes) * 100, 2) if len(acoes) > 0 else 0,
        "acoes_coletadas": [ticker for ticker in acoes if os.path.exists(os.path.join(DATA_DIR, f"{ticker.replace('.', '_')}.json"))]
    }
    
    arquivo = os.path.join(DATA_DIR, "relatorio_coleta.json")
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(relatorio, f, default=str)
    
    logger.info(f"Relatório de coleta gerado: {arquivo}")
    return relatorio

def verificar_qualidade_dados():
    """Verifica a qualidade dos dados coletados"""
    logger.info("Verificando qualidade dos dados coletados")
    
    # Listar todos os arquivos JSON no diretório de dados
    arquivos = [f for f in os.listdir(DATA_DIR) if f.endswith('.json') and not f.startswith('relatorio') and not f.startswith('dados_macro') and not f.startswith('classificacao')]
    
    resultados = {
        "total_arquivos": len(arquivos),
        "arquivos_completos": 0,
        "arquivos_parciais": 0,
        "arquivos_problematicos": 0,
        "metricas_disponiveis": {},
        "problemas_encontrados": []
    }
    
    # Métricas fundamentais a verificar
    metricas_fundamentais = [
        "info", "income_statement", "balance_sheet", "cash_flow", 
        "historical", "dividends"
    ]
    
    for metrica in metricas_fundamentais:
        resultados["metricas_disponiveis"][metrica] = 0
    
    for arquivo in arquivos:
        try:
            caminho = os.path.join(DATA_DIR, arquivo)
            with open(caminho, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            
            # Verificar presença de métricas fundamentais
            metricas_presentes = 0
            for metrica in metricas_fundamentais:
                if metrica in dados and dados[metrica]:
                    if isinstance(dados[metrica], dict) and len(dados[metrica]) > 0:
                        metricas_presentes += 1
                        resultados["metricas_disponiveis"][metrica] += 1
                    elif isinstance(dados[metrica], list) and len(dados[metrica]) > 0:
                        metricas_presentes += 1
                        resultados["metricas_disponiveis"][metrica] += 1
            
            # Classificar qualidade do arquivo
            if metricas_presentes == len(metricas_fundamentais):
                resultados["arquivos_completos"] += 1
            elif metricas_presentes >= len(metricas_fundamentais) // 2:
                resultados["arquivos_parciais"] += 1
            else:
                resultados["arquivos_problematicos"] += 1
                resultados["problemas_encontrados"].append({
                    "arquivo": arquivo,
                    "metricas_presentes": metricas_presentes,
                    "metricas_ausentes": len(metricas_fundamentais) - metricas_presentes
                })
                
        except Exception as e:
            logger.error(f"Erro ao verificar arquivo {arquivo}: {e}")
            resultados["arquivos_problematicos"] += 1
            resultados["problemas_encontrados"].append({
                "arquivo": arquivo,
                "erro": str(e)
            })
    
    # Calcular percentuais
    if resultados["total_arquivos"] > 0:
        resultados["percentual_completos"] = round(resultados["arquivos_completos"] / resultados["total_arquivos"] * 100, 2)
        resultados["percentual_parciais"] = round(resultados["arquivos_parciais"] / resultados["total_arquivos"] * 100, 2)
        resultados["percentual_problematicos"] = round(resultados["arquivos_problematicos"] / resultados["total_arquivos"] * 100, 2)
    
    # Salvar relatório de qualidade
    arquivo_relatorio = os.path.join(DATA_DIR, "relatorio_qualidade.json")
    with open(arquivo_relatorio, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, default=str)
    
    logger.info(f"Relatório de qualidade gerado: {arquivo_relatorio}")
    return resultados

def coletar_dados_acao_personalizada(ticker):
    """Coleta dados para um ticker específico e retorna os dados"""
    ticker_validado = validar_ticker(ticker)
    if not ticker_validado:
        logger.warning(f"Ticker inválido: {ticker}")
        return None
    
    resultado = obter_dados_fundamentalistas(ticker_validado)
    if resultado:
        arquivo = os.path.join(DATA_DIR, f"{ticker_validado.replace('.', '_')}.json")
        with open(arquivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

if __name__ == "__main__":
    # Criar diretório de dados se não existir
    os.makedirs(DATA_DIR, exist_ok=True)
    
    logger.info("Iniciando processo de coleta de dados fundamentalistas")
    
    # Coletar todos os dados
    sucessos, falhas, total = coletar_todos_dados()
    
    # Verificar qualidade dos dados
    resultados_qualidade = verificar_qualidade_dados()
    
    logger.info(f"Processo concluído. Coletados dados de {sucessos}/{total} ações.")
    logger.info(f"Qualidade: {resultados_qualidade['percentual_completos']}% completos, {resultados_qualidade['percentual_parciais']}% parciais, {resultados_qualidade['percentual_problematicos']}% problemáticos")
