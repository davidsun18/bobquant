# 应用 v2.5 分时均线做 T 策略补丁
import sys
sys.path.insert(0, '..')

from engine import GridTStrategy

# 应用补丁
GridTStrategy.check_sell = check_sell_v2_5
GridTStrategy.check_buyback = check_buyback_v2_5

print("✅ v2.5 分时均线做 T 策略已应用")
