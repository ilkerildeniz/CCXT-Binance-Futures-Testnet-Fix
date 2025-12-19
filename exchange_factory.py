"""
CCXT Binance Futures Testnet Fix
================================
Bypass solution for CCXT's deprecated sandbox mode on Binance Futures.
Usage:
    from exchange_factory import ExchangeFactory
    
    exchange = ExchangeFactory.create_binance_demo(
        api_key="YOUR_API_KEY",
        secret="YOUR_SECRET"
    )
"""
import ccxt
import types
import hashlib
import hmac
import time
import aiohttp
from urllib.parse import urlencode
class ExchangeFactory:
    """Factory for creating exchange instances with testnet patches."""
    
    @classmethod
    def create_binance_demo(cls, api_key: str, secret: str):
        """
        Create a Binance Futures instance that works with Demo/Testnet.
        
        Args:
            api_key: Your Binance Demo API key
            secret: Your Binance Demo secret key
            
        Returns:
            Patched ccxt.binance instance
        """
        instance = ccxt.binance({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
                'adjustForTimeDifference': True,
                'recvWindow': 60000,
            }
        })
        
        instance.set_sandbox_mode(True)
        cls._apply_patches(instance)
        
        return instance
    
    @classmethod
    def _apply_patches(cls, instance):
        """Apply all necessary patches to the instance."""
        
        # PATCH 1: fetch_balance
        async def patched_fetch_balance(self, params={}):
            timestamp = int(time.time() * 1000)
            payload = {'timestamp': timestamp, 'recvWindow': 60000}
            query_string = urlencode(payload)
            
            signature = hmac.new(
                self.secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            url = f"https://testnet.binancefuture.com/fapi/v2/account?{query_string}&signature={signature}"
            headers = {'X-MBX-APIKEY': self.apiKey}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, ssl=False) as response:
                    data = await response.json()
                    if response.status != 200:
                        raise Exception(f"Balance fetch failed: {data}")
                    
                    result = {'info': data, 'free': {}, 'used': {}, 'total': {}}
                    for asset in data.get('assets', []):
                        currency = asset.get('asset')
                        if not currency:
                            continue
                        total = float(asset.get('walletBalance', 0))
                        free = float(asset.get('availableBalance', 0))
                        result[currency] = {'free': free, 'used': total - free, 'total': total}
                        result['free'][currency] = free
                        result['total'][currency] = total
                    return result
        
        instance.fetch_balance = types.MethodType(patched_fetch_balance, instance)
        
        # PATCH 2: fetch_ticker
        async def patched_fetch_ticker(self, symbol, params={}):
            if not self.markets:
                await self.load_markets()
            
            market = self.market(symbol)
            url = f"https://testnet.binancefuture.com/fapi/v1/ticker/24hr?symbol={market['id']}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, ssl=False) as response:
                    data = await response.json()
                    if response.status != 200:
                        raise Exception(f"Ticker fetch failed: {data}")
                    return self.parse_ticker(data, market)
        
        instance.fetch_ticker = types.MethodType(patched_fetch_ticker, instance)
        
        # PATCH 3: fetch_positions
        async def patched_fetch_positions(self, symbols=None, params={}):
            timestamp = int(time.time() * 1000)
            payload = {'timestamp': timestamp, 'recvWindow': 60000}
            query_string = urlencode(payload)
            
            signature = hmac.new(
                self.secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            url = f"https://testnet.binancefuture.com/fapi/v2/positionRisk?{query_string}&signature={signature}"
            headers = {'X-MBX-APIKEY': self.apiKey}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, ssl=False) as response:
                    data = await response.json()
                    if response.status != 200:
                        raise Exception(f"Positions fetch failed: {data}")
                    
                    result = []
                    for item in data:
                        result.append({
                            'info': item,
                            'symbol': item['symbol'],
                            'contracts': float(item['positionAmt']),
                            'unrealizedPnl': float(item['unRealizedProfit']),
                            'leverage': float(item['leverage']),
                            'side': 'long' if float(item['positionAmt']) > 0 else 'short',
                            'entryPrice': float(item['entryPrice']),
                        })
                    return result
        
        instance.fetch_positions = types.MethodType(patched_fetch_positions, instance)
        
        # PATCH 4: create_order
        async def patched_create_order(self, symbol, type, side, amount, price=None, params={}):
            if not self.markets:
                await self.load_markets()
            
            market = self.market(symbol)
            timestamp = int(time.time() * 1000)
            
            order_params = {
                'symbol': market['id'],
                'side': side.upper(),
                'type': type.upper(),
                'quantity': str(amount),
                'timestamp': timestamp,
                'recvWindow': 60000
            }
            
            if price and type.upper() == 'LIMIT':
                order_params['price'] = str(price)
                order_params['timeInForce'] = params.get('timeInForce', 'GTC')
            
            for key, value in params.items():
                if key not in order_params:
                    order_params[key] = value
            
            query_string = urlencode(order_params)
            signature = hmac.new(
                self.secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            url = f"https://testnet.binancefuture.com/fapi/v1/order?{query_string}&signature={signature}"
            headers = {'X-MBX-APIKEY': self.apiKey}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, ssl=False) as response:
                    data = await response.json()
                    if response.status != 200:
                        raise Exception(f"Order failed: {data}")
                    print(f"✅ Order Success: ID={data.get('orderId')}")
                    return self.parse_order(data, market)
        
        instance.create_order = types.MethodType(patched_create_order, instance)
        print("✅ All patches applied!")

