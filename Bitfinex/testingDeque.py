# # Collect trade and orderbook data through websocket from bitfinex

import json
import websockets
import zlib
import datetime
from collections import deque
from db_conn import DatabaseConnector
import time
import asyncio


class BitfinexDataHandler:
    def __init__(self):
        self.connection = DatabaseConnector.connect_to_database()
        self.cursor = self.connection.cursor()
        self.incoming_messages = deque(maxlen=500)

        self.BOOK = {
            'bids': {},
            'asks': {},
            'psnap': {},
            'mcnt': 0
        }

        # Define a lock for thread safety
        self.lock = asyncio.Lock()

    def current_unix_timestamp_ms(self):
        return int(time.time() * 1000)

    def to_signed_32_bit(self, unsigned_checksum):
        if unsigned_checksum > 0x7FFFFFFF:
            return unsigned_checksum - 0x100000000

        return unsigned_checksum

    async def on_open(self, ws):
        self.BOOK['bids'] = {}
        self.BOOK['asks'] = {}
        self.BOOK['psnap'] = {}
        self.BOOK['mcnt'] = 0

        # send websocket conf event with checksum flag
        conf_msg = {'event': 'conf', 'flags': 131072}
        await ws.send(json.dumps(conf_msg))\

        # send subscribe to get desired book updates
        subscribe_msg = {'event': 'subscribe', 'channel': 'book', 'pair': 'tBTCUSD', 'prec': 'P0'}
        await ws.send(json.dumps(subscribe_msg))

    async def on_message(self, ws):
        async for message in ws:
            self.incoming_messages.append(message)

    async def process_messages(self):
        async with self.lock:
            while True:
                # If there are messages in the deque, process one
                if self.incoming_messages:
                    print(len(self.incoming_messages))
                    print(self.incoming_messages)
                    message = self.incoming_messages.popleft()
                    print(message)
                    await self.process_message(message)
                else:
                    # If no messages, yield control to the event loop
                    await asyncio.sleep(0.1)  # Adjust sleep duration as needed

    async def process_message(self, message):
        msg = json.loads(message)
        #print(datetime.datetime.now(), msg)

        if 'event' in msg:
            return
        if msg[1] == 'hb':
            return

        # if msg contains checksum, perform checksum
        if msg[1] == 'cs':
            # print('******* cs:', msg)
            checksum = msg[2]
            csdata = []
            bids_keys = self.BOOK['psnap']['bids']
            asks_keys = self.BOOK['psnap']['asks']

            # collect all bids and asks into an array
            for i in range(25):
                if bids_keys[i]:
                    price = bids_keys[i]
                    pp = self.BOOK['bids'][price]
                    csdata.extend([pp['price'], pp['amount']])
                if asks_keys[i]:
                    price = asks_keys[i]
                    pp = self.BOOK['asks'][price]
                    csdata.extend([pp['price'], -pp['amount']])

            # create string of array to compare with checksum
            cs_str = ':'.join(map(str, csdata))
            print('bids:', sorted(self.BOOK['bids'].keys()))
            print('asks:', sorted(self.BOOK['asks'].keys()))
            cs_str_bytes = cs_str.encode('utf-8')
            cs_calc_unsigned = zlib.crc32(cs_str_bytes)
            cs_calc_signed = self.to_signed_32_bit(cs_calc_unsigned)
            if cs_calc_signed != checksum:
                print('CHECKSUM FAILED', cs_calc_signed, checksum, 'len:', len(csdata))
                # exit(-1) # should not necessarily exit here, problem is usually on the server side (some info arrives
                # after the checksomes are compared)
            else:
                print('Checksum: ' + str(checksum) + ' success!', BOOK['mcnt'], 'len:', len(csdata))
            return

        # handle book. create book or update/delete price points
        if self.BOOK['mcnt'] == 0:  # snapshot
            for pp in msg[1]:
                pp = {'price': pp[0], 'cnt': pp[1], 'amount': pp[2]}
                side = 'bids' if pp['amount'] >= 0 else 'asks'
                pp['amount'] = abs(pp['amount'])
                self.BOOK[side][pp['price']] = pp

            # inserting initial snapshot to sql table


            try:
                bids_data = [(channel_id, data['price'], data['cnt'], data['amount'], 'bid') for channel_id, data in
                             self.BOOK['bids'].items()]
                asks_data = [(channel_id, data['price'], data['cnt'], data['amount'], 'ask') for channel_id, data in
                             self.BOOK['asks'].items()]

                insert_query = "INSERT INTO risklab1.orderBook (channel_id, price, count, amount, side) VALUES (%s, %s, %s, %s, %s)"
                self.cursor.executemany(insert_query, bids_data)
                self.cursor.executemany(insert_query, asks_data)

                self.connection.commit()
            except Exception as e:
                print("Error executing SQL statement:", e)


        else:  # update
            msg = msg[1]
            pp = {'price': msg[0], 'cnt': msg[1], 'amount': msg[2]}

            try:
                self.cursor.execute(
                    "INSERT INTO risklab1.orderBookUpdates (price, count, amount, timestamp) VALUES (%s, %s, %s, %s)",
                    (msg[0], msg[1], msg[2], self.current_unix_timestamp_ms()))
                self.connection.commit()
            except Exception as e:
                print("Error executing SQL statement:", e)

            # if count is zero, then delete price point
            if not pp['cnt']:
                found = True

                if pp['amount'] > 0:
                    if self.BOOK['bids'].get(pp['price']):
                        del self.BOOK['bids'][pp['price']]
                    else:
                        found = False
                elif pp['amount'] < 0:
                    if self.BOOK['asks'].get(pp['price']):
                        del self.BOOK['asks'][pp['price']]
                    else:
                        found = False

                if not found:
                    print('Book delete failed. Price point not found')

                # print('del:', len(BOOK['bids']), len(BOOK['asks']))

            else:
                # else update price point
                side = 'bids' if pp['amount'] >= 0 else 'asks'
                pp['amount'] = abs(pp['amount'])
                self.BOOK[side][pp['price']] = pp

                # print('update:', len(BOOK['bids']), len(BOOK['asks']))

                # save price snapshots. Checksum relies on psnaps!
                for side in ['bids', 'asks']:
                    sbook = self.BOOK[side]
                    bprices = list(sbook.keys())
                    prices = sorted(bprices, key=lambda x: -float(x) if side == 'bids' else float(x))
                    self.BOOK['psnap'][side] = prices

            # print('psnap:', len(BOOK['bids']), len(BOOK['asks'])) # proves that it lists what to remove and add
            # every ~0.2 sec (not real time!)

        self.BOOK['mcnt'] += 1

    async def main(self):
        uri = 'wss://api-pub.bitfinex.com/ws/2'
        async with websockets.connect(uri) as ws:
            await self.on_open(ws)

            # Run tasks concurrently for handling incoming messages and processing
            tasks = [
                asyncio.create_task(self.on_message(ws)),
                asyncio.create_task(self.process_messages())
            ]

            # Wait for both tasks to complete
            await asyncio.gather(*tasks)

    def run(self):
        asyncio.get_event_loop().run_until_complete(self.main())


if __name__ == "__main__":
    handler = BitfinexDataHandler()
    handler.run()
