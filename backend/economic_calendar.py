from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

log = logging.getLogger("calendar")

# Feed XML publico do ForexFactory (sem chave de API)
FEED_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
# Feed de hoje (fallback)
FEED_TODAY_URL = "https://nfs.faireconomy.media/ff_calendar_today.xml"

CACHE_TTL = 300  # segundos (5 min)

# Moedas/paises relevantes para WIN (Ibovespa) e WDO (dolar)
RELEVANT_COUNTRIES = {"USD", "BRL", "EUR", "CNY", "JPY", "All"}

# Mapeamento de impacto para peso
IMPACT_WEIGHT = {"High": 1.0, "Medium": 0.55, "Low": 0.2, None: 0.0}

# Direcao esperada do evento (para o dolar/WDO e para WIN).
# dolar_up: evento tende a fortalecer o dolar (-> WDO sobe, WIN cai)
# inflacao_up: evento tende a subir inflacao/juros (-> WIN cai, WDO sobe em geral)
HIGH_IMPACT_KEYWORDS = {
    # Listas de palavras-chave e a direcao aproximada no dolar (USD -> WDO)
    "interest rate": {"dir_usd": -1, "label": "Decisão de Juros"},
    "fed funds": {"dir_usd": -1, "label": "Juros do Fed"},
    "fomc": {"dir_usd": -1, "label": "Reunião FOMC"},
    "nonfarm payrolls": {"dir_usd": 1, "label": "Empregos EUA (NFP)"},
    "average hourly earnings": {"dir_usd": 1, "label": "Salário Médio EUA"},
    "unemployment claims": {"dir_usd": -1, "label": "Pedidos de Desemprego"},
    "unemployment rate": {"dir_usd": -1, "label": "Taxa de Desemprego"},
    "cpi": {"dir_usd": 1, "label": "Inflação (CPI)"},
    "inflation": {"dir_usd": 1, "label": "Inflação"},
    "core": {"dir_usd": 0, "label": "Núcleo de Inflação"},
    "gdp": {"dir_usd": 0, "label": "PIB"},
    "pce": {"dir_usd": 1, "label": "Inflação PCE"},
    "retail sales": {"dir_usd": 1, "label": "Vendas no Varejo"},
    "durable goods": {"dir_usd": 1, "label": "Bens Duráveis"},
    "housing": {"dir_usd": 0, "label": "Setor Imobiliário"},
    "pmI": {"dir_usd": 1, "label": "PMI"},
    "ismanufacturing": {"dir_usd": 1, "label": "PMI Industrial"},
    "ism services": {"dir_usd": 1, "label": "PMI Serviços"},
    "philadelphia fed": {"dir_usd": 1, "label": "Fed de Filadélfia"},
    "empire state": {"dir_usd": 1, "label": "Índice Empire State"},
    "consumer confidence": {"dir_usd": 1, "label": "Confiança do Consumidor"},
    "trade balance": {"dir_usd": 1, "label": "Balança Comercial"},
    "current account": {"dir_usd": 0, "label": "Conta Corrente"},
    "speaks": {"dir_usd": 0, "label": "Fala de Autoridade"},
    "chair": {"dir_usd": 0, "label": "Discurso Presidente Fed"},
    "minutes": {"dir_usd": 0, "label": "Atas de Reunião"},
    "jobless": {"dir_usd": -1, "label": "Pedidos de Desemprego"},
}

# Eventos de discurso/autoridade do Fed: direcao incerta, impacto menor
SPEECH_KEYWORDS = ["speaks", "chair", "minutes", "symposium", "meeting"]


def _parse_time(time_str: str, date_str: str) -> Optional[datetime]:
    """Converte '10:45pm' e '08-27-2026' em datetime no fuso America/Sao_Paulo."""
    if not time_str or not date_str:
        return None
    try:
        date_str = date_str.strip()
        parts = date_str.split("-")
        if len(parts) != 3:
            return None
        month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
        time_str = time_str.strip().lower()
        if "am" in time_str or "pm" in time_str:
            time_parts = re.sub(r"[ap]m", "", time_str).strip().split(":")
            hour = int(time_parts[0]) % 12
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
            if "pm" in time_str:
                hour += 12
        else:
            time_parts = time_str.strip().split(":")
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
        now = datetime.now(timezone.utc)
        # O feed usa horario de Brasilia (America/Sao_Paulo) normalmente.
        # Interpretamos como UTC-3
        brasil_tz = timezone(timedelta(hours=-3))
        return datetime(year, month, day, hour, minute, tzinfo=brasil_tz)
    except Exception:
        return None


def _brt_now() -> datetime:
    """Momento atual no fuso de Brasilia (UTC-3)."""
    return datetime.now(timezone(timedelta(hours=-3)))


def _classify_event(title: str) -> dict:
    """Classifica o evento e estima a direcao no dolar (para WDO/WIN)."""
    title_lower = (title or "").lower()
    for kw, info in HIGH_IMPACT_KEYWORDS.items():
        if kw.lower() in title_lower:
            return {"dir_usd": info["dir_usd"], "label": info["label"]}
    return {"dir_usd": 0, "label": title or ""}


@dataclass
class CalendarEvent:
    title: str
    country: str
    impact: str
    date: str
    time: str
    datetime_brt: Optional[datetime] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    url: Optional[str] = None
    dir_usd: int = 0
    label: Optional[str] = None
    is_relevant: bool = False

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "label": self.label or self.title,
            "country": self.country,
            "impact": self.impact,
            "date": self.date,
            "time": self.time,
            "datetime": self.datetime_brt.isoformat() if self.datetime_brt else None,
            "forecast": self.forecast,
            "previous": self.previous,
            "is_relevant": self.is_relevant,
        }


class EconomicCalendar:
    """Baixa o calendario economico (ForexFactory) e fornece eventos + influencia."""

    def __init__(self):
        self._lock = threading.Lock()
        self._events: List[CalendarEvent] = []
        self._today_events: List[CalendarEvent] = []
        self._last_fetch = 0.0
        self._error: Optional[str] = None

    def _fetch_raw(self) -> List[CalendarEvent]:
        if not HAS_REQUESTS:
            return []
        events: List[CalendarEvent] = []
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        for url in (FEED_TODAY_URL, FEED_URL):
            try:
                resp = requests.get(url, headers=headers, timeout=12)
                if resp.status_code != 200:
                    continue
                xml_bytes = resp.content
                # Decodifica, tolerando windows-1252 / utf-8
                try:
                    text = xml_bytes.decode("utf-8-sig")
                except UnicodeDecodeError:
                    text = xml_bytes.decode("windows-1252")
                root = ET.fromstring(text)
                for e in root.findall("event"):
                    title = (e.findtext("title") or "").strip()
                    country = (e.findtext("country") or "").strip()
                    impact = (e.findtext("impact") or "").strip()
                    date = (e.findtext("date") or "").strip()
                    time_str = (e.findtext("time") or "").strip()
                    forecast = (e.findtext("forecast") or "").strip() or None
                    previous = (e.findtext("previous") or "").strip() or None
                    url = (e.findtext("url") or "").strip() or None
                    dt = _parse_time(time_str, date)
                    cls = _classify_event(title)
                    relevant = country.upper() in RELEVANT_COUNTRIES or impact in (
                        "High",
                        "Medium",
                    )
                    events.append(
                        CalendarEvent(
                            title=title,
                            country=country,
                            impact=impact,
                            date=date,
                            time=time_str,
                            datetime_brt=dt,
                            forecast=forecast,
                            previous=previous,
                            url=url,
                            dir_usd=cls["dir_usd"],
                            label=cls["label"],
                            is_relevant=relevant,
                        )
                    )
                break  # primeiro feed que funcionou (hoje antes da semana)
            except Exception as exc:
                log.warning("Erro ao buscar feed calendario (%s): %s", url, exc)
                continue
        return events

    def refresh(self, force: bool = False) -> None:
        with self._lock:
            now = time.time()
            if not force and self._events and (now - self._last_fetch) < CACHE_TTL:
                return
            try:
                events = self._fetch_raw()
                if events:
                    self._events = events
                    now_brt = _brt_now()
                    today_str = now_brt.strftime("%m-%d-%Y")
                    self._today_events = [
                        ev
                        for ev in events
                        if ev.date == today_str or ev.datetime_brt
                        and ev.datetime_brt.date() == now_brt.date()
                    ]
                    self._last_fetch = now
                    self._error = None
                else:
                    self._error = "Nenhum evento obtido do feed"
            except Exception as exc:
                self._error = str(exc)
                log.warning("Erro no refresh do calendario: %s", exc)

    def events(self, force: bool = False) -> List[CalendarEvent]:
        self.refresh(force=force)
        return list(self._events)

    def today(self, force: bool = False) -> List[CalendarEvent]:
        self.refresh(force=force)
        return list(self._today_events)

    def relevant_events(self, force: bool = False) -> List[CalendarEvent]:
        today = self.today(force=force)
        high_med = [e for e in today if e.impact in ("High", "Medium")]
        low_relevant = [e for e in today if e.is_relevant and e.country.upper() == "USD"]
        return high_med + low_relevant

    def next_upcoming(self, limit: int = 8) -> List[CalendarEvent]:
        """Eventos futuros mais proximos (hoje ou proximos dias)."""
        self.refresh()
        now_brt = _brt_now()
        upcoming = []
        for ev in self._events:
            if ev.datetime_brt is None:
                continue
            if ev.datetime_brt >= now_brt:
                upcoming.append(ev)
        upcoming.sort(key=lambda e: e.datetime_brt)
        # prioriza relevantes
        upcoming.sort(key=lambda e: (not e.is_relevant, e.datetime_brt or now_brt))
        return upcoming[:limit]

    @property
    def error(self) -> Optional[str]:
        return self._error


# Instancia unica do calendario (compartilhada entre request handler e endpoint)
calendar_engine = EconomicCalendar()


def calendar_influence(today: Optional[List[CalendarEvent]] = None) -> dict:
    """Calcula a influencia do calendario economico de hoje no WIN e WDO.

    Retorna dict com score de influencia e detalhes dos eventos que moverao o mercado.
    """
    if today is None:
        today = calendar_engine.today()

    if not today:
        return {
            "available": False,
            "influence_win": 0.0,
            "influence_wdo": 0.0,
            "probability_adjust_win": 0.0,
            "probability_adjust_wdo": 0.0,
            "high_impact_count": 0,
            "highlight_count": 0,
            "watch_events": [],
            "note": "Calendário econômico indisponível.",
        }

    now_brt = _brt_now()

    # Considera eventos das proximas 12 horas (importa para o day trading)
    window = timedelta(hours=12)
    in_window = [
        e
        for e in today
        if e.datetime_brt
        and now_brt - timedelta(hours=2) <= e.datetime_brt <= now_brt + window
    ]

    total_influence_win = 0.0
    total_influence_wdo = 0.0
    prob_adj_win = 0.0
    prob_adj_wdo = 0.0
    watch: List[dict] = []
    high_impact_count = 0
    highlight_count = 0

    for e in in_window:
        weight = IMPACT_WEIGHT.get(e.impact, 0.0)
        if e.impact == "High":
            high_impact_count += 1
        if e.impact in ("High", "Medium"):
            highlight_count += 1

        # Relevancia especifica
        is_usd_relevant = e.country.upper() == "USD"
        minutes_until = (
            (e.datetime_brt - now_brt).total_seconds() / 60.0
            if e.datetime_brt
            else 999
        )

        # Efeito no WDO (dolar):
        #   dir_usd=1 (dado forte nos EUA) -> dolar sobe -> WDO sobe
        #   dir_usd=-1 (juros baixando/gasto estimulo) -> dolar cai -> WDO cai
        if is_usd_relevant:
            if e.dir_usd > 0:
                wdo_effect = weight * 8.0
                win_effect = -weight * 3.0  # dolar forte pressiona bolsa
            elif e.dir_usd < 0:
                wdo_effect = -weight * 8.0
                win_effect = weight * 3.0
            else:
                # Direcao incerta (speech, PMI neutro...) -> volatilidade
                wdo_effect = weight * 3.0
                win_effect = weight * 1.5
        else:
            # Eventos de outros paises podem gerar volatilidade geral
            wdo_effect = weight * 1.5
            win_effect = weight * 1.0

        # Nao deixamos influencia de um evento isolado ser absurda
        wdo_effect = max(-6.0, min(6.0, wdo_effect))
        win_effect = max(-3.0, min(3.0, win_effect))

        total_influence_wdo += wdo_effect
        total_influence_win += win_effect

        if e.is_relevant and e.impact in ("High", "Medium"):
            watch.append(
                {
                    "title": e.title,
                    "label": e.label,
                    "country": e.country,
                    "impact": e.impact,
                    "time": e.time,
                    "minutes_until": round(minutes_until),
                    "dir_usd": e.dir_usd,
                    "effect": {
                        "wdo": round(wdo_effect, 1),
                        "win": round(win_effect, 1),
                    },
                }
            )

    # Soma direta para a probabilidade (ajuste leve, nao quebra o sistema)
    prob_adj_wdo = max(-10.0, min(10.0, total_influence_wdo))
    prob_adj_win = max(-10.0, min(10.0, total_influence_win))

    # influencia composicional direta no score (escala maior, mas limitada)
    score_influence_wdo = max(-12.0, min(12.0, total_influence_wdo))
    score_influence_win = max(-8.0, min(8.0, total_influence_win))

    watch.sort(key=lambda w: w["minutes_until"])

    note = ""
    if high_impact_count:
        note = f"{high_impact_count} evento(s) de alto impacto nas próximas horas. Volatilidade elevada esperada."
    elif highlight_count:
        note = "Eventos de médio/alto impacto hoje. Fique atento aos horários."
    else:
        note = "Sem eventos de alto impacto nas próximas horas. Mercado tende a seguir a técnica."

    return {
        "available": True,
        "influence_win": round(score_influence_win, 1),
        "influence_wdo": round(score_influence_wdo, 1),
        "probability_adjust_win": round(prob_adj_win, 1),
        "probability_adjust_wdo": round(prob_adj_wdo, 1),
        "high_impact_count": high_impact_count,
        "highlight_count": highlight_count,
        "watch_events": watch,
        "note": note,
    }
