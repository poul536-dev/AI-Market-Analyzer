const API_BASE = "";
const REFRESH_MS = 3000;
const CIRCUMFERENCE = 2 * Math.PI * 26;

function $(id) { return document.getElementById(id); }

function getAuthToken() { return localStorage.getItem('token'); }

function authFetch(url, options) {
    options = options || {};
    options.headers = options.headers || {};
    var token = getAuthToken();
    if (token) options.headers['Authorization'] = 'Bearer ' + token;
    return fetch(url, options).then(function(res) {
        if (res.status === 401) {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = '/login';
            return Promise.reject(new Error('Unauthorized'));
        }
        return res;
    });
}

function logout() {
    fetch('/auth/logout', { method: 'POST' }).catch(function() {});
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
}

function formatPrice(val, decimals) {
    if (val == null) return "0";
    return Number(val).toLocaleString("pt-BR", {
        minimumFractionDigits: decimals || 0,
        maximumFractionDigits: decimals || 0,
    });
}

function colorForScore(score) {
    if (score >= 80) return "var(--green)";
    if (score >= 60) return "var(--green)";
    if (score >= 40) return "var(--yellow)";
    if (score >= 20) return "var(--red)";
    return "var(--red)";
}

function badgeClass(forca) {
    if (forca === "COMPRADORA") return "badge-buy";
    if (forca === "VEDORA") return "badge-sell";
    return "badge-neutral";
}

function badgeText(score, label) {
    return label || "NEUTRO";
}

function setScoreCircle(id, score) {
    const el = $(id);
    if (!el) return;
    const offset = CIRCUMFERENCE - (score / 100) * CIRCUMFERENCE;
    el.style.strokeDashoffset = offset;
    el.style.stroke = colorForScore(score);
}

function updateClock() {
    const now = new Date();
    $("clock").textContent = now.toLocaleTimeString("pt-BR");
}

function updateAsset(prefix, data, scoreData) {
    const decimals = prefix === "wdo" ? 2 : 0;
    const asset = prefix.toUpperCase();

    $(prefix + "-price").textContent = formatPrice(data.price, decimals);

    const varEl = $(prefix + "-variation");
    const varSign = data.variation >= 0 ? "+" : "";
    varEl.textContent = varSign + formatPrice(data.variation, decimals) +
        " (" + data.variation_pct.toFixed(2) + "%)";
    varEl.className = "price-variation " + (data.variation >= 0 ? "price-up" : "price-down");

    const badge = $(prefix + "-badge");
    badge.textContent = badgeText(scoreData.score, scoreData.score_label);
    badge.className = "card-badge " + badgeClass(scoreData.forca);

    $(prefix + "-score").textContent = scoreData.score;
    $(prefix + "-score").style.color = colorForScore(scoreData.score);
    setScoreCircle(prefix + "-score-circle", scoreData.score);
    $(prefix + "-score-label").textContent = scoreData.score_label;
    $(prefix + "-score-label").style.color = colorForScore(scoreData.score);

    $(prefix + "-force-text").textContent = scoreData.forca;
    $(prefix + "-force-bar").style.width = scoreData.score + "%";
    $(prefix + "-force-bar").style.background = colorForScore(scoreData.score);

    const indicators = [
        { key: "Tendencia", value: data.tendencia },
        { key: "VWAP", value: formatPrice(data.vwap, decimals) },
        { key: "VWAP Pos", value: data.vwap_position },
        { key: "EMA 9", value: data.ema_9 != null ? formatPrice(data.ema_9, decimals) : "-" },
        { key: "EMA 21", value: data.ema_21 != null ? formatPrice(data.ema_21, decimals) : "-" },
        { key: "SMA 50", value: data.sma_50 != null ? formatPrice(data.sma_50, decimals) : "-" },
        { key: "RSI", value: data.rsi.toFixed(1) },
        { key: "ADX", value: data.adx ? data.adx.adx.toFixed(0) + " (" + data.adx.trend_strength + ")" : "-" },
        { key: "Stoch K", value: data.stochastic ? data.stochastic.k.toFixed(0) : "-" },
        { key: "Stoch D", value: data.stochastic ? data.stochastic.d.toFixed(0) : "-" },
        { key: "Boll Pos", value: data.bollinger ? data.bollinger.position : "-" },
        { key: "ATR", value: data.atr ? data.atr.toFixed(0) : "-" },
        { key: "Momentum", value: data.momentum },
        { key: "Volume", value: data.volume_ratio.toFixed(2) + "x" },
        { key: "ROC", value: data.roc.toFixed(2) + "%" },
        { key: "Suporte", value: formatPrice(data.suporte_1, decimals) },
        { key: "Resistencia", value: formatPrice(data.resistencia_1, decimals) },
    ];

    const grid = $(prefix + "-indicators");
    grid.innerHTML = indicators.map(ind =>
        '<div class="indicator-item">' +
            '<span class="indicator-key">' + ind.key + '</span>' +
            '<span class="indicator-val">' + ind.value + '</span>' +
        '</div>'
    ).join("");
}

function updateWinWDO(winData, wdoData, crossData) {
    $("ww-win-forca").textContent = winData.forca;
    $("ww-win-score").textContent = winData.score + " / 100";
    $("ww-win-trend").textContent = winData.tendencia;
    $("ww-win-momentum").textContent = winData.momentum;

    $("ww-wdo-forca").textContent = wdoData.forca;
    $("ww-wdo-score").textContent = wdoData.score + " / 100";
    $("ww-wdo-trend").textContent = wdoData.tendencia;
    $("ww-wdo-momentum").textContent = wdoData.momentum;

    if (crossData) {
        $("ww-correlation").textContent = crossData.correlation + " (" + crossData.correlation_score + ")";
        $("ww-divergence").textContent = crossData.divergence;
        $("ww-spread").textContent = crossData.spread_pct + "% " + crossData.spread_direction;
        $("ww-wdo-pressure").textContent = crossData.wdo_pressure;
        $("ww-recommendation").textContent = crossData.recommendation;

        let confluence = "MISTO";
        if (crossData.correlation.includes("FORTE INV") || crossData.divergence.includes("FORTE")) {
            confluence = "DIVERGENTE";
        } else if (crossData.win_trend === crossData.wdo_trend && crossData.win_trend !== "LATERAL") {
            confluence = "CONVERGENTE";
        }

        const badge = $("winwdo-badge");
        badge.textContent = confluence;
        badge.className = "card-badge " +
            (confluence === "CONVERGENTE" ? "badge-buy" : confluence === "DIVERGENTE" ? "badge-sell" : "badge-neutral");
    }
}

function updateCenarios(asset, cenarios, decimals) {
    const container = $("cenarios-" + asset.toLowerCase());
    if (!container) return;

    const html = `
        <div class="scenario-item altista">
            <div class="scenario-label" style="color:var(--green)">CENARIO ALTISTA</div>
            <div class="scenario-cond">${cenarios.cenario_altista.condicao}</div>
            <div class="scenario-targets">
                <div class="scenario-target" style="color:var(--green)">Alvo 1: ${formatPrice(cenarios.cenario_altista.alvo_1, decimals)}</div>
                <div class="scenario-target" style="color:var(--green)">Alvo 2: ${formatPrice(cenarios.cenario_altista.alvo_2, decimals)}</div>
            </div>
            <div class="scenario-prob">Probabilidade: ${cenarios.cenario_altista.probabilidade}%</div>
        </div>
        <div class="scenario-item baixista">
            <div class="scenario-label" style="color:var(--red)">CENARIO BAIXISTA</div>
            <div class="scenario-cond">${cenarios.cenario_baixista.condicao}</div>
            <div class="scenario-targets">
                <div class="scenario-target" style="color:var(--red)">Alvo 1: ${formatPrice(cenarios.cenario_baixista.alvo_1, decimals)}</div>
                <div class="scenario-target" style="color:var(--red)">Alvo 2: ${formatPrice(cenarios.cenario_baixista.alvo_2, decimals)}</div>
            </div>
            <div class="scenario-prob">Probabilidade: ${cenarios.cenario_baixista.probabilidade}%</div>
        </div>
        <div class="scenario-item lateral">
            <div class="scenario-label" style="color:var(--yellow)">CENARIO LATERAL</div>
            <div class="scenario-cond">${cenarios.cenario_lateral.condicao}</div>
            <div class="scenario-prob">${cenarios.cenario_lateral.observacao}</div>
        </div>
    `;
    container.innerHTML = html;
}

function updateMapa(winData, wdoData) {
    const mapa = $("mapa-grid");
    const winDec = 0;
    const wdoDec = 2;

    const items = [
        { label: "Tendencia WIN", value: winData.tendencia },
        { label: "Forca WIN", value: winData.score + "/100" },
        { label: "VWAP WIN", value: winData.vwap_position },
        { label: "ADX WIN", value: winData.adx ? winData.adx.trend_strength : "-" },
        { label: "Stoch WIN", value: winData.stochastic ? winData.stochastic.signal : "-" },
        { label: "Boll WIN", value: winData.bollinger ? winData.bollinger.position : "-" },
        { label: "Momentum WIN", value: winData.momentum },
        { label: "Tendencia WDO", value: wdoData.tendencia },
        { label: "Forca WDO", value: wdoData.score + "/100" },
        { label: "VWAP WDO", value: wdoData.vwap_position },
        { label: "ADX WDO", value: wdoData.adx ? wdoData.adx.trend_strength : "-" },
        { label: "Stoch WDO", value: wdoData.stochastic ? wdoData.stochastic.signal : "-" },
        { label: "Boll WDO", value: wdoData.bollinger ? wdoData.bollinger.position : "-" },
        { label: "Momentum WDO", value: wdoData.momentum },
        { label: "Compra WIN acima", value: formatPrice(winData.resistencia_1, winDec) },
        { label: "Venda WIN abaixo", value: formatPrice(winData.suporte_1, winDec) },
        { label: "Compra WDO acima", value: formatPrice(wdoData.resistencia_1, wdoDec) },
        { label: "Venda WDO abaixo", value: formatPrice(wdoData.suporte_1, wdoDec) },
    ];

    mapa.innerHTML = items.map(item => {
        let color = "var(--text-primary)";
        if (item.label.includes("Tendencia")) {
            color = item.value === "ALTA" ? "var(--green)" : item.value === "BAIXA" ? "var(--red)" : "var(--yellow)";
        } else if (item.label.includes("ADX")) {
            color = item.value === "FORTE" || item.value === "MUITO FORTE" ? "var(--green)" :
                item.value === "FRACO" ? "var(--red)" : "var(--yellow)";
        }
        return '<div class="mapa-item">' +
            '<div class="mapa-item-label">' + item.label + '</div>' +
            '<div class="mapa-item-value" style="color:' + color + '">' + item.value + '</div>' +
        '</div>';
    }).join("");
}

function updateMultitimeframe(asset, data) {
    const container = $("mtf-" + asset.toLowerCase());
    const badge = $("mtf-" + asset.toLowerCase() + "-badge");
    if (!container) return;
    if (!badge) return;

    if (!data || !data.timeframes) {
        container.innerHTML = '<div class="no-data">Sem dados multitimeframe</div>';
        return;
    }

    badge.textContent = data.confluence;
    badge.className = "card-badge " +
        (data.confluence === "ALTA" ? "badge-buy" : data.confluence === "BAIXA" ? "badge-sell" : "badge-neutral");

    const tfs = ["1M", "5M", "15M", "30M", "1H"];
    container.innerHTML = tfs.map(tf => {
        const tfData = data.timeframes[tf];
        if (!tfData) return '<div class="mtf-item"><div class="mtf-tf">' + tf + '</div><div class="no-data">-</div></div>';

        const trendColor = tfData.trend === "ALTA" ? "var(--green)" :
            tfData.trend === "BAIXA" ? "var(--red)" : "var(--yellow)";
        const signalColor = tfData.signal === "COMPRA" ? "var(--green)" :
            tfData.signal === "VENDA" ? "var(--red)" : "var(--yellow)";
        const scoreColor = tfData.score >= 60 ? "var(--green)" :
            tfData.score <= 40 ? "var(--red)" : "var(--yellow)";

        return '<div class="mtf-item">' +
            '<div class="mtf-tf">' + tf + '</div>' +
            '<div class="mtf-trend" style="color:' + trendColor + '">' + tfData.trend + '</div>' +
            '<div class="mtf-signal" style="background:' + signalColor + '20;color:' + signalColor + '">' + tfData.signal + '</div>' +
            '<div class="mtf-score" style="color:' + scoreColor + '">' + tfData.score + '</div>' +
            '<div class="mtf-detail">RSI:' + tfData.rsi.toFixed(0) + ' MACD:' + (tfData.macd_hist > 0 ? '+' : '') + tfData.macd_hist.toFixed(1) + ' ADX:' + tfData.adx.toFixed(0) + '</div>' +
        '</div>';
    }).join("");
}

function updateDivergences(asset, data) {
    const container = $("div-" + asset.toLowerCase());
    if (!container) return;

    if (!data || !data.divergences || data.divergences.length === 0) {
        container.innerHTML = '<div class="no-data">Nenhuma divergencia detectada</div>';
        return;
    }

    container.innerHTML = data.divergences.map(d => {
        const typeClass = d.direction === "BAIXA" ? "bearish" : "bullish";
        const typeColor = d.direction === "BAIXA" ? "var(--red)" : "var(--green)";

        return '<div class="divergence-item ' + typeClass + '">' +
            '<div class="divergence-type" style="color:' + typeColor + '">' + d.type + ' (' + d.direction + ')</div>' +
            '<div class="divergence-detail">' + d.detail + '</div>' +
            '<div class="divergence-strength" style="color:' + (d.strength === "FORTE" ? "var(--green)" : "var(--yellow)") + '">Forca: ' + d.strength + '</div>' +
        '</div>';
    }).join("");
}

function updateAI(winData, wdoData) {
    const parts = [];

    parts.push("<strong>LEITURA DO MERCADO</strong><br><br>");

    const winForce = winData.forca === "COMPRADORA" ? "forca compradora" :
        winData.forca === "VEDORA" ? "forca vendedora" : "momento neutro";
    parts.push("O WIN apresenta <strong>" + winForce + "</strong> (score " + winData.score + "/100).");

    if (winData.vwap_position === "ACIMA") {
        parts.push("O preco esta <strong>acima da VWAP</strong> (" + formatPrice(winData.vwap, 0) + ").");
    } else if (winData.vwap_position === "ABAIXO") {
        parts.push("O preco esta <strong>abaixo da VWAP</strong> (" + formatPrice(winData.vwap, 0) + ").");
    }

    if (winData.tendencia === "ALTA") {
        parts.push("A tendencia e de <strong>alta</strong>.");
    } else if (winData.tendencia === "BAIXA") {
        parts.push("A tendencia e de <strong>baixa</strong>.");
    } else {
        parts.push("O mercado esta em <strong>lateralizacao</strong>.");
    }

    parts.push("<br><br>");

    const wdoForce = wdoData.forca === "COMPRADORA" ? "forca compradora" :
        wdoData.forca === "VEDORA" ? "forca vendedora" : "momento neutro";
    parts.push("O WDO apresenta <strong>" + wdoForce + "</strong> (score " + wdoData.score + "/100).");

    if (wdoData.tendencia !== winData.tendencia) {
        parts.push("Existe <strong>divergencia</strong> entre WIN e WDO, o que reduz a confianca no cenario atual.");
    } else {
        parts.push("WIN e WDO apresentam tendencias <strong>alinhadas</strong>.");
    }

    parts.push("<br><br>");
    parts.push("A principal resistencia do WIN esta em <strong>" + formatPrice(winData.resistencia_1, 0) + "</strong>.");
    parts.push("O principal suporte do WIN esta em <strong>" + formatPrice(winData.suporte_1, 0) + "</strong>.");
    parts.push("<br><br>");

    if (winData.probability_up >= 60) {
        parts.push("O cenario com maior probabilidade e o <strong>comprador</strong> (" + winData.probability_up + "%).");
    } else if (winData.probability_down >= 60) {
        parts.push("O cenario com maior probabilidade e o <strong>vendedor</strong> (" + winData.probability_down + "%).");
    } else {
        parts.push("Os cenarios estao <strong>equilibrados</strong>. Cuidado com operacoes no meio da faixa.");
    }

    $("ai-text").innerHTML = parts.join("");
}

function updateAlerts(alerts) {
    const list = $("alerts-list");
    const count = $("alerts-count");

    if (!alerts || alerts.length === 0) {
        list.innerHTML = '<div class="alert-item baixa"><div class="alert-content"><span class="alert-mensagem">Nenhum alerta no momento.</span></div></div>';
        count.textContent = "0";
        return;
    }

    count.textContent = alerts.length;
    const icons = { "CRITICA": "!!", "ALTA": "!", "MEDIA": "!", "BAIXA": "i" };

    list.innerHTML = alerts.map(a => {
        const sevClass = a.severidade ? a.severidade.toLowerCase() : "baixa";
        return '<div class="alert-item ' + sevClass + '">' +
            '<div class="alert-icon">' + (icons[a.severidade] || "i") + '</div>' +
            '<div class="alert-content">' +
                '<span class="alert-tipo">' + a.tipo + ' - ' + a.asset + '</span>' +
                '<span class="alert-mensagem">' + a.mensagem + '</span>' +
                '<span class="alert-time">' + a.timestamp + '</span>' +
            '</div>' +
        '</div>';
    }).join("");
}

function updateNewsSentiment(data) {
    if (!data) return;

    const score = data.score || 0;
    const scoreEl = $("news-sent-score");
    scoreEl.textContent = score.toFixed(1);
    scoreEl.style.color = score > 10 ? "var(--green)" : score < -10 ? "var(--red)" : "var(--yellow)";

    const labelEl = $("news-sent-label");
    labelEl.textContent = data.label || "Neutro";
    labelEl.style.color = score > 10 ? "var(--green)" : score < -10 ? "var(--red)" : "var(--yellow)";

    const badge = $("news-sent-badge");
    badge.textContent = data.label || "NEUTRO";
    badge.className = "card-badge " +
        (score > 10 ? "badge-buy" : score < -10 ? "badge-sell" : "badge-neutral");

    const countsEl = $("news-sent-counts");
    countsEl.innerHTML =
        '<span class="news-count-positive">' + data.positive_count + ' positivas</span>' +
        '<span class="news-count-neutral">' + data.neutral_count + ' neutras</span>' +
        '<span class="news-count-negative">' + data.negative_count + ' negativas</span>' +
        '<span class="news-count-total">Total: ' + data.total + '</span>';

    const posEl = $("news-top-positive");
    if (data.top_positive && data.top_positive.length > 0) {
        posEl.innerHTML = '<div class="news-section-title" style="color:var(--green)">POSITIVAS</div>' +
            data.top_positive.map(n =>
                '<div class="news-top-item positive">' + n.title + ' <span class="news-src">(' + n.source + ')</span></div>'
            ).join("");
    } else {
        posEl.innerHTML = "";
    }

    const negEl = $("news-top-negative");
    if (data.top_negative && data.top_negative.length > 0) {
        negEl.innerHTML = '<div class="news-section-title" style="color:var(--red)">NEGATIVAS</div>' +
            data.top_negative.map(n =>
                '<div class="news-top-item negative">' + n.title + ' <span class="news-src">(' + n.source + ')</span></div>'
            ).join("");
    } else {
        negEl.innerHTML = "";
    }
}

function updateProjection(asset, data) {
    if (!data) return;
    const prefix = "proj-" + asset.toLowerCase();

    const combinedEl = $(prefix + "-combined");
    combinedEl.textContent = data.combined_score.toFixed(1) + "%";
    combinedEl.style.color = data.overall_color === "verde" ? "var(--green)" :
        data.overall_color === "vermelho" ? "var(--red)" : "var(--yellow)";

    const signalEl = $(prefix + "-signal");
    signalEl.textContent = data.overall_signal;
    signalEl.style.color = data.overall_color === "verde" ? "var(--green)" :
        data.overall_color === "vermelho" ? "var(--red)" : "var(--yellow)";

    const badge = $(prefix + "-badge");
    badge.textContent = data.overall_signal;
    badge.className = "card-badge " +
        (data.overall_color === "verde" ? "badge-buy" : data.overall_color === "vermelho" ? "badge-sell" : "badge-neutral");

    const factorsEl = $(prefix + "-factors");
    if (data.factors && data.factors.length > 0) {
        factorsEl.innerHTML = data.factors.map(f => {
            if (f.name.includes("Destaque")) {
                return '<div class="proj-factor highlight">' +
                    '<span class="proj-factor-name">' + f.name + '</span>' +
                    '<span class="proj-factor-value">' + f.direction + '</span>' +
                '</div>';
            }
            return '<div class="proj-factor">' +
                '<span class="proj-factor-name">' + f.name + ' (' + f.weight + ')</span>' +
                '<span class="proj-factor-value" style="color:' +
                    (f.direction.includes("COMPRA") ? "var(--green)" : f.direction.includes("VENDA") ? "var(--red)" : "var(--yellow)") +
                '">' + f.direction + ' ' + f.value + '%</span>' +
            '</div>';
        }).join("");
    }
}

function updateNewsFeed(news) {
    const feed = $("news-feed");
    const countBadge = $("news-count-badge");

    if (!news || news.length === 0) {
        feed.innerHTML = '<div class="no-data">Nenhuma noticia encontrada</div>';
        countBadge.textContent = "0";
        return;
    }

    countBadge.textContent = news.length;

    feed.innerHTML = news.map(n => {
        const sentClass = n.sentiment_label === "POSITIVO" ? "positive" :
            n.sentiment_label === "NEGATIVO" ? "negative" : "neutral";
        const sentIcon = n.sentiment_label === "POSITIVO" ? "+" :
            n.sentiment_label === "NEGATIVO" ? "-" : "~";
        const relClass = n.relevance > 60 ? "high" : n.relevance > 30 ? "medium" : "low";

        return '<a href="' + n.link + '" target="_blank" class="news-item ' + sentClass + '">' +
            '<div class="news-sent-icon">' + sentIcon + '</div>' +
            '<div class="news-content">' +
                '<div class="news-title">' + n.title + '</div>' +
                '<div class="news-meta">' +
                    '<span class="news-source">' + n.source + '</span>' +
                    '<span class="news-relevance ' + relClass + '">Rel:' + n.relevance.toFixed(0) + '</span>' +
                    '<span class="news-sent-badge ' + sentClass + '">' + n.sentiment_label + '</span>' +
                '</div>' +
            '</div>' +
        '</a>';
    }).join("");
}

function updateAccuracy(data) {
    const mainEl = $("accuracy-main");
    const compEl = $("accuracy-components");
    const badge = $("accuracy-badge");

    if (!data || data.total_predictions === 0) {
        mainEl.innerHTML = '<div class="accuracy-item"><div class="accuracy-label">Total Previsoes</div><div class="accuracy-value">0</div></div><div class="accuracy-item"><div class="accuracy-label">Aguardando dados...</div><div class="accuracy-value">-</div></div>';
        compEl.innerHTML = "";
        badge.textContent = "SEM DADOS";
        return;
    }

    const wr = data.win_rate;
    badge.textContent = wr.toFixed(0) + "% ACERTO";
    badge.className = "card-badge " + (wr >= 55 ? "badge-buy" : wr >= 45 ? "badge-neutral" : "badge-sell");

    const items = [
        { label: "Win Rate", value: wr.toFixed(1) + "%", color: wr >= 55 ? "var(--green)" : wr >= 45 ? "var(--yellow)" : "var(--red)" },
        { label: "Total Previsoes", value: data.total_predictions, color: "var(--text-primary)" },
        { label: "Wins", value: data.wins, color: "var(--green)" },
        { label: "Losses", value: data.losses, color: "var(--red)" },
        { label: "Win Rate CIMA", value: data.win_rate_up.toFixed(1) + "%", color: data.win_rate_up >= 55 ? "var(--green)" : "var(--red)" },
        { label: "Win Rate BAIXO", value: data.win_rate_down.toFixed(1) + "%", color: data.win_rate_down >= 55 ? "var(--green)" : "var(--red)" },
        { label: "Profit Factor", value: data.profit_factor, color: data.profit_factor >= 1.5 ? "var(--green)" : "var(--red)" },
        { label: "Media Ticks Ganho", value: data.avg_profit_ticks, color: "var(--green)" },
        { label: "Media Ticks Perda", value: data.avg_loss_ticks, color: "var(--red)" },
    ];

    mainEl.innerHTML = items.map(i =>
        '<div class="accuracy-item">' +
            '<div class="accuracy-label">' + i.label + '</div>' +
            '<div class="accuracy-value" style="color:' + i.color + '">' + i.value + '</div>' +
        '</div>'
    ).join("");

    const comp = data.component_accuracy || {};
    const compNames = {
        "vwap": "VWAP", "trend": "Tendencia", "moving_averages": "Medias",
        "momentum": "Momentum", "volume": "Volume", "breakout": "Breakout",
        "structure": "Estrutura", "relative_strength": "Forca Rel",
        "adx": "ADX", "stochastic": "Estocastico", "bollinger": "Bollinger"
    };

    compEl.innerHTML = '<div class="acc-comp-title">ACURACIA POR COMPONENTE</div>' +
        '<div class="acc-comp-grid">' +
        Object.entries(comp).map(([key, val]) => {
            const acc = val.accuracy;
            const color = acc >= 60 ? "var(--green)" : acc >= 45 ? "var(--yellow)" : "var(--red)";
            return '<div class="acc-comp-item">' +
                '<span class="acc-comp-name">' + (compNames[key] || key) + '</span>' +
                '<div class="acc-comp-bar"><div class="acc-comp-fill" style="width:' + acc + '%;background:' + color + '"></div></div>' +
                '<span class="acc-comp-val" style="color:' + color + '">' + acc.toFixed(0) + '%</span>' +
            '</div>';
        }).join("") +
        '</div>';
}

function updateWeights(data) {
    const grid = $("weights-grid");
    const badge = $("weights-badge");

    if (!data) {
        grid.innerHTML = '<div class="no-data">Sem dados de pesos</div>';
        return;
    }

    const current = data.current || {};
    const defaults = data.defaults || {};
    badge.textContent = data.history_count + " ajustes";

    const names = {
        "vwap": "VWAP", "trend": "Tendencia", "moving_averages": "Medias",
        "momentum": "Momentum", "volume": "Volume", "breakout": "Breakout",
        "structure": "Estrutura", "relative_strength": "Forca Rel",
        "adx": "ADX", "stochastic": "Estocastico", "bollinger": "Bollinger"
    };

    grid.innerHTML = Object.entries(current).map(([key, val]) => {
        const def = defaults[key] || val;
        const diff = val - def;
        const diffStr = diff > 0 ? "+" + (diff * 100).toFixed(1) + "%" :
            diff < 0 ? (diff * 100).toFixed(1) + "%" : "=";
        const diffColor = diff > 0.005 ? "var(--green)" : diff < -0.005 ? "var(--red)" : "var(--text-muted)";
        const barW = (val / 0.30) * 100;

        return '<div class="weight-item">' +
            '<span class="weight-name">' + (names[key] || key) + '</span>' +
            '<div class="weight-bar"><div class="weight-fill" style="width:' + barW + '%"></div></div>' +
            '<span class="weight-val">' + (val * 100).toFixed(1) + '%</span>' +
            '<span class="weight-diff" style="color:' + diffColor + '">' + diffStr + '</span>' +
        '</div>';
    }).join("");
}

function updateOutcomeHistory(data) {
    const list = $("outcome-history");
    const countBadge = $("history-count");

    if (!data || !data.history || data.history.length === 0) {
        list.innerHTML = '<div class="no-data">Nenhuma previsao registrada</div>';
        countBadge.textContent = "0";
        return;
    }

    countBadge.textContent = data.history.length;

    list.innerHTML = data.history.map(o => {
        const cls = o.outcome === "WIN" ? "win" : o.outcome === "LOSS" ? "loss" : "neutral";
        const icon = o.outcome === "WIN" ? "V" : o.outcome === "LOSS" ? "X" : "-";
        const color = o.outcome === "WIN" ? "var(--green)" : o.outcome === "LOSS" ? "var(--red)" : "var(--yellow)";

        return '<div class="outcome-item ' + cls + '">' +
            '<div class="outcome-icon" style="color:' + color + '">' + icon + '</div>' +
            '<div class="outcome-info">' +
                '<span class="outcome-asset">' + o.asset + ' ' + o.direction + '</span>' +
                '<span class="outcome-detail">Score: ' + o.score + ' | ' +
                    o.price_prediction + ' -> ' + o.price_outcome +
                    ' (' + (o.ticks > 0 ? '+' : '') + o.ticks + ' ticks)</span>' +
            '</div>' +
        '</div>';
    }).join("");
}

function updateSentiment(data) {
    if (!data) return;

    const score = data.overall_score || 50;
    const scoreEl = $("sentiment-score");
    scoreEl.textContent = score.toFixed(0);
    scoreEl.style.color = score >= 60 ? "var(--green)" : score <= 40 ? "var(--red)" : "var(--yellow)";

    const labelEl = $("sentiment-label");
    labelEl.textContent = data.label || "Neutro";
    labelEl.style.color = score >= 60 ? "var(--green)" : score <= 40 ? "var(--red)" : "var(--yellow)";

    $("sentiment-interpretation").textContent = data.interpretation || "";

    const badge = $("sentiment-badge");
    badge.textContent = data.label || "NEUTRO";
    badge.className = "card-badge " +
        (score >= 60 ? "badge-buy" : score <= 40 ? "badge-sell" : "badge-neutral");

    const factorsEl = $("sentiment-factors");
    if (data.factors && data.factors.length > 0) {
        factorsEl.innerHTML = data.factors.map(f => {
            const cls = f.impact.includes("POSITIVO") ? "positive" :
                f.impact.includes("NEGATIVO") ? "negative" : "neutral";
            return '<div class="sentiment-factor ' + cls + '">' +
                '<strong>' + f.factor + '</strong><br>' + f.detail +
            '</div>';
        }).join("");
    }
}

function updateStrategies(data) {
    const list = $("strategy-list");
    if (!data || !data.results) {
        list.innerHTML = '<div class="no-data">Sem estrategias</div>';
        return;
    }

    list.innerHTML = data.results.map(s => {
        const isActive = s.signal !== "NEUTRO";
        const cls = isActive ? "active" : "inactive";
        const signalColor = s.signal === "COMPRA" ? "var(--green)" :
            s.signal === "VENDA" ? "var(--red)" : "var(--yellow)";

        return '<div class="strategy-item ' + cls + '">' +
            '<div class="strategy-name">' + s.strategy + '</div>' +
            '<div class="strategy-signal" style="color:' + signalColor + '">' + s.signal + ' (' + s.confidence.toFixed(0) + '%)</div>' +
            '<div class="strategy-detail">Entry: ' + formatPrice(s.entry_price, s.asset === "WDO" ? 2 : 0) +
            ' | TP: ' + formatPrice(s.tp_price, s.asset === "WDO" ? 2 : 0) +
            ' | SL: ' + formatPrice(s.sl_price, s.asset === "WDO" ? 2 : 0) +
            ' | R:R ' + s.risk_reward + '</div>' +
            '<div class="strategy-detail">' + s.reason + '</div>' +
        '</div>';
    }).join("");
}

function updateRisk(data) {
    const grid = $("risk-grid");
    if (!data) {
        grid.innerHTML = '<div class="no-data">Sem dados de risco</div>';
        return;
    }

    const items = [];
    for (const asset of ["WIN", "WDO"]) {
        const r = data[asset];
        if (!r) continue;
        const a = r.assessment;
        const dec = asset === "WDO" ? 2 : 0;

        items.push(
            { label: asset + " Contratos", value: a.contracts, color: a.can_trade ? "var(--green)" : "var(--red)" },
            { label: asset + " Risco/Trade", value: "R$ " + formatPrice(a.risk_amount, 2), color: "var(--text-primary)" },
            { label: asset + " R:R", value: a.risk_reward_ratio + ":1", color: a.risk_reward_ratio >= 1.5 ? "var(--green)" : "var(--red)" },
            { label: asset + " Stop", value: a.stop_type, color: "var(--yellow)" },
            { label: asset + " Pode Operar", value: a.can_trade ? "SIM" : "NAO", color: a.can_trade ? "var(--green)" : "var(--red)" },
            { label: asset + " Sugestao", value: a.suggestion.substring(0, 40), color: "var(--text-secondary)" },
        );
    }

    grid.innerHTML = items.map(i =>
        '<div class="risk-item">' +
            '<div class="risk-label">' + i.label + '</div>' +
            '<div class="risk-value" style="color:' + i.color + '">' + i.value + '</div>' +
        '</div>'
    ).join("");
}

function updatePerformance(data) {
    const grid = $("perf-grid");
    if (!data || data.total_trades === 0) {
        grid.innerHTML = '<div class="no-data">Nenhuma operacao registrada</div>';
        return;
    }

    const items = [
        { label: "Total Operacoes", value: data.total_trades, color: "var(--text-primary)" },
        { label: "Win Rate", value: data.win_rate + "%", color: data.win_rate >= 50 ? "var(--green)" : "var(--red)" },
        { label: "PnL Total", value: "R$ " + formatPrice(data.total_pnl, 2), color: data.total_pnl >= 0 ? "var(--green)" : "var(--red)" },
        { label: "Profit Factor", value: data.profit_factor, color: data.profit_factor >= 1.5 ? "var(--green)" : "var(--red)" },
        { label: "Sharpe Ratio", value: data.sharpe_ratio, color: data.sharpe_ratio >= 1 ? "var(--green)" : "var(--yellow)" },
        { label: "Max Drawdown", value: data.max_drawdown_pct + "%", color: "var(--red)" },
        { label: "Melhor Trade", value: "R$ " + formatPrice(data.best_trade, 2), color: "var(--green)" },
        { label: "Pior Trade", value: "R$ " + formatPrice(data.worst_trade, 2), color: "var(--red)" },
        { label: "Retorno Total", value: data.total_return_pct + "%", color: data.total_return_pct >= 0 ? "var(--green)" : "var(--red)" },
        { label: "Expectancy", value: "R$ " + formatPrice(data.expectancy * 100, 2), color: data.expectancy >= 0 ? "var(--green)" : "var(--red)" },
    ];

    grid.innerHTML = items.map(i =>
        '<div class="perf-item">' +
            '<div class="perf-label">' + i.label + '</div>' +
            '<div class="perf-value" style="color:' + i.color + '">' + i.value + '</div>' +
        '</div>'
    ).join("");
}

function setConnected(ok) {
    const dot = $("conn-dot");
    const txt = $("conn-text");
    if (ok) {
        dot.className = "connection-dot dot-connected";
        txt.textContent = "ONLINE";
    } else {
        dot.className = "connection-dot dot-disconnected";
        txt.textContent = "OFFLINE";
    }
}

function updateBattleBar(win, wdo) {
    if (!win && !wdo) return;
    var winScore = win ? win.score : 50;
    var wdoScore = wdo ? wdo.score : 50;
    updateBattleArenas(winScore, wdoScore);
}

function setStatus(open) {
    const el = $("market-status");
    if (open) {
        el.textContent = "ABERTO";
        el.className = "status-badge status-open";
    } else {
        el.textContent = "FECHADO";
        el.className = "status-badge status-closed";
    }
}

function updateMT5Status(data) {
    const el = $("mt5-status");
    if (!data) {
        el.textContent = "N/A";
        el.style.color = "var(--text-muted)";
        return;
    }

    if (data.connected) {
        el.textContent = "CONECTADO";
        el.style.color = "var(--green)";
    } else {
        el.textContent = "DESCONECTADO";
        el.style.color = "var(--red)";
    }
}

async function fetchData() {
    try {
        const [analiseRes, cenariosRes, alertasRes, crossRes, mtfWinRes, mtfWdoRes, divWinRes, divWdoRes, sentRes, estratRes, riscoRes, perfRes, mt5Res, newsRes, newsResumRes, projWinRes, projWdoRes, accuracyRes, weightsRes, historyRes] = await Promise.all([
            authFetch(API_BASE + "/analise"),
            authFetch(API_BASE + "/cenarios"),
            authFetch(API_BASE + "/alertas"),
            authFetch(API_BASE + "/cross"),
            authFetch(API_BASE + "/multitimeframe/WIN"),
            authFetch(API_BASE + "/multitimeframe/WDO"),
            authFetch(API_BASE + "/divergencias/WIN"),
            authFetch(API_BASE + "/divergencias/WDO"),
            authFetch(API_BASE + "/sentimento"),
            authFetch(API_BASE + "/estrategias/avaliar-todas", { method: 'POST' }),
            authFetch(API_BASE + "/risco"),
            authFetch(API_BASE + "/performance"),
            authFetch(API_BASE + "/mt5/status"),
            authFetch(API_BASE + "/noticias?limit=15"),
            authFetch(API_BASE + "/noticias/resumo"),
            authFetch(API_BASE + "/noticias/projecao/WIN"),
            authFetch(API_BASE + "/noticias/projecao/WDO"),
            authFetch(API_BASE + "/outcome/acuracia"),
            authFetch(API_BASE + "/outcome/pesos"),
            authFetch(API_BASE + "/outcome/historico"),
        ]);

        const analise = await analiseRes.json();
        const cenarios = await cenariosRes.json();
        const alertasData = await alertasRes.json();
        const crossData = await crossRes.json();
        const mtfWin = await mtfWinRes.json();
        const mtfWdo = await mtfWdoRes.json();
        const divWin = await divWinRes.json();
        const divWdo = await divWdoRes.json();
        const sentData = await sentRes.json();
        const estratData = await estratRes.json();
        const riscoData = await riscoRes.json();
        const perfData = await perfRes.json();
        const mt5Data = await mt5Res.json();
        const newsData = await newsRes.json();
        const newsResumo = await newsResumRes.json();
        const projWin = await projWinRes.json();
        const projWdo = await projWdoRes.json();
        const accuracyData = await accuracyRes.json();
        const weightsData = await weightsRes.json();
        const historyData = await historyRes.json();

        setConnected(true);

        const dataSource = analise.WIN ? (analise.WIN.source || "unknown") : "unknown";
        const sourceEl = $("data-source");
        if (dataSource === "mt5_realtime") {
            sourceEl.textContent = "MT5 TEMPO REAL";
            sourceEl.style.color = "var(--green)";
        } else if (dataSource === "brapi_dev") {
            sourceEl.textContent = "BRAPI (EOD)";
            sourceEl.style.color = "var(--yellow)";
        } else if (dataSource === "yahoo") {
            sourceEl.textContent = "YAHOO FINANCE";
            sourceEl.style.color = "var(--yellow)";
        } else {
            sourceEl.textContent = dataSource.toUpperCase();
            sourceEl.style.color = "var(--text-secondary)";
        }

        updateMT5Status(mt5Data);

        const win = analise.WIN;
        const wdo = analise.WDO;

        if (win) {
            updateAsset("win", win, win);
        }
        if (wdo) {
            updateAsset("wdo", wdo, wdo);
        }
        if (win && wdo) {
            updateWinWDO(win, wdo, crossData);
            updateMapa(win, wdo);
            updateAI(win, wdo);
            updateBattleBar(win, wdo);
        }
        if (mtfWin) {
            updateMultitimeframe("WIN", mtfWin);
        }
        if (mtfWdo) {
            updateMultitimeframe("WDO", mtfWdo);
        }
        if (divWin) {
            updateDivergences("WIN", divWin);
        }
        if (divWdo) {
            updateDivergences("WDO", divWdo);
        }
        if (cenarios.WIN) {
            updateCenarios("WIN", cenarios.WIN, 0);
        }
        if (cenarios.WDO) {
            updateCenarios("WDO", cenarios.WDO, 2);
        }

        updateSentiment(sentData);
        updateStrategies(estratData);
        updateRisk(riscoData);
        updatePerformance(perfData);
        updateAlerts(alertasData.alerts);
        updateNewsSentiment(newsResumo);
        updateProjection("WIN", projWin);
        updateProjection("WDO", projWdo);
        updateNewsFeed(newsData.news);
        updateAccuracy(accuracyData);
        updateWeights(weightsData);
        updateOutcomeHistory(historyData);

        $("last-update").textContent = new Date().toLocaleTimeString("pt-BR");
    } catch (err) {
        setConnected(false);
        console.error("Erro ao buscar dados:", err);
    }
}

updateClock();
setInterval(updateClock, 1000);

if (typeof initBattleArenas === 'function') initBattleArenas();

fetch('/auth/me').then(function(r) {
    if (r.ok) return r.json();
    throw new Error('Not authenticated');
}).then(function(data) {
    if (data && data.username) {
        var userEl = $('user-info');
        if (userEl) userEl.textContent = data.username.toUpperCase();
        fetchData();
        setInterval(fetchData, REFRESH_MS);
    }
}).catch(function() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
});
