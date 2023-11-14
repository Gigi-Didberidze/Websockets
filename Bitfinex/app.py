import websocket
import json
import threading

class OrderBook:
    def __init__(self, symbol):
        self.symbol = symbol
        self.order_book = {'bids': {}, 'asks': {}}
        self.initial_snapshot_received = False
        self.stop_event = threading.Event()

    def on_message(self, ws, message):
        data = json.loads(message)
        
        if 'event' in data and data['event'] == 'subscribed':
            print(f"Subscribed to {data['pair']} order book channel")

        if isinstance(data[1][0], list):
            if not self.initial_snapshot_received:
                self.initial_snapshot_received = True
                print(f"Snapshot received for {self.symbol}")

                bids_and_asks = data[1]

                # Format: [price, count, amount]
                for entry in bids_and_asks:
                    price, count, amount = entry
                    price_key = str(price)

                    if amount > 0:
                        self.order_book['bids'][price_key] = amount

                    elif amount < 0:
                        self.order_book['asks'][price_key] = -amount

                self.print_order_book()

            else:
                # This is an update message
                print(f"Update received for {self.symbol}")
                print(f"Update data: {data[1]}")

                price, count, amount = data[1]
                price_key = str(price)

                if count > 0:
                    # Add or update price level
                    if amount > 0:
                        self.order_book['bids'][price_key] = amount
                    elif amount < 0:
                        self.order_book['asks'][price_key] = -amount
                else:
                    # Delete price level
                    if amount == 1:
                        del self.order_book['bids'][price_key]
                    elif amount == -1:
                        del self.order_book['asks'][price_key]

                # Print order book
                self.print_order_book()

    def print_order_book(self):
        print(f"Order Book for {self.symbol}:")
        print("Bids:")
        for price, amount in self.order_book['bids'].items():
            print(f"Price: {price}, Amount: {amount}")

        print("\nAsks:")
        for price, amount in self.order_book['asks'].items():
            print(f"Price: {price}, Amount: {amount}")

    def stop(self):
        print("Stopping the WebSocket thread...")
        self.stop_event.set()

if __name__ == '__main__':
    symbol = 'tBTCUSD'
    ob = OrderBook(symbol)

    ws = websocket.WebSocketApp('wss://api-pub.bitfinex.com/ws/2',
                                on_message=ob.on_message)
    ws.on_open = lambda self: self.send('{ "event": "subscribe", "channel": "book", "symbol": "tBTCUSD"}')

    ws.run_forever()

    ob.stop()
    