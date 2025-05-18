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

# Lista de ações brasileiras do Ibovespa
def obter_lista_acoes():
    """Obtém a lista de ações do Ibovespa e outras ações relevantes do mercado brasileiro"""
    try:
        # Tentativa de obter composição do Ibovespa via yfinance
        ibov = yf.Ticker("^BVSP")
        ibov_components = ibov.components
        
        if ibov_components is not None and len(ibov_components) > 0:
            logger.info(f"Obtidas {len(ibov_components)} ações do Ibovespa via yfinance")
            # Adicionar sufixo .SA para ações brasileiras
            acoes = [ticker + ".SA" for ticker in ibov_components]
            return acoes
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
            
            return acoes_ibov + outras_acoes
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
        # Obter objeto ticker
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
        
        # 5. Recomendações de analistas
        try:
            recommendations = acao.recommendations
            if recommendations is not None:
                dados['recommendations'] = recommendations.to_dict('records')
            else:
                dados['recommendations'] = []
        except:
            dados['recommendations'] = []
        
        # 6. Ações institucionais
        try:
            institutional_holders = acao.institutional_holders
            if institutional_holders is not None:
                dados['institutional_holders'] = institutional_holders.to_dict('records')
            else:
                dados['institutional_holders'] = []
        except:
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
            "cambio": pib.history(period="2y").to_dict('records'),
            "inflacao": ipca.history(period="2y").to_dict('records'),
            "juros": selic.history(period="2y").to_dict('records')
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

def coletar_todos_dados():
    """Função principal para coletar todos os dados necessários"""
    logger.info("Iniciando coleta de todos os dados")
    
    # 1. Obter lista de ações
    acoes = obter_lista_acoes()
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
