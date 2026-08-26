# AI Market Analyzer

Plataforma profissional de analise de mercado financeiro para Day Trade na B3, com foco em Mini Indice (WIN) e Mini Dolar (WDO).

## Como Usar

### Iniciar a Plataforma

Clique duplo em **`start.bat`** na pasta do projeto.

O servidor ira iniciar automaticamente e o navegador abrira em `http://localhost:8000`.

### Parar a Plataforma

Clique duplo em **`stop.bat`**.

### Login

| Campo | Valor |
|-------|-------|
| Usuario | `admin` |
| Senha | `admin123` |

> Altere a senha editando `ADMIN_PASSWORD` no arquivo `.env` e reinicie o servidor.

## Credenciais

As credenciais ficam no arquivo `.env` na raiz do projeto. Nao compartilhe este arquivo.

```
AUTH_SECRET_KEY=chave_secreta_jwt
ADMIN_USERNAME=admin
ADMIN_PASSWORD=sua_senha
MT5_LOGIN=2194500971
MT5_SERVER=ClearInvestimentos-DEMO
MT5_PASSWORD=sua_senha_mt5
```

## Estrutura do Projeto

```
AI-Market-Analyzer/
├── start.bat           # Iniciar servidor
├── stop.bat            # Parar servidor
├── .env                # Credenciais (NAO committar!)
├── .env.example        # Modelo do .env
├── build_frontend.py   # Minificar frontend
├── backend/
│   ├── main.py         # Servidor FastAPI
│   ├── config.py       # Configuracoes
│   ├── auth.py         # Sistema de login
│   ├── security.py     # Protecoes
│   ├── market_data.py  # Fontes de dados (MT5/Brapi/Yahoo)
│   ├── indicators.py   # Indicadores tecnicos
│   ├── analysis.py     # Motor de analise
│   ├── signal_engine.py# Score e sinais
│   └── ...
├── frontend/
│   ├── index.html      # Dashboard
│   ├── login.html      # Pagina de login
│   ├── app.js          # Logica do frontend
│   ├── battle-engine.js# Animacao de batalha
│   └── style.css       # Estilos
├── build/              # Versao minificada (auto-gerada)
└── data/               # Dados salvos
```

## Funcionalidades

- **Dados em Tempo Real**: Conexao com MetaTrader 5 para WINV26 e WDOU26
- **Indicadores Tecnicos**: VWAP, EMA, SMA, RSI, MACD, Bollinger, Stochastic, ADX, ATR, ROC
- **Analise Cruzada**: Correlacao WIN/WDO, divergencias
- **Multi-Timeframe**: Analise em multiplos periodos
- **Noticias**: 11 feeds RSS com analise de sentimento
- **Cenarios**: Altista, Baixista, lateral com probabilidades
- **Alertas**: Sistema de alertas avancados
- **Gestao de Risco**: Posicao, stop, risk/reward
- **Outcome Tracker**: Registro e resolucao de previsoes
- **Auto-Tune**: Ajuste automatico de pesos do score
- **Batalha Visual**: Arena animada com forca compradores vs vendedores
- **Login Seguro**: JWT com httpOnly cookies, rate limiting

## Seguranca

- Chaves secretas em `.env` (fora do codigo)
- Rate limiting no login (15 tentativas/min)
- Headers de seguranca (CSP, X-Frame-Options, etc.)
- Arquivos sensiveis bloqueados (.py, .env, .json)
- Binding apenas em 127.0.0.1 (acesso local)

## Requisitos

- Python 3.10+
- MetaTrader 5 (opcional, para dados reais)

## Instalacao Manual (alternativa ao start.bat)

```bash
cd AI-Market-Analyzer
pip install -r requirements.txt
cd backend
py -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Acesse: http://localhost:8000

## Tecnologias

- **Backend**: Python, FastAPI, Uvicorn, Pydantic
- **Frontend**: HTML5, CSS3, JavaScript
- **Dados**: MetaTrader 5, Brapi.dev, Yahoo Finance
- **Auth**: JWT, bcrypt, httpOnly cookies

## Aviso

Este software e uma ferramenta de analise e nao constitui recomendacao de investimento.
