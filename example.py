"""
Example usage of the Binance Futures Testnet Fix
"""
import asyncio
from exchange_factory import ExchangeFactory
async def main():
    # Replace with your Binance Demo API keys
    # Get them from: https://testnet.binancefuture.com/
    API_KEY = "YOUR_DEMO_API_KEY"
    SECRET = "YOUR_DEMO_SECRET"
    
    # Create patched exchange instance
    exchange = ExchangeFactory.create_binance_demo(API_KEY, SECRET)
    
    # Load markets
    await exchange.load_markets()
    print(f"✅ Loaded {len(exchange.markets)} markets")
    
    # Fetch balance
    balance = await exchange.fetch_balance()
    usdt = balance.get('USDT', {})
    print(f"💰 USDT Balance: {usdt.get('total', 0):.2f}")
    
    # Fetch ticker
    ticker = await exchange.fetch_ticker('BTC/USDT:USDT')
    print(f"📊 BTC Price: ${ticker['last']:,.2f}")
    
    # Fetch positions
    positions = await exchange.fetch_positions()
    print(f"📈 Open Positions: {len([p for p in positions if p['contracts'] != 0])}")
    
    # Place a test order (uncomment to use)
    # order = await exchange.create_order(
    #     symbol='BTC/USDT:USDT',
    #     type='MARKET',
    #     side='BUY',
    #     amount=0.01
    # )
    # print(f"🎯 Order placed: {order['id']}")
if __name__ == "__main__":
    asyncio.run(main())
