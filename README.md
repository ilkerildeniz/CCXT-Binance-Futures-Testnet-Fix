# CCXT-Binance-Futures-Testnet-Fix
> Complete bypass solution for CCXT's deprecated sandbox mode on Binance Futures
## 📌 The Problem
When you try to use Binance Futures Testnet with CCXT, you get this error:
binance testnet/sandbox mode is not supported for futures anymore, please check the deprecation announcement https://t.me/ccxt_announcements/92 and consider using the demo trading instead.

### Why Does This Happen?
1. **Binance deprecated their old Testnet** and moved to a new "Demo Trading" system
2. **CCXT's `set_sandbox_mode(True)`** still points to the old URLs and throws this error
3. **The API keys you generate on Binance Demo** (`demo.binance.com/en/futures/`) are valid
4. **But CCXT blocks the request** before it even reaches Binance
### What Methods Are Affected?
| Method | Status | Error |
|--------|--------|-------|
| [fetch_balance()](cci:1://file:///c:/Antigravity/workspace/Hummingbot/professional_ccxt_trading_system/core/exchanges/exchange_factory.py:205:24-293:39) | ❌ Blocked | NotSupported |
| [fetch_ticker()](cci:1://file:///c:/Antigravity/workspace/Hummingbot/professional_ccxt_trading_system/core/exchanges/exchange_factory.py:300:24-326:39) | ❌ Blocked | Invalid Api-Key ID |
| [fetch_positions()](cci:1://file:///c:/Antigravity/workspace/Hummingbot/professional_ccxt_trading_system/core/exchanges/exchange_factory.py:331:24-397:39) | ❌ Blocked | NotSupported |
| [create_order()](cci:1://file:///c:/Antigravity/workspace/Hummingbot/professional_ccxt_trading_system/core/exchanges/exchange_factory.py:402:24-477:39) | ❌ Blocked | Sandbox not supported |
---
## 🎯 The Solution: Manual Monkey Patching
We bypass CCXT's internal checks by **replacing the problematic methods** with our own implementations that:
1. **Manually sign requests** using HMAC-SHA256
2. **Send HTTP requests directly** to `testnet.binancefuture.com`
3. **Parse responses** back to CCXT's expected format
---
## 📋 Step-by-Step Implementation
### Step 1: Get Your Binance Demo API Keys
1. Log in to your KYC-verified Binance.com account. a.Go to Switch to demo mode on your Binance.com account. b. Get your API key from https://demo.binance.com/en/futures
2. Login with your Binance account
3. Go to **API Management** → Create new API key
4. Copy your **API Key** and **Secret Key**
5. You get **free testnet USDT** automatically!
### Step 2: Install Dependencies
```bash
pip install ccxt aiohttp
Step 3: Create the Patched Exchange Factory
Create a new file called 

exchange_factory.py
:

import ccxt
import types
import hashlib
import hmac
import time
import json
import aiohttp
from urllib.parse import urlencode
class ExchangeFactory:
    """Factory for creating exchange instances with testnet patches."""
    
    @classmethod
    def create_binance_demo(cls, api_key: str, secret: str):
        """
        Create a Binance Futures instance that works with Demo/Testnet.
        """
        # Create base instance
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
        
        # Enable sandbox mode (sets correct URLs)
        instance.set_sandbox_mode(True)
        
        # Apply patches
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
            market_id = market['id']
            url = f"https://testnet.binancefuture.com/fapi/v1/ticker/24hr?symbol={market_id}"
            
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
        
        # PATCH 4: create_order (THE KEY FIX!)
        async def patched_create_order(self, symbol, type, side, amount, price=None, params={}):
            if not self.markets:
                await self.load_markets()
            
            market = self.market(symbol)
            market_id = market['id']
            
            timestamp = int(time.time() * 1000)
            order_params = {
                'symbol': market_id,
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
Step 4: Use the Patched Exchange
import asyncio
from exchange_factory import ExchangeFactory
async def main():
    exchange = ExchangeFactory.create_binance_demo(
        api_key="YOUR_DEMO_API_KEY",
        secret="YOUR_DEMO_SECRET"
    )
    
    await exchange.load_markets()
    print(f"Loaded {len(exchange.markets)} markets")
    
    # Fetch balance
    balance = await exchange.fetch_balance()
    print(f"USDT Balance: {balance.get('USDT', {})}")
    
    # Place order
    order = await exchange.create_order(
        symbol='BTC/USDT:USDT',
        type='MARKET',
        side='BUY',
        amount=0.01
    )
    print(f"Order placed: {order['id']}")
asyncio.run(main())
🔧 How It Works
Binance requires HMAC-SHA256 signatures for authenticated endpoints:

# 1. Create payload with timestamp
payload = {'timestamp': 1703012345678, 'recvWindow': 60000}
# 2. Convert to query string
query_string = "timestamp=1703012345678&recvWindow=60000"
# 3. Sign with your secret key
signature = hmac.new(secret, query_string, sha256).hexdigest()
# 4. Append signature
final_url = f"{url}?{query_string}&signature={signature}"
# 5. Add API key header
headers = {'X-MBX-APIKEY': api_key}
⚠️ Important Notes
Testnet funds are fake - Use for testing only
SSL verification disabled (ssl=False) - Only for testnet!
Symbol format: BTC/USDT:USDT (with colon for perpetuals)
📄 License
MIT License
