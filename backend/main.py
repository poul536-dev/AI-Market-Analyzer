from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from security import (
    security_headers_middleware,
    block_sensitive_files_middleware,
    login_rate_limit_middleware,
    login_limiter,
    get_client_ip,
)

from auth import (
    UserLogin, UserCreate,
    authenticate_user, register_user, list_users, delete_user,
    ensure_admin_user, get_current_user, _create_token,
    _set_auth_cookie, _clear_auth_cookie,
)
from config import auth_settings

log = logging.getLogger("main")

PREDICTION_INTERVAL = 300
TUNE_INTERVAL = 600


from analysis import AnalysisEngine
from market_data import MarketDataService
from signal_engine import calculate_score, calculate_probability
from multitimeframe import analyze_multitimeframe
from cross_analysis import analyze_cross
from divergence import detect_divergences
from strategy import StrategyEngine
from risk_manager import RiskManager
from performance import PerformanceTracker
from alerts_advanced import AdvancedAlertSystem
from sentiment import MarketSentiment
from news import NewsAnalyzer
from outcome_tracker import OutcomeTracker
from auto_tune import AutoTuner


async def _background_prediction_loop():
    """Register predictions every 5 min, resolve, and auto-tune periodically."""
    last_tune_time = 0.0
    await asyncio.sleep(10)

    while True:
        try:
            results = analysis_engine.analyze_all()
            current_prices = {}
            for asset_name, analysis in results.items():
                current_prices[asset_name] = analysis.price
                score = calculate_score(analysis)
                sentiment = news_analyzer.get_sentiment_summary(asset_name)
                sent_score = sentiment.get("score", 0)

                signal = "COMPRA" if score.total >= 60 else "VENDA" if score.total <= 40 else "NEUTRO"

                outcome_tracker.record_prediction(
                    asset=asset_name,
                    price=analysis.price,
                    score=score.total,
                    signal=signal,
                    components=score.components,
                    sentiment_score=sent_score,
                    relevance=0.0,
                )

            resolved = outcome_tracker.resolve_predictions(current_prices)
            if resolved:
                log.info("Background: resolved %d predictions", len(resolved))

            now = time.time()
            if (now - last_tune_time) >= TUNE_INTERVAL:
                acc = outcome_tracker.get_accuracy()
                if acc["total_predictions"] >= 15:
                    result = auto_tuner.tune(acc)
                    if result.get("tuned"):
                        log.info("Background auto-tune: %d weights adjusted", len(result.get("changes", {})))
                    last_tune_time = now

        except Exception as e:
            log.error("Background prediction loop error: %s", e)

        await asyncio.sleep(PREDICTION_INTERVAL)


@asynccontextmanager
async def lifespan(app_instance):
    ensure_admin_user()
    log.info("Starting background prediction/tune loop")
    task = asyncio.create_task(_background_prediction_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="AI Market Analyzer", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://192.168.15.8:8000",
        "https://ai-market-analyzer-production.up.railway.app",
        "https://ai-market-analyzer.up.railway.app",
    ],
    allow_origin_regex=r"^(https?://.*\.up\.railway\.app|http://192\.168\.\d+\.\d+:\d+)$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.middleware("http")(security_headers_middleware)
app.middleware("http")(block_sensitive_files_middleware)
app.middleware("http")(login_rate_limit_middleware)

market_service = MarketDataService()
analysis_engine = AnalysisEngine(market_service)
strategy_engine = StrategyEngine()
risk_manager = RiskManager()
performance_tracker = PerformanceTracker()
alert_system = AdvancedAlertSystem()
sentiment_analyzer = MarketSentiment()
news_analyzer = NewsAnalyzer()
outcome_tracker = OutcomeTracker()
auto_tuner = AutoTuner()


def _format_time(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S")


def _market_status() -> str:
    from datetime import timezone, timedelta
    tz_brt = timezone(timedelta(hours=-3))
    now = datetime.now(tz_brt)
    hour = now.hour
    minute = now.minute
    t = hour * 100 + minute
    if 1000 <= t <= 1130 or 1300 <= t <= 1650:
        return "ABERTO"
    return "FECHADO"


@app.get("/mercado")
def get_mercado():
    full = market_service.get_full_data()
    ts = full.get("timestamp", time.time())

    response = {
        "status": "ok",
        "data_source": market_service.data_source,
        "timestamp": _format_time(ts),
        "market_status": _market_status(),
        "assets": {},
    }

    for asset in ["WIN", "WDO"]:
        data = full.get(asset, {})
        if data:
            analysis = analysis_engine.analyze(asset)
            score = calculate_score(analysis)
            prob = calculate_probability(analysis, score)
            response["assets"][asset] = {
                "price": data["price"],
                "variation": analysis.variation,
                "variation_pct": analysis.variation_pct,
                "volume": data["volume"],
                "avg_volume": data["avg_volume"],
                "source": data.get("source", "unknown"),
            }

    return response


@app.get("/mercados")
def get_mercados():
    global_data = market_service.get_global_markets()
    result = {}

    for name, data in global_data.items():
        result[name] = {
            "price": data["price"],
            "open": data["open"],
            "high": data["high"],
            "low": data["low"],
            "volume": data["volume"],
            "source": data.get("source", "yahoo"),
            "ticker": data.get("ticker", ""),
            "name": data.get("name", name),
            "variation": round(data["price"] - data["open"], 2) if data["open"] else 0,
            "variation_pct": round(((data["price"] - data["open"]) / abs(data["open"])) * 100, 4) if data["open"] else 0,
        }

    return {"markets": result, "source": market_service.data_source}


@app.get("/analise")
def get_analise():
    results = analysis_engine.analyze_all()
    output = {}
    current_prices = {}

    for asset_name, analysis in results.items():
        score = calculate_score(analysis)
        prob = calculate_probability(analysis, score)
        ind = analysis.indicators
        sr = ind.sr

        current_prices[asset_name] = analysis.price

        output[asset_name] = {
            "asset": asset_name,
            "source": market_service.data_source,
            "price": analysis.price,
            "open": analysis.open_price,
            "high": analysis.high,
            "low": analysis.low,
            "variation": analysis.variation,
            "variation_pct": analysis.variation_pct,
            "volume": analysis.volume,
            "avg_volume": analysis.avg_volume,
            "volume_ratio": analysis.volume_ratio,
            "forca": score.force,
            "score": score.total,
            "score_label": score.label,
            "score_components": score.components,
            "tendencia": analysis.trend,
            "trend_strength": analysis.trend_strength,
            "vwap": ind.vwap,
            "vwap_position": analysis.vwap_position,
            "vwap_distance_pct": analysis.vwap_distance_pct,
            "ema_9": ind.ema_9,
            "ema_21": ind.ema_21,
            "sma_50": ind.sma_50,
            "sma_200": ind.sma_200,
            "moving_alignment": analysis.moving_avg_alignment,
            "rsi": ind.rsi,
            "rsi_zone": analysis.rsi_zone,
            "macd": ind.macd,
            "roc": ind.roc,
            "momentum": analysis.momentum,
            "momentum_value": analysis.momentum_value,
            "adx": ind.adx,
            "stochastic": ind.stochastic,
            "bollinger": ind.bollinger,
            "atr": ind.atr,
            "suporte_1": sr.get("support_1", 0),
            "suporte_2": sr.get("support_2", 0),
            "resistencia_1": sr.get("resist_1", 0),
            "resistencia_2": sr.get("resist_2", 0),
            "day_high": sr.get("day_high", 0),
            "day_low": sr.get("day_low", 0),
            "probability_up": prob["probability_up"],
            "probability_down": prob["probability_down"],
        }

    outcome_tracker.resolve_predictions(current_prices)

    return output


@app.get("/analise/{asset}")
def get_analise_asset(asset: str):
    asset = asset.upper()
    if asset not in ("WIN", "WDO"):
        return {"error": "Asset not found. Use WIN or WDO."}

    analysis = analysis_engine.analyze(asset)
    score = calculate_score(analysis)
    prob = calculate_probability(analysis, score)
    ind = analysis.indicators
    sr = ind.sr

    return {
        "asset": asset,
        "source": market_service.data_source,
        "price": analysis.price,
        "open": analysis.open_price,
        "high": analysis.high,
        "low": analysis.low,
        "variation": analysis.variation,
        "variation_pct": analysis.variation_pct,
        "volume": analysis.volume,
        "avg_volume": analysis.avg_volume,
        "volume_ratio": analysis.volume_ratio,
        "forca": score.force,
        "score": score.total,
        "score_label": score.label,
        "score_components": score.components,
        "tendencia": analysis.trend,
        "trend_strength": analysis.trend_strength,
        "vwap": ind.vwap,
        "vwap_position": analysis.vwap_position,
        "vwap_distance_pct": analysis.vwap_distance_pct,
        "ema_9": ind.ema_9,
        "ema_21": ind.ema_21,
        "sma_50": ind.sma_50,
        "sma_200": ind.sma_200,
        "moving_alignment": analysis.moving_avg_alignment,
        "rsi": ind.rsi,
        "rsi_zone": analysis.rsi_zone,
        "macd": ind.macd,
        "roc": ind.roc,
        "momentum": analysis.momentum,
        "momentum_value": analysis.momentum_value,
        "adx": ind.adx,
        "stochastic": ind.stochastic,
        "bollinger": ind.bollinger,
        "atr": ind.atr,
        "suporte_1": sr.get("support_1", 0),
        "suporte_2": sr.get("support_2", 0),
        "resistencia_1": sr.get("resist_1", 0),
        "resistencia_2": sr.get("resist_2", 0),
        "day_high": sr.get("day_high", 0),
        "day_low": sr.get("day_low", 0),
        "probability_up": prob["probability_up"],
        "probability_down": prob["probability_down"],
    }


@app.get("/indicadores/{asset}")
def get_indicadores(asset: str):
    asset = asset.upper()
    if asset not in ("WIN", "WDO"):
        return {"error": "Asset not found. Use WIN or WDO."}

    analysis = analysis_engine.analyze(asset)
    ind = analysis.indicators

    return {
        "asset": asset,
        "vwap": ind.vwap,
        "ema_9": ind.ema_9,
        "ema_21": ind.ema_21,
        "sma_50": ind.sma_50,
        "sma_200": ind.sma_200,
        "rsi": ind.rsi,
        "macd": ind.macd,
        "roc": ind.roc,
    }


@app.get("/cenarios")
def get_cenarios():
    results = analysis_engine.analyze_all()
    output = {}

    for asset_name, analysis in results.items():
        sr = analysis.indicators.sr
        price = analysis.price
        resist_1 = sr.get("resist_1", price + 50)
        resist_2 = sr.get("resist_2", price + 100)
        support_1 = sr.get("support_1", price - 50)
        support_2 = sr.get("support_2", price - 100)
        score = calculate_score(analysis)
        prob = calculate_probability(analysis, score)

        output[asset_name] = {
            "cenario_altista": {
                "label": "ALTISTA",
                "condicao": f"Se {asset_name} romper {resist_1} com volume",
                "alvo_1": resist_1 + (resist_1 - support_1) * 0.382,
                "alvo_2": resist_1 + (resist_1 - support_1) * 0.618,
                "confirmacao": "volume + sustentacao acima do rompimento",
                "probabilidade": prob["probability_up"],
            },
            "cenario_baixista": {
                "label": "BAIXISTA",
                "condicao": f"Se {asset_name} perder {support_1}",
                "alvo_1": support_1 - (resist_1 - support_1) * 0.382,
                "alvo_2": support_1 - (resist_1 - support_1) * 0.618,
                "confirmacao": "volume + sustentacao abaixo da perda",
                "probabilidade": prob["probability_down"],
            },
            "cenario_lateral": {
                "label": "LATERAL",
                "condicao": f"Entre {support_1} e {resist_1}",
                "observacao": "Mercado sem direcao clara. Evitar operacoes no meio da faixa.",
            },
        }

    return output


@app.get("/alertas")
def get_alertas():
    results = analysis_engine.analyze_all()
    alerts = []

    for asset_name, analysis in results.items():
        score = calculate_score(analysis)
        sr = analysis.indicators.sr
        price = analysis.price

        if score.total >= 80:
            alerts.append({
                "tipo": "COMPRA FORTE",
                "asset": asset_name,
                "mensagem": f"{asset_name} demonstra compra muito forte. Score: {score.total}/100",
                "severidade": "ALTA",
                "timestamp": _format_time(time.time()),
            })

        if score.total <= 20:
            alerts.append({
                "tipo": "VENDA FORTE",
                "asset": asset_name,
                "mensagem": f"{asset_name} demonstra venda muito forte. Score: {score.total}/100",
                "severidade": "ALTA",
                "timestamp": _format_time(time.time()),
            })

        if analysis.indicators.rsi > 75:
            alerts.append({
                "tipo": "RSI SOBRECOMPRADO",
                "asset": asset_name,
                "mensagem": f"{asset_name} com RSI em {analysis.indicators.rsi}. Possivel reversao para baixo.",
                "severidade": "MEDIA",
                "timestamp": _format_time(time.time()),
            })

        if analysis.indicators.rsi < 25:
            alerts.append({
                "tipo": "RSI SOBREVENDIDO",
                "asset": asset_name,
                "mensagem": f"{asset_name} com RSI em {analysis.indicators.rsi}. Possivel reversao para cima.",
                "severidade": "MEDIA",
                "timestamp": _format_time(time.time()),
            })

        if analysis.volume_ratio > 2.0:
            alerts.append({
                "tipo": "VOLUME ANORMAL",
                "asset": asset_name,
                "mensagem": f"{asset_name} com volume {analysis.volume_ratio}x acima da media.",
                "severidade": "MEDIA",
                "timestamp": _format_time(time.time()),
            })

        resist_1_val = sr.get("resist_1", 0)
        if resist_1_val > 0 and price > resist_1_val * 0.999:
            alerts.append({
                "tipo": "ROMPIMENTO DE RESISTENCIA",
                "asset": asset_name,
                "mensagem": f"{asset_name} proximo ou acima da resistencia em {sr.get('resist_1', 0)}",
                "severidade": "ALTA",
                "timestamp": _format_time(time.time()),
            })

        if price < sr.get("support_1", 0) * 1.001 and sr.get("support_1", 0) > 0:
            alerts.append({
                "tipo": "PROXIMO AO SUPORTE",
                "asset": asset_name,
                "mensagem": f"{asset_name} proximo ao suporte em {sr.get('support_1', 0)}",
                "severidade": "MEDIA",
                "timestamp": _format_time(time.time()),
            })

    if not alerts:
        alerts.append({
            "tipo": "SISTEMA",
            "asset": "GERAL",
            "mensagem": "Nenhum alerta no momento. Mercado dentro dos parametros normais.",
            "severidade": "BAIXA",
            "timestamp": _format_time(time.time()),
        })

    return {"alerts": alerts, "count": len(alerts)}


@app.get("/multitimeframe/{asset}")
def get_multitimeframe(asset: str):
    asset = asset.upper()
    if asset not in ("WIN", "WDO"):
        return {"error": "Asset not found. Use WIN or WDO."}

    full = market_service.get_full_data()
    data = full.get(asset, {})
    if not data:
        return {"error": "No data available"}

    candles = data.get("candles", [])
    result = analyze_multitimeframe(candles)
    result["asset"] = asset
    return result


@app.get("/cross")
def get_cross_analysis():
    full = market_service.get_full_data()
    win_data = full.get("WIN", {})
    wdo_data = full.get("WDO", {})

    win_candles = win_data.get("candles", [])
    wdo_candles = wdo_data.get("candles", [])

    result = analyze_cross(win_candles, wdo_candles)
    return result


@app.get("/divergencias/{asset}")
def get_divergencias(asset: str):
    asset = asset.upper()
    if asset not in ("WIN", "WDO"):
        return {"error": "Asset not found. Use WIN or WDO."}

    full = market_service.get_full_data()
    data = full.get(asset, {})
    if not data:
        return {"error": "No data available"}

    candles = data.get("candles", [])
    divergences = detect_divergences(candles)
    return {"asset": asset, "divergences": divergences, "count": len(divergences)}


@app.get("/estrategias")
def get_estrategias():
    return {"strategies": strategy_engine.get_strategies()}


@app.post("/estrategias/avaliar/{strategy_name}")
def avaliar_estrategia(strategy_name: str):
    full = market_service.get_full_data()
    analise = analysis_engine.analyze_all()
    cross = analyze_cross(
        full.get("WIN", {}).get("candles", []),
        full.get("WDO", {}).get("candles", []),
    )
    cross_dict = cross if isinstance(cross, dict) else {}

    results = {}
    for asset in ["WIN", "WDO"]:
        data = full.get(asset, {})
        if data:
            analysis = analysis_engine.analyze(asset)
            score = calculate_score(analysis)
            analysis_dict = {
                "price": data["price"],
                "score": score.total,
                "tendencia": analysis.trend,
                "rsi": analysis.indicators.rsi,
                "adx": analysis.indicators.adx,
                "volume_ratio": analysis.volume_ratio,
                "vwap_position": analysis.vwap_position,
                "stochastic": analysis.indicators.stochastic,
                "bollinger": analysis.indicators.bollinger,
            }
            result = strategy_engine.evaluate(strategy_name, analysis_dict, cross_dict)
            results[asset] = result

    return {"strategy": strategy_name, "results": results}


@app.post("/estrategias/avaliar-todas")
def avaliar_todas_estrategias():
    full = market_service.get_full_data()
    cross = analyze_cross(
        full.get("WIN", {}).get("candles", []),
        full.get("WDO", {}).get("candles", []),
    )
    cross_dict = cross if isinstance(cross, dict) else {}

    analysis_results = {}
    for asset in ["WIN", "WDO"]:
        data = full.get(asset, {})
        if data:
            analysis = analysis_engine.analyze(asset)
            score = calculate_score(analysis)
            analysis_results[asset] = {
                "price": data["price"],
                "score": score.total,
                "tendencia": analysis.trend,
                "rsi": analysis.indicators.rsi,
                "adx": analysis.indicators.adx,
                "volume_ratio": analysis.volume_ratio,
                "vwap_position": analysis.vwap_position,
                "stochastic": analysis.indicators.stochastic,
                "bollinger": analysis.indicators.bollinger,
            }

    results = strategy_engine.evaluate_all(analysis_results, cross_dict)
    return {"results": results}


@app.get("/risco")
def get_risco():
    full = market_service.get_full_data()
    results = {}

    for asset in ["WIN", "WDO"]:
        data = full.get(asset, {})
        if data:
            analysis = analysis_engine.analyze(asset)
            score = calculate_score(analysis)
            prob = calculate_probability(analysis, score)

            entry = data["price"]
            tick_size = 5.0 if asset == "WIN" else 0.50

            if score.total >= 60:
                sl = entry - 8 * tick_size
                tp = entry + 12 * tick_size
            elif score.total <= 40:
                sl = entry + 8 * tick_size
                tp = entry - 12 * tick_size
            else:
                sl = entry - 5 * tick_size
                tp = entry + 5 * tick_size

            risk_assessment = risk_manager.assess_risk(entry, sl, tp, asset)
            position_suggestion = risk_manager.get_position_suggestion(
                asset, entry, score.total, analysis.trend
            )
            results[asset] = {
                "assessment": risk_assessment,
                "suggestion": position_suggestion,
            }

    return results


@app.get("/performance")
def get_performance():
    return performance_tracker.get_snapshot()


@app.get("/performance/trades")
def get_trades():
    return {"trades": performance_tracker.get_trades()}


@app.post("/performance/reset")
def reset_performance():
    performance_tracker.clear()
    risk_manager.reset_daily()
    return {"status": "ok", "message": "Performance resetada"}


@app.get("/alertas-avancados")
def get_alertas_avancados():
    full = market_service.get_full_data()
    analysis_results = {}

    for asset in ["WIN", "WDO"]:
        data = full.get(asset, {})
        if data:
            analysis = analysis_engine.analyze(asset)
            score = calculate_score(analysis)
            analysis_results[asset] = {
                "score": score.total,
                "rsi": analysis.indicators.rsi,
                "adx": analysis.indicators.adx,
                "volume_ratio": analysis.volume_ratio,
                "price": data["price"],
            }

    triggered = alert_system.check_alerts(analysis_results)
    rules = alert_system.get_rules()
    history = alert_system.get_all_alerts()

    return {
        "triggered": triggered,
        "rules": rules,
        "history": history,
        "triggered_count": len(triggered),
    }


@app.get("/sentimento")
def get_sentimento():
    global_data = market_service.get_global_markets()
    win_data = None
    wdo_data = None

    try:
        win_analysis = analysis_engine.analyze("WIN")
        win_data = {"tendencia": win_analysis.trend, "score": calculate_score(win_analysis).total}
    except Exception:
        pass

    try:
        wdo_analysis = analysis_engine.analyze("WDO")
        wdo_data = {"tendencia": wdo_analysis.trend, "score": calculate_score(wdo_analysis).total}
    except Exception:
        pass

    return sentiment_analyzer.analyze(global_data, win_data, wdo_data)


@app.get("/mt5/status")
def get_mt5_status():
    return market_service.get_mt5_connection()


@app.get("/mt5/tick/{asset}")
def get_mt5_tick(asset: str):
    asset = asset.upper()
    if asset not in ("WIN", "WDO"):
        return {"error": "Asset not found. Use WIN or WDO."}

    if market_service._mt5:
        tick = market_service._mt5.get_tick(asset)
        if tick:
            return tick
    return {"error": "MT5 not connected or no tick data"}


@app.post("/auth/login")
def auth_login(creds: UserLogin, request: Request):
    client_ip = get_client_ip(request)
    user = authenticate_user(creds.username, creds.password)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Credenciais invalidas"})
    login_limiter.reset(client_ip)
    token = _create_token(user["id"], user["username"], user["role"])
    resp = JSONResponse(content={
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "display_name": user.get("display_name", user["username"]),
            "role": user["role"],
        },
    })
    _set_auth_cookie(resp, token)
    return resp


@app.post("/auth/register")
def auth_register(data: UserCreate):
    result = register_user(data.username, data.password, data.display_name)
    if "error" in result:
        return JSONResponse(status_code=400, content=result)
    token = _create_token(result["id"], result["username"], result["role"])
    resp = JSONResponse(content={
        "token": token,
        "user": result,
    })
    _set_auth_cookie(resp, token)
    return resp


@app.get("/auth/me")
def auth_me(user=Depends(get_current_user)):
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    return {"username": user.get("username"), "role": user.get("role")}


@app.post("/auth/logout")
def auth_logout():
    resp = JSONResponse(content={"status": "logged out"})
    _clear_auth_cookie(resp)
    return resp


@app.get("/auth/users")
def auth_list_users(user=Depends(get_current_user)):
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    if user.get("role") != "admin":
        return JSONResponse(status_code=403, content={"error": "Admin access required"})
    return {"users": [u.model_dump() for u in list_users()]}


@app.delete("/auth/users/{user_id}")
def auth_delete_user(user_id: str, user=Depends(get_current_user)):
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    if user.get("role") != "admin":
        return JSONResponse(status_code=403, content={"error": "Admin access required"})
    if delete_user(user_id):
        return {"status": "deleted"}
    return JSONResponse(status_code=404, content={"error": "User not found"})


@app.get("/login")
def serve_login():
    return FileResponse("../build/login.html")


PROTECTED_PATHS = {"/", "/analise", "/cenarios", "/alertas", "/cross",
                   "/multitimeframe", "/divergencias", "/sentimento",
                   "/estrategias", "/risco", "/performance", "/mt5",
                   "/noticias", "/outcome", "/indicadores",
                   "/mercado", "/mercados", "/alertas-avancados"}

PUBLIC_PATHS = {"/login", "/auth/login", "/auth/register", "/auth/me"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    if path.startswith("/static/") or path.startswith("/auth/"):
        return await call_next(request)

    if path in PUBLIC_PATHS:
        return await call_next(request)

    for pp in PROTECTED_PATHS:
        if path == pp or path.startswith(pp + "/"):
            user = get_current_user(request)
            if not user:
                accept = request.headers.get("accept", "")
                if "text/html" in accept:
                    return RedirectResponse(url="/login", status_code=302)
                return JSONResponse(status_code=401, content={"error": "Not authenticated"})
            break

    return await call_next(request)


app.mount("/static", StaticFiles(directory="../build", html=True), name="static")


@app.get("/download/apk")
async def download_apk():
    from fastapi.responses import FileResponse
    search_paths = [
        Path(__file__).resolve().parent.parent / "build" / "AI-Market-Analyzer.apk",
        Path(__file__).resolve().parent.parent / "AI-Market-Analyzer.apk",
        Path(__file__).resolve().parent.parent / "downloads" / "AI-Market-Analyzer.apk",
    ]
    for p in search_paths:
        if p.exists():
            return FileResponse(
                path=str(p),
                filename="AI-Market-Analyzer.apk",
                media_type="application/vnd.android.package-archive",
            )
    return JSONResponse(status_code=404, content={"error": "APK not found"})


@app.get("/noticias")
def get_noticias(limit: int = 20, asset: str = None):
    items = news_analyzer.get_news(limit=limit, asset=asset)
    return {"news": items, "count": len(items)}


@app.get("/noticias/resumo")
def get_noticias_resumo(asset: str = None):
    return news_analyzer.get_sentiment_summary(asset=asset)


@app.get("/noticias/projecao/{asset}")
def get_noticias_projecao(asset: str):
    asset = asset.upper()
    if asset not in ("WIN", "WDO"):
        return {"error": "Asset not found. Use WIN or WDO."}

    analysis = analysis_engine.analyze(asset)
    score = calculate_score(analysis)

    return news_analyzer.get_projection(
        asset=asset,
        score=score.total,
        trend=analysis.trend,
    )


@app.get("/outcome/acuracia")
def get_outcome_accuracy():
    return outcome_tracker.get_accuracy()


@app.get("/outcome/historico")
def get_outcome_history(limit: int = 20):
    return {"history": outcome_tracker.get_history(limit)}


@app.get("/outcome/pendentes")
def get_outcome_pending():
    return {"pending": outcome_tracker.get_pending_count()}


@app.post("/outcome/registrar")
def register_predictions():
    full = market_service.get_full_data()
    results = []

    for asset in ["WIN", "WDO"]:
        data = full.get(asset, {})
        if not data:
            continue

        analysis = analysis_engine.analyze(asset)
        score = calculate_score(analysis)

        news_asset = news_analyzer.get_sentiment_summary(asset)
        sent_score = news_asset.get("score", 0)

        pred_id = outcome_tracker.record_prediction(
            asset=asset,
            price=data["price"],
            score=score.total,
            signal=score.label,
            components=score.components,
            sentiment_score=sent_score,
            relevance=news_asset.get("total", 0),
        )
        results.append({"asset": asset, "prediction_id": pred_id, "score": score.total})

    current_prices = {}
    for asset in ["WIN", "WDO"]:
        data = full.get(asset, {})
        if data:
            current_prices[asset] = data["price"]

    resolved = outcome_tracker.resolve_predictions(current_prices)

    accuracy = outcome_tracker.get_accuracy()
    tune_result = auto_tuner.tune(accuracy)

    return {
        "registered": results,
        "resolved": resolved,
        "accuracy": accuracy,
        "auto_tune": tune_result,
    }


@app.post("/outcome/reset")
def reset_outcomes():
    outcome_tracker.clear()
    auto_tuner.reset_weights()
    return {"status": "ok", "message": "Outcomes and weights reset"}


@app.get("/outcome/pesos")
def get_current_weights():
    return auto_tuner.get_current_weights()


@app.get("/outcome/historico-pesos")
def get_weights_history():
    return {"history": auto_tuner.get_tune_history()}


@app.get("/")
def serve_dashboard(user=Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return FileResponse("../build/index.html")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
