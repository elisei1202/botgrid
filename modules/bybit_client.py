"""
Bybit Client Module - API Communication
Handles all REST and WebSocket communication with Bybit
"""

import hmac
import hashlib
import time
import asyncio
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)


def safe_float(value, default=0.0):
    """Safely convert value to float, return default if conversion fails"""
    try:
        if value is None or value == '':
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


class BybitClient:
    """Async Bybit API client for Unified Trading Account"""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        self.base_url = (
            "https://api-testnet.bybit.com" if testnet 
            else "https://api.bybit.com"
        )
        
        self.recv_window = 5000
        self.session = None
        
        # Rate limiting
        self.rate_limit_per_second = 10
        self.last_request_time = 0
        self.request_times = []
        
        logger.info(f"Bybit client initialized ({'testnet' if testnet else 'mainnet'})")
    
    async def initialize(self):
        """Initialize aiohttp session"""
        self.session = aiohttp.ClientSession()
        logger.info("HTTP session initialized")
    
    async def close(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            logger.info("HTTP session closed")
    
    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """Generate signature for authenticated requests"""
        param_str = urlencode(sorted(params.items()))
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            param_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    async def _rate_limit(self):
        """Simple rate limiting implementation"""
        current_time = time.time()
        
        # Remove old timestamps (older than 1 second)
        self.request_times = [
            t for t in self.request_times 
            if current_time - t < 1.0
        ]
        
        # If we've made too many requests, wait
        if len(self.request_times) >= self.rate_limit_per_second:
            sleep_time = 1.0 - (current_time - self.request_times[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                self.request_times = []
        
        self.request_times.append(current_time)
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        params: Dict = None,
        signed: bool = True,
        retry_count: int = 3
    ) -> Dict[str, Any]:
        """Make HTTP request to Bybit API with retry logic"""
        
        if params is None:
            params = {}
        
        await self._rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        
        if signed:
            timestamp = str(int(time.time() * 1000))
            params['api_key'] = self.api_key
            params['timestamp'] = timestamp
            params['recv_window'] = str(self.recv_window)
            params['sign'] = self._generate_signature(params)
        
        for attempt in range(retry_count):
            try:
                if method == "GET":
                    async with self.session.get(url, params=params, timeout=10) as response:
                        data = await response.json()
                        
                elif method == "POST":
                    headers = {'Content-Type': 'application/json'}
                    async with self.session.post(url, json=params, headers=headers, timeout=10) as response:
                        data = await response.json()
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                # Check response
                if data.get('retCode') == 0:
                    return data.get('result', {})
                
                # Handle specific errors
                ret_code = data.get('retCode')
                ret_msg = data.get('retMsg', '')
                
                # Non-critical errors that we can handle
                if ret_code in [10001, 110043, 100028]:
                    logger.warning(f"Bybit error {ret_code}: {ret_msg} (continuing)")
                    return {'error': ret_code, 'message': ret_msg}
                
                # Rate limit error - wait and retry
                if ret_code == 10006:
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limit hit, waiting {wait_time}s before retry {attempt + 1}/{retry_count}")
                    await asyncio.sleep(wait_time)
                    continue
                
                # Other errors
                logger.error(f"Bybit API error: {ret_code} - {ret_msg}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(1)
                    continue
                
                return {'error': ret_code, 'message': ret_msg}
                
            except asyncio.TimeoutError:
                logger.error(f"Request timeout (attempt {attempt + 1}/{retry_count})")
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
                
            except Exception as e:
                logger.error(f"Request exception: {e} (attempt {attempt + 1}/{retry_count})")
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
        
        return {'error': 'max_retries', 'message': 'Maximum retry attempts exceeded'}
    
    # ============ MARKET DATA ============
    
    async def get_ticker(self, symbol: str, category: str = "linear") -> Dict[str, Any]:
        """Get latest ticker price"""
        params = {
            'category': category,
            'symbol': symbol
        }
        result = await self._request("GET", "/v5/market/tickers", params, signed=False)
        if result and 'list' in result and len(result['list']) > 0:
            return result['list'][0]
        return {}
    
    async def get_mark_price(self, symbol: str, category: str = "linear") -> float:
        """Get current mark price"""
        ticker = await self.get_ticker(symbol, category)
        if ticker and 'markPrice' in ticker:
            return float(ticker['markPrice'])
        return 0.0
    
    async def get_instruments_info(self, symbol: str, category: str = "linear") -> Dict[str, Any]:
        """Get instrument specifications (min qty, step size, etc.)"""
        params = {
            'category': category,
            'symbol': symbol
        }
        result = await self._request("GET", "/v5/market/instruments-info", params, signed=False)
        if result and 'list' in result and len(result['list']) > 0:
            return result['list'][0]
        return {}
    
    async def get_kline(
        self, 
        symbol: str, 
        interval: str = "60",  # 1 hour
        limit: int = 200,
        category: str = "linear"
    ) -> List[Dict[str, Any]]:
        """Get kline/candlestick data"""
        params = {
            'category': category,
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        result = await self._request("GET", "/v5/market/kline", params, signed=False)
        if result and 'list' in result:
            return result['list']
        return []
    
    # ============ ACCOUNT & WALLET ============
    
    async def get_wallet_balance(self, account_type: str = "UNIFIED") -> Dict[str, Any]:
        """Get wallet balance for unified account"""
        params = {
            'accountType': account_type
        }
        result = await self._request("GET", "/v5/account/wallet-balance", params)
        if result and 'list' in result and len(result['list']) > 0:
            wallet = result['list'][0]
            # Ensure numeric fields have valid values
            return {
                'accountType': wallet.get('accountType', account_type),
                'totalEquity': wallet.get('totalEquity', '0'),
                'totalWalletBalance': wallet.get('totalWalletBalance', '0'),
                'totalMarginBalance': wallet.get('totalMarginBalance', '0'),
                'totalAvailableBalance': wallet.get('totalAvailableBalance', '0'),
                'totalPerpUPL': wallet.get('totalPerpUPL', '0'),
                'totalInitialMargin': wallet.get('totalInitialMargin', '0'),
                'totalMaintenanceMargin': wallet.get('totalMaintenanceMargin', '0'),
                'coin': wallet.get('coin', [])
            }
        # Return safe defaults
        return {
            'accountType': account_type,
            'totalEquity': '0',
            'totalWalletBalance': '0',
            'totalMarginBalance': '0',
            'totalAvailableBalance': '0',
            'totalPerpUPL': '0',
            'totalInitialMargin': '0',
            'totalMaintenanceMargin': '0',
            'coin': []
        }
    
    async def get_coin_balance(self, coin: str = "USDT") -> Dict[str, Any]:
        """Get specific coin balance"""
        wallet = await self.get_wallet_balance()
        if wallet and 'coin' in wallet:
            for coin_data in wallet['coin']:
                if coin_data['coin'] == coin:
                    # Ensure all numeric fields have valid values
                    return {
                        'coin': coin_data.get('coin', coin),
                        'walletBalance': coin_data.get('walletBalance', '0'),
                        'availableToWithdraw': coin_data.get('availableToWithdraw', '0'),
                        'totalOrderIM': coin_data.get('totalOrderIM', '0'),
                        'totalPositionIM': coin_data.get('totalPositionIM', '0'),
                        'unrealisedPnl': coin_data.get('unrealisedPnl', '0'),
                        'cumRealisedPnl': coin_data.get('cumRealisedPnl', '0')
                    }
        # Return safe defaults if not found
        return {
            'coin': coin,
            'walletBalance': '0',
            'availableToWithdraw': '0',
            'totalOrderIM': '0',
            'totalPositionIM': '0',
            'unrealisedPnl': '0',
            'cumRealisedPnl': '0'
        }
    
    # ============ POSITIONS ============
    
    async def get_positions(
        self, 
        symbol: str = None, 
        category: str = "linear"
    ) -> List[Dict[str, Any]]:
        """Get current positions"""
        params = {
            'category': category,
            'settleCoin': 'USDT'
        }
        if symbol:
            params['symbol'] = symbol
        
        result = await self._request("GET", "/v5/position/list", params)
        if result and 'list' in result:
            return result['list']
        return []
    
    async def get_position(self, symbol: str, category: str = "linear") -> Optional[Dict[str, Any]]:
        """Get position for specific symbol"""
        positions = await self.get_positions(symbol, category)
        for pos in positions:
            if pos['symbol'] == symbol and float(pos['size']) > 0:
                return pos
        return None
    
    async def set_leverage(
        self, 
        symbol: str, 
        buy_leverage: str, 
        sell_leverage: str,
        category: str = "linear"
    ) -> Dict[str, Any]:
        """Set leverage for symbol"""
        params = {
            'category': category,
            'symbol': symbol,
            'buyLeverage': buy_leverage,
            'sellLeverage': sell_leverage
        }
        return await self._request("POST", "/v5/position/set-leverage", params)
    
    # ============ ORDERS ============
    
    async def place_order(
        self,
        symbol: str,
        side: str,  # Buy or Sell
        order_type: str,  # Limit or Market
        qty: str,
        price: str = None,
        time_in_force: str = "PostOnly",
        position_idx: int = 0,
        category: str = "linear",
        order_link_id: str = None
    ) -> Dict[str, Any]:
        """Place an order"""
        params = {
            'category': category,
            'symbol': symbol,
            'side': side,
            'orderType': order_type,
            'qty': qty,
            'timeInForce': time_in_force,
            'positionIdx': position_idx
        }
        
        if price:
            params['price'] = price
        
        if order_link_id:
            params['orderLinkId'] = order_link_id
        
        result = await self._request("POST", "/v5/order/create", params)
        return result
    
    async def cancel_order(
        self,
        symbol: str,
        order_id: str = None,
        order_link_id: str = None,
        category: str = "linear"
    ) -> Dict[str, Any]:
        """Cancel an order"""
        params = {
            'category': category,
            'symbol': symbol
        }
        
        if order_id:
            params['orderId'] = order_id
        elif order_link_id:
            params['orderLinkId'] = order_link_id
        else:
            raise ValueError("Either order_id or order_link_id must be provided")
        
        return await self._request("POST", "/v5/order/cancel", params)
    
    async def cancel_all_orders(
        self,
        symbol: str = None,
        category: str = "linear"
    ) -> Dict[str, Any]:
        """Cancel all orders for symbol or all symbols"""
        params = {
            'category': category
        }
        
        if symbol:
            params['symbol'] = symbol
        
        return await self._request("POST", "/v5/order/cancel-all", params)
    
    async def get_open_orders(
        self,
        symbol: str = None,
        category: str = "linear",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get open orders"""
        params = {
            'category': category,
            'limit': limit
        }
        
        if symbol:
            params['symbol'] = symbol
        
        result = await self._request("GET", "/v5/order/realtime", params)
        if result and 'list' in result:
            return result['list']
        return []
    
    async def get_order_history(
        self,
        symbol: str = None,
        category: str = "linear",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get order history"""
        params = {
            'category': category,
            'limit': limit
        }
        
        if symbol:
            params['symbol'] = symbol
        
        result = await self._request("GET", "/v5/order/history", params)
        if result and 'list' in result:
            return result['list']
        return []
    
    # ============ TRADE HISTORY ============
    
    async def get_executions(
        self,
        symbol: str = None,
        category: str = "linear",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get execution history"""
        params = {
            'category': category,
            'limit': limit
        }
        
        if symbol:
            params['symbol'] = symbol
        
        result = await self._request("GET", "/v5/execution/list", params)
        if result and 'list' in result:
            return result['list']
        return []
    
    # ============ HELPERS ============
    
    async def close_position(
        self,
        symbol: str,
        category: str = "linear"
    ) -> Dict[str, Any]:
        """Close position at market price"""
        position = await self.get_position(symbol, category)
        
        if not position or float(position['size']) == 0:
            return {'error': 'no_position', 'message': 'No open position to close'}
        
        side = "Sell" if position['side'] == "Buy" else "Buy"
        qty = position['size']
        
        return await self.place_order(
            symbol=symbol,
            side=side,
            order_type="Market",
            qty=qty,
            category=category,
            time_in_force="IOC"  # Immediate or Cancel for market orders
        )
    
    def format_quantity(self, qty: float, qty_step: str) -> str:
        """Format quantity according to step size"""
        step = float(qty_step)
        precision = len(qty_step.rstrip('0').split('.')[-1]) if '.' in qty_step else 0
        formatted = int(qty / step) * step
        return f"{formatted:.{precision}f}"
    
    def format_price(self, price: float, tick_size: str) -> str:
        """Format price according to tick size"""
        tick = float(tick_size)
        precision = len(tick_size.rstrip('0').split('.')[-1]) if '.' in tick_size else 0
        formatted = int(price / tick) * tick
        return f"{formatted:.{precision}f}"
