"""
HeX Grid Trading Bot - places buy/sell orders in a price corridor.
Usage: python hex_grid_bot.py
"""

import asyncio
import signal
from py_near.omni_balance import OmniBalance
from py_near.dapps.hex import OrderbookClient

# Configuration
ACCOUNT_ID = "your-account.near"
PRIVATE_KEY = "ed25519:your-private-key-here"

CONFIG = dict(
    base_token="nep245:v2_1.omni.hot.tg:4444119_wyixUKCL",
    quote_token="nep141:usdt.tether-token.near",
    decimal_base=9,
    decimal_quote=6,
    price_low=1.20,
    price_high=1.80,
    grid_levels=5,
    order_amount_usdt=1.0,
    update_interval=60,
)


class GridBot:
    def __init__(self):
        self.running = True
        self.ob = None
        self.omni = None
        signal.signal(signal.SIGINT, lambda *_: setattr(self, "running", False))

    async def get_mid_price(self):
        book = await self.ob.get_orderbook(depth=3)
        if not book.asks or not book.bids:
            return None
        div = 10 ** (CONFIG["decimal_quote"] - CONFIG["decimal_base"])
        return (float(book.asks[0].price) + float(book.bids[0].price)) / 2 / div

    async def cancel_all(self):
        orders = await self.ob.get_orders(limit=100)
        for o in orders:
            if o.order.maker == self.omni.account_id:
                await self.ob.cancel_order(o.hash)
        print(f"Cancelled {len(orders)} orders")

    async def place_grid(self, mid_price):
        await self.cancel_all()
        step = (CONFIG["price_high"] - CONFIG["price_low"]) / (CONFIG["grid_levels"] * 2)

        for i in range(1, CONFIG["grid_levels"] + 1):
            # Buy orders (USDT -> HOT)
            buy_price = mid_price - i * step
            if buy_price >= CONFIG["price_low"]:
                amount = int(CONFIG["order_amount_usdt"] * 10 ** CONFIG["decimal_quote"])
                tx = await self.ob.place_limit_order(
                    price=self.ob.get_price(buy_price),
                    amount=str(amount),
                    token_in=CONFIG["quote_token"],
                )
                print(f"Buy  ${buy_price:.3f}: {tx[:16]}...")

            # Sell orders (HOT -> USDT)
            sell_price = mid_price + i * step
            if sell_price <= CONFIG["price_high"]:
                hot_amount = int(CONFIG["order_amount_usdt"] / sell_price * 10 ** CONFIG["decimal_base"])
                tx = await self.ob.place_limit_order(
                    price=self.ob.get_price(sell_price),
                    amount=str(hot_amount),
                    token_in=CONFIG["base_token"],
                )
                print(f"Sell ${sell_price:.3f}: {tx[:16]}...")

    async def run(self):
        async with OmniBalance(ACCOUNT_ID, PRIVATE_KEY) as omni:
            self.omni = omni
            self.ob = OrderbookClient(
                omni,
                base=CONFIG["base_token"],
                decimal_base=CONFIG["decimal_base"],
            )
            print(f"Grid bot started: ${CONFIG['price_low']} - ${CONFIG['price_high']}")

            last_mid = None
            while self.running:
                try:
                    mid = await self.get_mid_price()
                    if mid is None:
                        await asyncio.sleep(10)
                        continue

                    if mid < CONFIG["price_low"] or mid > CONFIG["price_high"]:
                        print(f"Price ${mid:.3f} out of range")
                        await self.cancel_all()
                    elif last_mid is None or abs(mid - last_mid) / last_mid > 0.02:
                        print(f"Mid price: ${mid:.3f}")
                        await self.place_grid(mid)
                        last_mid = mid

                    await asyncio.sleep(CONFIG["update_interval"])
                except Exception as e:
                    print(f"Error: {e}")
                    await asyncio.sleep(10)

            await self.cancel_all()
            print("Bot stopped")


if __name__ == "__main__":
    asyncio.run(GridBot().run())
