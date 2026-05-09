"""
A股分析API接口模块

提供RESTful API接口用于：
1. 获取实时行情
2. 分析个股
3. 批量分析
4. 板块分析
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from flask import Flask, jsonify, request

logger = logging.getLogger(__name__)


def create_a_stock_api_app():
    """创建A股分析API应用"""
    app = Flask(__name__)

    # 初始化分析器
    from src.tools.a_stock_api import AStockAPI
    from src.utils.tencent_api import get_stock_quotes
    from src.utils.eastmoney_api import EastMoneyAPI
    from src.utils.technical_indicators import analyze_technical
    from src.utils.cache_enhanced import get_cache

    a_stock_api = AStockAPI()
    eastmoney_api = EastMoneyAPI()
    cache = get_cache()

    @app.route('/api/v1/quote/<ticker>', methods=['GET'])
    def get_quote(ticker):
        """获取实时行情"""
        try:
            quotes = get_stock_quotes([ticker])
            if ticker in quotes:
                q = quotes[ticker]
                return jsonify({
                    "success": True,
                    "data": {
                        "ticker": q.code,
                        "name": q.name,
                        "price": q.price,
                        "change": q.change,
                        "change_pct": q.change_pct,
                        "open": q.open,
                        "high": q.high,
                        "low": q.low,
                        "volume": q.volume,
                        "amount": q.amount,
                        "prev_close": q.prev_close,
                    }
                })
            return jsonify({"success": False, "error": "无法获取行情数据"}), 404

        except Exception as e:
            logger.error(f"获取行情失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/v1/quotes', methods=['POST'])
    def get_quotes():
        """批量获取实时行情"""
        try:
            data = request.get_json()
            tickers = data.get('tickers', [])

            if not tickers:
                return jsonify({"success": False, "error": "请提供股票代码列表"}), 400

            quotes = get_stock_quotes(tickers)

            result = []
            for ticker, q in quotes.items():
                result.append({
                    "ticker": q.code,
                    "name": q.name,
                    "price": q.price,
                    "change_pct": q.change_pct,
                    "volume": q.volume,
                })

            return jsonify({"success": True, "data": result, "count": len(result)})

        except Exception as e:
            logger.error(f"批量获取行情失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/v1/kline/<ticker>', methods=['GET'])
    def get_kline(ticker):
        """获取K线数据"""
        try:
            period = request.args.get('period', 'day')
            count = int(request.args.get('count', 60))

            klines = eastmoney_api.get_kline_data(ticker, period=period, count=count)

            if klines:
                result = [{
                    "date": k.date,
                    "open": k.open,
                    "close": k.close,
                    "high": k.high,
                    "low": k.low,
                    "volume": k.volume,
                    "change_pct": k.change_pct,
                } for k in klines]
                return jsonify({"success": True, "data": result, "count": len(result)})

            return jsonify({"success": False, "error": "无法获取K线数据"}), 404

        except Exception as e:
            logger.error(f"获取K线失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/v1/fundflow/<ticker>', methods=['GET'])
    def get_fundflow(ticker):
        """获取资金流向"""
        try:
            flow = eastmoney_api.get_fund_flow(ticker)

            if flow:
                return jsonify({
                    "success": True,
                    "data": {
                        "ticker": flow.ticker,
                        "name": flow.name,
                        "main_net_inflow": flow.main_net_inflow,
                        "super_net_inflow": flow.super_net_inflow,
                        "big_net_inflow": flow.big_net_inflow,
                        "medium_net_inflow": flow.medium_net_inflow,
                        "small_net_inflow": flow.small_net_inflow,
                    }
                })

            return jsonify({"success": False, "error": "无法获取资金流向数据"}), 404

        except Exception as e:
            logger.error(f"获取资金流向失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/v1/technical/<ticker>', methods=['GET'])
    def get_technical(ticker):
        """获取技术指标分析"""
        try:
            klines = eastmoney_api.get_kline_data(ticker, count=60)

            if not klines:
                return jsonify({"success": False, "error": "无法获取K线数据"}), 404

            closes = [k.close for k in klines]
            highs = [k.high for k in klines]
            lows = [k.low for k in klines]

            indicators = analyze_technical(closes, highs, lows)

            return jsonify({
                "success": True,
                "data": {
                    "ticker": ticker,
                    "trend": indicators.trend,
                    "strength": indicators.signal_strength,
                    "macd": indicators.macd,
                    "macd_signal": indicators.macd_signal,
                    "kdj_k": indicators.kdj_k,
                    "kdj_d": indicators.kdj_d,
                    "kdj_j": indicators.kdj_j,
                    "rsi_6": indicators.rsi_6,
                    "rsi_12": indicators.rsi_12,
                    "rsi_24": indicators.rsi_24,
                    "boll_upper": indicators.boll_upper,
                    "boll_middle": indicators.boll_middle,
                    "boll_lower": indicators.boll_lower,
                    "ma5": indicators.ma5,
                    "ma10": indicators.ma10,
                    "ma20": indicators.ma20,
                }
            })

        except Exception as e:
            logger.error(f"获取技术指标失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/v1/northbound', methods=['GET'])
    def get_northbound():
        """获取北向资金"""
        try:
            days = int(request.args.get('days', 30))
            flows = a_stock_api.get_northbound_flow(days=days)

            if flows:
                result = [{
                    "date": f.date,
                    "buy_amount": f.buy_amount,
                    "sell_amount": f.sell_amount,
                    "net_buy": f.net_buy,
                } for f in flows]
                return jsonify({"success": True, "data": result, "count": len(result)})

            return jsonify({"success": False, "error": "无法获取北向资金数据"}), 404

        except Exception as e:
            logger.error(f"获取北向资金失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/v1/sectors', methods=['GET'])
    def get_sectors():
        """获取板块数据"""
        try:
            sectors = eastmoney_api.get_sector_fund_flow()

            if sectors:
                return jsonify({
                    "success": True,
                    "data": sectors,
                    "count": len(sectors)
                })

            return jsonify({"success": False, "error": "无法获取板块数据"}), 404

        except Exception as e:
            logger.error(f"获取板块数据失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/v1/analyze/<ticker>', methods=['GET'])
    def analyze_stock(ticker):
        """综合分析单只股票"""
        try:
            # 获取行情
            quotes = get_stock_quotes([ticker])
            if ticker not in quotes:
                return jsonify({"success": False, "error": "无法获取行情数据"}), 404

            quote = quotes[ticker]

            # 获取K线
            klines = eastmoney_api.get_kline_data(ticker, count=60)

            # 获取资金流向
            flow = eastmoney_api.get_fund_flow(ticker)

            # 技术分析
            technical_result = {}
            if klines:
                closes = [k.close for k in klines]
                highs = [k.high for k in klines]
                lows = [k.low for k in klines]
                indicators = analyze_technical(closes, highs, lows)
                technical_result = {
                    "trend": indicators.trend,
                    "strength": indicators.signal_strength,
                    "macd": indicators.macd,
                    "kdj": indicators.kdj_j,
                    "rsi": indicators.rsi_12,
                }

            # 综合评分
            score = 50
            if technical_result.get('trend') == 'bullish':
                score += 15
            elif technical_result.get('trend') == 'bearish':
                score -= 15

            if flow and flow.main_net_inflow > 0:
                score += 10
            elif flow and flow.main_net_inflow < 0:
                score -= 10

            if quote.change_pct > 0:
                score += 5

            score = max(0, min(100, score))

            signal = "bullish" if score >= 65 else ("bearish" if score <= 40 else "neutral")

            return jsonify({
                "success": True,
                "data": {
                    "ticker": ticker,
                    "name": quote.name,
                    "price": quote.price,
                    "change_pct": quote.change_pct,
                    "volume": quote.volume,
                    "technical": technical_result,
                    "fund_flow": {
                        "main_net_inflow": flow.main_net_inflow if flow else 0,
                    } if flow else None,
                    "score": score,
                    "signal": signal,
                    "recommendation": "建议关注" if signal == "bullish" else ("建议谨慎" if signal == "bearish" else "建议观望"),
                }
            })

        except Exception as e:
            logger.error(f"综合分析失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/v1/health', methods=['GET'])
    def health_check():
        """健康检查"""
        return jsonify({
            "success": True,
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        })

    return app


if __name__ == "__main__":
    app = create_a_stock_api_app()
    app.run(host='0.0.0.0', port=5001, debug=True)