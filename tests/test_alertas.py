import sys
sys.path.insert(0, '.')
import time
from datetime import datetime
from market_data import MarketDataService
from analysis import AnalysisEngine
from signal_engine import calculate_score

market_service = MarketDataService()
analysis_engine = AnalysisEngine(market_service)

results = analysis_engine.analyze_all()
alerts = []

for asset_name, analysis in results.items():
    score = calculate_score(analysis)
    sr = analysis.indicators.sr
    price = analysis.price
    print(f'{asset_name}: score={score.total}, rsi={analysis.rsi}, vol_ratio={analysis.volume_ratio}')
    
    resist_1_val = sr.get('resist_1', 0)
    support_1_val = sr.get('support_1', 0)
    
    print(f'  resist_1={resist_1_val}, support_1={support_1_val}, price={price}')
    print(f'  resist check: price > resist_1*0.999 = {price > resist_1_val * 0.999 if resist_1_val > 0 else "N/A"}')
    print(f'  support check: price < support_1*1.001 = {price < support_1_val * 1.001 if support_1_val > 0 else "N/A"}')

print('Done - no errors')
