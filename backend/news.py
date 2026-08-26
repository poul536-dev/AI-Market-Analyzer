from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import List
from html import unescape

try:
    import feedparser

    HAS_FEED = True
except ImportError:
    HAS_FEED = False

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

log = logging.getLogger("news")

RSS_FEEDS = {
    "infomoney_mercados": "https://www.infomoney.com.br/mercados/feed/",
    "infomoney_economia": "https://www.infomoney.com.br/economia/feed/",
    "infomoney_ultimas": "https://www.infomoney.com.br/ultimas-noticias/feed/",
    "investing_br": "https://br.investing.com/rss/news.rss",
    "investing_market": "https://br.investing.com/rss/news_285.rss",
    "investing_stocks": "https://br.investing.com/rss/news_301.rss",
    "investing_macro": "https://br.investing.com/rss/news_25.rss",
    "google_ibov": "https://news.google.com/rss/search?q=ibovespa+bolsa&hl=pt-BR&gl=BR&ceid=BR:pt-419",
    "google_win": "https://news.google.com/rss/search?q=mini+indice+ibovespa+WIN&hl=pt-BR&gl=BR&ceid=BR:pt-419",
    "google_wdo": "https://news.google.com/rss/search?q=dolar+cotacao+real+trader&hl=pt-BR&gl=BR&ceid=BR:pt-419",
    "google_mercado": "https://news.google.com/rss/search?q=mercado+financeiro+investimentos&hl=pt-BR&gl=BR&ceid=BR:pt-419",
}

POSITIVE_WORDS = {
    "alta": 2, "subir": 2, "sobe": 2, "subiu": 2, "sobem": 2,
    "ganho": 2, "ganhos": 2, "lucro": 2, "lucros": 2,
    "recorde": 3, "maxima": 2, "máxima": 2, "máximas": 2,
    "positivo": 2, "positiva": 2, "crescimento": 2, "cresce": 2,
    "rompimento": 2, "rompe": 2, "rompeu": 2,
    "valorização": 2, "valorizou": 2, "valoriza": 2,
    "compra": 1, "comprador": 1, "compradores": 1,
    "oportunidade": 1, "otimismo": 2, "otimista": 2,
    "recuperação": 2, "recupera": 2, "superou": 2,
    "avanço": 2, "avançou": 2, "avança": 2,
    "acordo": 1, "estabilidade": 1, "estável": 1,
    "estimulo": 2, "estímulo": 2, "incentivo": 1,
    "bull": 2, "rally": 2, "boom": 2, "safe haven": 1,
    "dividendo": 1, "proventos": 1, "dy": 1,
    "surpreendeu": 2, "surpresa positiva": 3,
    "acima da expectativa": 3, "superação": 2,
}

NEGATIVE_WORDS = {
    "queda": -2, "cai": -2, "caiu": -2, "caem": -2, "caindo": -2,
    "perda": -2, "perdas": -2, "prejuizo": -3, "prejuízo": -3,
    "crise": -3, "negativo": -2, "negativa": -2,
    "derrota": -2, "preocupa": -2, "preocupação": -2,
    "preocupacoes": -2, "preocupações": -2,
    "sell-off": -3, "tomba": -3, "despencou": -3, "despenca": -3,
    "pânico": -3, "panico": -3, "medo": -2,
    "incerteza": -1, "incerto": -1, "volatil": -1,
    "volatilidade": -1, "correção": -2, "correcao": -2,
    "recessão": -3, "recessao": -3,
    "inflação": -1, "inflacao": -1,
    "juros altos": -2, "taxa de juros": -1,
    "risco": -1,
    "guerra": -2, "conflito": -2, "tensão": -1, "tensao": -1,
    "sanção": -1, "sancoes": -1, "tarifa": -1, "tarifas": -1,
    "bancarrota": -3, "default": -3, "calote": -3,
    "speculative": -1, "bear": -2, "crash": -3,
    "cortou": -2, "reduziu": -1, "demissão": -2, "demissoes": -2,
    "investigação": -1, "investigacao": -1, "escândalo": -2,
    "escandalo": -2, "fraude": -3, "corrupção": -2,
    "surpresa negativa": -3, "abaixo da expectativa": -3,
    "desemprego": -1, "desempregado": -1,
}

ASSET_KEYWORDS = {
    "WIN": [
        "ibovespa", "ibov", "indice", "índice", "bolsa", "bovespa",
        "mini indice", "mini índice", "win", "futuro do indice",
        "ações", "acoes", "stock", "equity", "small cap", "large cap",
        "PETR", "VALE", "ITUB", "BBDC", "ABEV", "WEG", "RENT",
        "BBAS", "SUZB", "PRIO", "RADL", "VIIA", "MGLU",
    ],
    "WDO": [
        "dolar", "dólar", "usd", "cambio", "câmbio", "moeda",
        "real", "reais", "realidade", "exchange rate",
        "dolar comercial", "dólar comercial", "ptax",
        "juros", "selic", "copom", "banco central", "bcb",
        "taxa", "renda fixa", "tesouro", "debênture",
        "inflação", "ipca", "igpm",
    ],
}

HIGH_RELEVANCE_KEYWORDS = [
    "ibovespa", "mini indice", "mini índice", "win", "wdo",
    "dolar", "dólar", "bolsa", "bovespa", "petrobras", "vale",
    "copom", "selic", "banco central", "bcb", "fazenda",
    "pib", "inflação", "ipca", "trade", "tarifa", "tarifas",
    "trump", "fed", "federal reserve", "juros", "recession",
]


@dataclass
class NewsItem:
    title: str
    summary: str
    link: str
    published: str
    published_ts: float
    source: str
    sentiment: float
    sentiment_label: str
    relevance: float
    asset_relevance: dict
    keywords_matched: List[str]


class NewsAnalyzer:
    def __init__(self) -> None:
        self._cache: List[NewsItem] = []
        self._cache_time: float = 0.0
        self._cache_duration = 300.0
        self._all_cache: List[NewsItem] = []
        self._last_fetch_all = 0.0

    def _clean_html(self, text: str) -> str:
        if not text:
            return ""
        text = unescape(text)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _parse_date(self, entry) -> float:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                return time.mktime(entry.published_parsed)
            except Exception:
                pass
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                return time.mktime(entry.updated_parsed)
            except Exception:
                pass
        return time.time()

    def _get_date_str(self, entry) -> str:
        if hasattr(entry, "published") and entry.published:
            return entry.published[:25]
        if hasattr(entry, "updated") and entry.updated:
            return entry.updated[:25]
        return ""

    def _calc_sentiment(self, text: str) -> tuple:
        text_lower = text.lower()
        score = 0.0
        matched = []

        for word, weight in POSITIVE_WORDS.items():
            if word in text_lower:
                score += weight
                matched.append(word)

        for word, weight in NEGATIVE_WORDS.items():
            if word in text_lower:
                score += weight
                matched.append(word)

        if score > 3:
            label = "POSITIVO"
        elif score < -3:
            label = "NEGATIVO"
        else:
            label = "NEUTRO"

        normalized = max(-100, min(100, score * 10))
        return normalized, label, matched

    def _calc_relevance(self, title: str, summary: str) -> tuple:
        text = (title + " " + summary).lower()
        score = 0.0
        asset_rel = {"WIN": 0.0, "WDO": 0.0}
        matched_kw = []

        for kw in HIGH_RELEVANCE_KEYWORDS:
            if kw in text:
                score += 15
                matched_kw.append(kw)

        for asset, keywords in ASSET_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    asset_rel[asset] += 10
                    matched_kw.append(kw)

        combined_asset = (asset_rel.get("WIN", 0) + asset_rel.get("WDO", 0)) / 2
        total = min(100, score + combined_asset)

        if total > 60:
            label = "ALTA"
        elif total > 30:
            label = "MEDIA"
        else:
            label = "BAIXA"

        return total, label, asset_rel, list(set(matched_kw))

    def _fetch_feed(self, url: str, source_name: str, timeout: int = 10) -> List[dict]:
        results = []
        try:
            if HAS_REQUESTS:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                resp = requests.get(url, headers=headers, timeout=timeout)
                feed = feedparser.parse(resp.text)
            else:
                feed = feedparser.parse(url)

            for entry in feed.entries[:15]:
                title = self._clean_html(entry.get("title", ""))
                summary = self._clean_html(
                    entry.get("summary", "") or entry.get("description", "")
                )
                if not title:
                    continue

                results.append({
                    "title": title,
                    "summary": summary[:500],
                    "link": entry.get("link", ""),
                    "published": self._get_date_str(entry),
                    "published_ts": self._parse_date(entry),
                    "source": source_name,
                })
        except Exception as e:
            log.warning("Feed error %s: %s", source_name, e)

        return results

    def _fetch_all_feeds(self) -> List[NewsItem]:
        now = time.time()
        if self._all_cache and (now - self._last_fetch_all) < self._cache_duration:
            return self._all_cache

        all_entries = []
        for name, url in RSS_FEEDS.items():
            entries = self._fetch_feed(url, name)
            all_entries.extend(entries)

        seen_titles = set()
        unique_entries = []
        for e in all_entries:
            title_key = e["title"][:80].lower().strip()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_entries.append(e)

        news_items = []
        for e in unique_entries:
            full_text = e["title"] + " " + e["summary"]
            sentiment, sent_label, sent_kw = self._calc_sentiment(full_text)
            relevance, rel_label, asset_rel, rel_kw = self._calc_relevance(
                e["title"], e["summary"]
            )
            all_kw = list(set(sent_kw + rel_kw))

            item = NewsItem(
                title=e["title"],
                summary=e["summary"],
                link=e["link"],
                published=e["published"],
                published_ts=e["published_ts"],
                source=e["source"],
                sentiment=sentiment,
                sentiment_label=sent_label,
                relevance=relevance,
                asset_relevance=asset_rel,
                keywords_matched=all_kw,
            )
            news_items.append(item)

        news_items.sort(key=lambda x: x.published_ts, reverse=True)

        self._all_cache = news_items
        self._last_fetch_all = now
        return news_items

    def get_news(
        self,
        limit: int = 30,
        min_relevance: float = 0,
        asset: str = None,
        min_sentiment: float = None,
    ) -> List[dict]:
        items = self._fetch_all_feeds()

        filtered = []
        for item in items:
            if item.relevance < min_relevance:
                continue
            if asset:
                asset_upper = asset.upper()
                if asset_upper not in item.asset_relevance:
                    continue
                if item.asset_relevance[asset_upper] < 5:
                    continue
            filtered.append({
                "title": item.title,
                "summary": item.summary,
                "link": item.link,
                "published": item.published,
                "source": item.source,
                "sentiment": item.sentiment,
                "sentiment_label": item.sentiment_label,
                "relevance": item.relevance,
                "relevance_label": (
                    "ALTA" if item.relevance > 60
                    else "MEDIA" if item.relevance > 30
                    else "BAIXA"
                ),
                "asset_relevance": item.asset_relevance,
                "keywords": item.keywords_matched[:5],
            })

        return filtered[:limit]

    def get_sentiment_summary(self, asset: str = None) -> dict:
        items = self._fetch_all_feeds()

        if asset:
            items = [
                i for i in items
                if i.asset_relevance.get(asset.upper(), 0) > 0
            ]

        if not items:
            return {
                "score": 0,
                "label": "SEM DADOS",
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "total": 0,
                "top_positive": [],
                "top_negative": [],
                "latest": [],
            }

        positive = [i for i in items if i.sentiment > 0]
        negative = [i for i in items if i.sentiment < 0]
        neutral = [i for i in items if i.sentiment == 0]

        total_sentiment = sum(i.sentiment for i in items)
        avg = total_sentiment / len(items) if items else 0

        if avg > 15:
            label = "OTIMISTA"
        elif avg > 5:
            label = "LEVE POSITIVO"
        elif avg < -15:
            label = "PESSIMISTA"
        elif avg < -5:
            label = "LEVE NEGATIVO"
        else:
            label = "NEUTRO"

        top_pos = sorted(positive, key=lambda x: x.sentiment, reverse=True)[:3]
        top_neg = sorted(negative, key=lambda x: x.sentiment)[:3]
        latest = items[:5]

        return {
            "score": round(avg, 1),
            "label": label,
            "positive_count": len(positive),
            "negative_count": len(negative),
            "neutral_count": len(neutral),
            "total": len(items),
            "top_positive": [
                {"title": i.title[:100], "sentiment": i.sentiment, "source": i.source}
                for i in top_pos
            ],
            "top_negative": [
                {"title": i.title[:100], "sentiment": i.sentiment, "source": i.source}
                for i in top_neg
            ],
            "latest": [
                {"title": i.title[:100], "sentiment_label": i.sentiment_label, "source": i.source}
                for i in latest
            ],
        }

    def get_projection(self, asset: str, score: float, trend: str) -> dict:
        news_summary = self.get_sentiment_summary(asset)

        news_score = news_summary["score"]
        news_count = news_summary["total"]

        if news_score > 20:
            news_bias = "COMPRADOR"
            news_bias_pct = min(80, 50 + news_score)
        elif news_score > 5:
            news_bias = "LEVEMENTE COMPRADOR"
            news_bias_pct = 50 + news_score
        elif news_score < -20:
            news_bias = "VENDEDOR"
            news_bias_pct = max(20, 50 + news_score)
        elif news_score < -5:
            news_bias = "LEVEMENTE VENDEDOR"
            news_bias_pct = 50 + news_score
        else:
            news_bias = "NEUTRO"
            news_bias_pct = 50

        technical_pct = score
        combined_pct = (technical_pct * 0.6 + news_bias_pct * 0.4)

        if combined_pct > 65:
            overall = "FORTE COMPRA"
            overall_color = "verde"
        elif combined_pct > 55:
            overall = "COMPRA"
            overall_color = "verde"
        elif combined_pct < 35:
            overall = "FORTE VENDA"
            overall_color = "vermelho"
        elif combined_pct < 45:
            overall = "VENDA"
            overall_color = "vermelho"
        else:
            overall = "NEUTRO"
            overall_color = "cinza"

        factors = []
        factors.append({
            "name": "Analise Tecnica",
            "value": technical_pct,
            "weight": "60%",
            "direction": "COMPRA" if technical_pct > 55 else "VENDA" if technical_pct < 45 else "NEUTRO",
        })
        factors.append({
            "name": "Sentimento Noticias",
            "value": round(news_bias_pct, 1),
            "weight": "40%",
            "direction": news_bias,
        })

        if news_summary["top_positive"]:
            factors.append({
                "name": "Destaque Positivo",
                "value": 0,
                "weight": "",
                "direction": news_summary["top_positive"][0]["title"][:80],
            })
        if news_summary["top_negative"]:
            factors.append({
                "name": "Destaque Negativo",
                "value": 0,
                "weight": "",
                "direction": news_summary["top_negative"][0]["title"][:80],
            })

        return {
            "asset": asset,
            "technical_score": technical_pct,
            "news_sentiment": news_score,
            "news_bias": news_bias,
            "news_bias_pct": round(news_bias_pct, 1),
            "news_count": news_count,
            "combined_score": round(combined_pct, 1),
            "overall_signal": overall,
            "overall_color": overall_color,
            "factors": factors,
        }
