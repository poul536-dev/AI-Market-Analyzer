class BattleArena {
constructor(config) {
this.id = config.id;
this.container = config.container;
this.targetBuy = 50;
this.targetSell = 50;
this.currentBuy = 50;
this.currentSell = 50;
this.particles = [];
this.candles = [];
this.running = true;
this.lastSpawn = 0;
this.el = {};
this.pCtx = null;
this.cCtx = null;
this.pCanvas = null;
this.cCanvas = null;
this.W = 0;
this.H = 0;
this.init();
}
init() {
var p = this.id;
this.pCanvas = document.getElementById('particles-' + p);
this.cCanvas = document.getElementById('candles-' + p);
if (this.pCanvas) {
this.pCtx = this.pCanvas.getContext('2d');
this.resizeCanvas(this.pCanvas);
}
if (this.cCanvas) {
this.cCtx = this.cCanvas.getContext('2d');
this.resizeCanvas(this.cCanvas);
}
var ids = [
'bull-side', 'bear-side', 'bull-power', 'bear-power',
'pct-bull', 'pct-bear', 'bar-fill-buy', 'bar-fill-sell',
'battle-marker', 'battle-signal', 'center-indicator',
'indicator-icon', 'indicator-text', 'market-state',
'differential', 'intensity', 'scene'
];
for (var i = 0; i < ids.length; i++) {
this.el[ids[i]] = document.getElementById(p + '-' + ids[i]);
}
this.generateCandles();
var self = this;
window.addEventListener('resize', function() {
self.resizeCanvas(self.pCanvas);
self.resizeCanvas(self.cCanvas);
});
requestAnimationFrame(function(t) { self.animate(t); });
}
resizeCanvas(c) {
if (!c) return;
var rect = c.parentElement.getBoundingClientRect();
c.width = rect.width || 800;
c.height = rect.height || 300;
if (c === this.pCanvas) {
this.W = c.width;
this.H = c.height;
}
}
update(buyPower, sellPower) {
this.targetBuy = Math.max(0, Math.min(100, buyPower));
this.targetSell = Math.max(0, Math.min(100, sellPower));
}
lerp(a, b, t) { return a + (b - a) * t; }
generateCandles() {
this.candles = [];
for (var i = 0; i < 40; i++) {
this.candles.push({
x: Math.random(),
open: 30 + Math.random() * 140,
close: 30 + Math.random() * 140,
high: 0, low: 0,
w: 4 + Math.random() * 4,
speed: 0.0002 + Math.random() * 0.0005,
offset: Math.random() * 1000
});
}
}
spawnParticle(side) {
var isBull = side === 'bull';
var baseX = isBull ? this.W * 0.15 : this.W * 0.85;
var baseY = this.H * 0.55;
var power = isBull ? this.currentBuy : this.currentSell;
var intensity = power / 100;
var spread = 50 + 30 * (1 - intensity);
return {
x: baseX + (Math.random() - 0.5) * spread,
y: baseY + (Math.random() - 0.5) * 40,
vx: (Math.random() - 0.5) * 0.8,
vy: -(0.5 + Math.random() * 1.5) * (0.5 + intensity * 0.8),
life: 1,
decay: 0.008 + Math.random() * 0.012,
size: 1.5 + Math.random() * 3 * intensity,
color: isBull ? [34, 197, 94] : [239, 68, 68],
glow: isBull ? [34, 197, 94] : [239, 68, 68]
};
}
animate(time) {
if (!this.running) return;
var self = this;
var dt = Math.min((time - (this._last || time)) / 16, 3);
this._last = time;
var speed = 0.04 * dt;
this.currentBuy = this.lerp(this.currentBuy, this.targetBuy, speed);
this.currentSell = this.lerp(this.currentSell, this.targetSell, speed);
var total = this.currentBuy + this.currentSell;
if (total < 1) total = 1;
var buyPct = Math.round(this.currentBuy / total * 100);
var sellPct = 100 - buyPct;
var diff = Math.abs(this.currentBuy - this.currentSell);
var dominant = this.currentBuy > this.currentSell ? 'bull' : (this.currentSell > this.currentBuy ? 'bear' : 'equal');
this.updateBar(buyPct, sellPct, dominant, diff);
this.updateAnimals(dominant, diff);
this.updateIndicator(dominant, buyPct, sellPct);
this.updateScene(dominant, diff);
if (time - this.lastSpawn > (30 - diff * 0.2)) {
this.lastSpawn = time;
if (dominant === 'bull' || dominant === 'equal') {
this.particles.push(this.spawnParticle('bull'));
if (dominant === 'bull' && diff > 20) this.particles.push(this.spawnParticle('bull'));
}
if (dominant === 'bear' || dominant === 'equal') {
this.particles.push(this.spawnParticle('bear'));
if (dominant === 'bear' && diff > 20) this.particles.push(this.spawnParticle('bear'));
}
}
this.updateParticles(dt);
this.renderParticles();
this.renderCandles(time, dominant);
requestAnimationFrame(function(t) { self.animate(t); });
}
updateBar(buyPct, sellPct, dominant, diff) {
var fillBuy = this.el['bar-fill-buy'];
var fillSell = this.el['bar-fill-sell'];
var marker = this.el['battle-marker'];
var sig = this.el['battle-signal'];
var pctBull = this.el['pct-bull'];
var pctBear = this.el['pct-bear'];
var bullPower = this.el['bull-power'];
var bearPower = this.el['bear-power'];
if (fillBuy) { fillBuy.style.width = buyPct + '%'; }
if (fillSell) { fillSell.style.width = sellPct + '%'; }
if (marker) { marker.style.left = buyPct + '%'; }
if (pctBull) pctBull.textContent = buyPct + '%';
if (pctBear) pctBear.textContent = sellPct + '%';
if (bullPower) bullPower.textContent = buyPct + '%';
if (bearPower) bearPower.textContent = sellPct + '%';
if (sig) {
if (dominant === 'bull') {
sig.textContent = 'COMPRADORES DOMINAM';
sig.style.color = '#22c55e';
sig.style.borderColor = 'rgba(34,197,94,0.3)';
sig.style.background = 'rgba(34,197,94,0.1)';
} else if (dominant === 'bear') {
sig.textContent = 'VENDEDORES DOMINAM';
sig.style.color = '#ef4444';
sig.style.borderColor = 'rgba(239,68,68,0.3)';
sig.style.background = 'rgba(239,68,68,0.1)';
} else {
sig.textContent = 'EQUILIBRIO';
sig.style.color = '#eab308';
sig.style.borderColor = 'rgba(234,179,8,0.3)';
sig.style.background = 'rgba(234,179,8,0.1)';
}
}
}
updateAnimals(dominant, diff) {
var bullSide = this.el['bull-side'];
var bearSide = this.el['bear-side'];
if (!bullSide || !bearSide) return;
bullSide.classList.remove('dominant', 'receding');
bearSide.classList.remove('dominant', 'receding');
var intensity = Math.min(diff / 50, 1);
if (dominant === 'bull') {
bullSide.classList.add('dominant');
} else if (dominant === 'bear') {
bearSide.classList.add('dominant');
}
}
updateIndicator(dominant, buyPct, sellPct) {
var icon = this.el['indicator-icon'];
var text = this.el['indicator-text'];
var state = this.el['market-state'];
var diff = this.el['differential'];
var intens = this.el['intensity'];
var ind = this.el['center-indicator'];
if (!icon || !text) return;
var absDiff = Math.abs(buyPct - sellPct);
var assetName = this.id.toUpperCase();
if (dominant === 'bull') {
icon.textContent = '\uD83D\uDC02';
text.textContent = assetName + ' COMPRADORES';
text.style.color = '#22c55e';
} else if (dominant === 'bear') {
icon.textContent = '\uD83D\uDC3B';
text.textContent = assetName + ' VENDEDORES';
text.style.color = '#ef4444';
} else {
icon.textContent = '\u2696';
text.textContent = assetName + ' EQUILIBRADO';
text.style.color = '#eab308';
}
if (state) {
if (dominant === 'bull') state.textContent = 'FORCA COMPRADORA';
else if (dominant === 'bear') state.textContent = 'FORCA VENDEDORA';
else state.textContent = 'EQUILIBRIO';
}
if (diff) {
var d = Math.round(this.targetBuy - this.targetSell);
diff.textContent = (d > 0 ? '+' : '') + d;
diff.style.color = d > 0 ? '#22c55e' : d < 0 ? '#ef4444' : '#eab308';
}
if (intens) {
if (absDiff >= 60) intens.textContent = 'EXTREMA';
else if (absDiff >= 40) intens.textContent = 'FORTE';
else if (absDiff >= 20) intens.textContent = 'MODERADA';
else intens.textContent = 'BAIXA';
}
if (ind) {
ind.classList.remove('bull-dom', 'bear-dom', 'equal');
ind.classList.add(dominant === 'bull' ? 'bull-dom' : dominant === 'bear' ? 'bear-dom' : 'equal');
}
}
updateScene(dominant, diff) {
var scene = this.el['scene'];
if (!scene) return;
var push = Math.min(diff / 100, 0.4);
if (dominant === 'bull') {
scene.style.transform = 'scale(1) translateX(' + (-push * 3) + '%)';
} else if (dominant === 'bear') {
scene.style.transform = 'scale(1) translateX(' + (push * 3) + '%)';
} else {
scene.style.transform = 'scale(1) translateX(0)';
}
}
updateParticles(dt) {
for (var i = this.particles.length - 1; i >= 0; i--) {
var p = this.particles[i];
p.x += p.vx * dt;
p.y += p.vy * dt;
p.life -= p.decay * dt;
p.vx += (Math.random() - 0.5) * 0.1;
if (p.life <= 0) this.particles.splice(i, 1);
}
if (this.particles.length > 200) this.particles.splice(0, this.particles.length - 200);
}
renderParticles() {
if (!this.pCtx) return;
var ctx = this.pCtx;
ctx.clearRect(0, 0, this.W, this.H);
for (var i = 0; i < this.particles.length; i++) {
var p = this.particles[i];
var alpha = p.life * 0.8;
ctx.save();
ctx.globalAlpha = alpha;
ctx.shadowColor = 'rgba(' + p.glow[0] + ',' + p.glow[1] + ',' + p.glow[2] + ',0.6)';
ctx.shadowBlur = p.size * 3;
ctx.fillStyle = 'rgba(' + p.color[0] + ',' + p.color[1] + ',' + p.color[2] + ',' + alpha + ')';
ctx.beginPath();
ctx.arc(p.x, p.y, p.size * p.life, 0, Math.PI * 2);
ctx.fill();
ctx.restore();
}
}
renderCandles(time, dominant) {
if (!this.cCtx) return;
var ctx = this.cCtx;
var w = this.cCanvas.width;
var h = this.cCanvas.height;
ctx.clearRect(0, 0, w, h);
ctx.globalAlpha = 0.12;
for (var i = 0; i < this.candles.length; i++) {
var c = this.candles[i];
var phase = (time * c.speed + c.offset) % 3;
var priceMove = Math.sin(phase) * 30;
var o = c.open + priceMove;
var cl = c.close + priceMove * 0.7;
if (o > cl) { var tmp = o; o = cl; cl = tmp; }
var x = c.x * w;
var bodyTop = h - (cl / 200) * h * 0.8 - 10;
var bodyBot = h - (o / 200) * h * 0.8 - 10;
var bodyH = Math.max(bodyBot - bodyTop, 2);
var isGreen;
if (dominant === 'bull') isGreen = Math.random() > 0.25;
else if (dominant === 'bear') isGreen = Math.random() > 0.75;
else isGreen = Math.random() > 0.5;
ctx.fillStyle = isGreen ? '#22c55e' : '#ef4444';
ctx.fillRect(x - c.w / 2, bodyTop, c.w, bodyH);
ctx.fillRect(x - 0.5, bodyTop - 6, 1, bodyH + 12);
}
ctx.globalAlpha = 1;
}
}
var battleWin = null;
var battleWdo = null;
function initBattleArenas() {
var winContainer = document.getElementById('arena-win');
var wdoContainer = document.getElementById('arena-wdo');
if (winContainer) battleWin = new BattleArena({ id: 'win', container: winContainer });
if (wdoContainer) battleWdo = new BattleArena({ id: 'wdo', container: wdoContainer });
}
function updateBattleArenas(winScore, wdoScore) {
if (battleWin && winScore !== undefined) {
var buy = Math.max(0, Math.min(100, winScore));
var sell = Math.max(0, Math.min(100, 100 - winScore));
battleWin.update(buy, sell);
}
if (battleWdo && wdoScore !== undefined) {
var buy2 = Math.max(0, Math.min(100, wdoScore));
var sell2 = Math.max(0, Math.min(100, 100 - wdoScore));
battleWdo.update(buy2, sell2);
}
}