from binance.client import Client
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Any
import logging
from functools import wraps
from binance.exceptions import BinanceAPIException
from requests.exceptions import RequestException
import time

logger = logging.getLogger(__name__)

def retry_on_network_error(max_retries=5, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (BinanceAPIException, RequestException) as e:
                    if attempt == max_retries - 1:
                        logger.error(f"最大重试次数已达到。最后一次错误: {str(e)}")
                        raise
                    logger.warning(f"操作失败，正在重试 ({attempt + 1}/{max_retries}): {str(e)}")
                    time.sleep(delay * (2 ** attempt))  # 指数退避
        return wrapper
    return decorator

class BinanceOperations:
    def __init__(self, get_binance_client):
        self.get_binance_client = get_binance_client

    @retry_on_network_error()
    def get_positions(self, symbol: str):
        client = self.get_binance_client()
        try:
            positions = client.futures_position_information(symbol=symbol)
            return positions[0] if positions else None
        except Exception as e:
            logger.error(f"获取持仓信息时发生错误: {str(e)}")
            raise

    @retry_on_network_error()
    def get_usdt_balance(self):
        client = self.get_binance_client()
        try:
            account = client.futures_account_balance()
            usdt_balance = next((Decimal(asset['balance']) for asset in account if asset['asset'] == 'USDT'), None)
            return usdt_balance if usdt_balance else Decimal('0')
        except Exception as e:
            logger.error(f"获取USDT余额时发生错误: {str(e)}")
            raise

    @retry_on_network_error()
    def get_current_price(self, symbol: str):
        client = self.get_binance_client()
        try:
            ticker = client.futures_symbol_ticker(symbol=symbol)
            return Decimal(ticker['price'])
        except Exception as e:
            logger.error(f"获取当前价格时发生错误: {str(e)}")
            raise

    def calculate_quantity(self, symbol: str, usdt_balance: Decimal, current_price: Decimal) -> Decimal:
        try:
            # 获取交易对的精度信息
            symbol_info = self.get_binance_client().futures_exchange_info()
            symbol_info = next(filter(lambda x: x['symbol'] == symbol, symbol_info['symbols']))
            quantity_precision = int(symbol_info['quantityPrecision'])

            # 计算数量，使用全部可用余额
            quantity = usdt_balance / current_price

            # 根据精度截断数量
            quantity = quantity.quantize(Decimal(f'1.{"0" * quantity_precision}'), rounding=ROUND_DOWN)

            return quantity
        except Exception as e:
            logger.error(f"计算交易数量时发生错误: {str(e)}")
            raise

    @retry_on_network_error()
    def create_order(self, symbol: str, side: str, quantity: Decimal, leverage: int):
        client = self.get_binance_client()
        try:
            # 设置杠杆
            client.futures_change_leverage(symbol=symbol, leverage=leverage)
            
            # 创建订单
            order = client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=float(quantity)
            )
            
            # 获取完整的订单信息
            order_info = client.futures_get_order(symbol=symbol, orderId=order['orderId'])
            order_info['leverage'] = leverage
            return order_info
        except Exception as e:
            logger.error(f"创建订单时发生错误: {str(e)}")
            raise

    @retry_on_network_error()
    def close_position(self, symbol: str, position_side: str, quantity: Decimal):
        client = self.get_binance_client()
        try:
            side = 'SELL' if quantity > 0 else 'BUY'

            
            # 创建平仓订单
            order = client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=float(abs(quantity))
            )
            
            # 获取完整的订单信息
            order_info = client.futures_get_order(symbol=symbol, orderId=order['orderId'])
            return order_info
        except Exception as e:
            logger.error(f"平仓时发生错误: {str(e)}")
            raise

    @retry_on_network_error()
    def set_leverage(self, symbol: str, leverage: int):
        client = self.get_binance_client()
        try:
            return client.futures_change_leverage(symbol=symbol, leverage=leverage)
        except Exception as e:
            logger.error(f"设置杠杆时发生错误: {str(e)}")
            raise

    @retry_on_network_error()
    def get_current_leverage(self, symbol: str) -> int:
        client = self.get_binance_client()
        try:
            position_info = client.futures_position_information(symbol=symbol)
            return int(position_info[0]['leverage'])
        except Exception as e:
            logger.error(f"获取当前杠杆时发生错误: {str(e)}")
            raise

    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        client = self.get_binance_client()
        symbol_info = client.futures_exchange_info()
        return next(s for s in symbol_info['symbols'] if s['symbol'] == symbol)
