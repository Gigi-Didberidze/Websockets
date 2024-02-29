# Collect trade and orderbook data through websocket from bitfinex

import json
import websocket
import zlib
import datetime
from db_conn import connect_to_database
import time


BOOK = {
    'bids': {},
    'asks': {},
    'psnap': {},
    'mcnt': 0
}

def current_unix_timestamp_ms():
    return int(time.time() * 1000)

def to_signed_32_bit(unsiged_checksum):
    if unsiged_checksum > 0x7FFFFFFF:
        return unsiged_checksum - 0x100000000
    return unsiged_checksum


def on_open(ws):
    BOOK['bids'] = {}
    BOOK['asks'] = {}
    BOOK['psnap'] = {}
    BOOK['mcnt'] = 0

    # send websocket conf event with checksum flag
    conf_msg = {'event': 'conf', 'flags': 131072}
    ws.send(json.dumps(conf_msg))

    # send subscribe to get desired book updates
    subscribe_msg = {'event': 'subscribe', 'channel': 'book', 'pair': 'tBTCUSD', 'prec': 'P0'}
    ws.send(json.dumps(subscribe_msg))


def on_message(ws, message):
    msg = json.loads(message)
    print(datetime.datetime.now(), msg)

    if 'event' in msg:
        return
    if msg[1] == 'hb':
        return

    # if msg contains checksum, perform checksum
    if msg[1] == 'cs':
        # print('******* cs:', msg)
        checksum = msg[2]
        csdata = []
        bids_keys = BOOK['psnap']['bids']
        asks_keys = BOOK['psnap']['asks']

        # collect all bids and asks into an array
        for i in range(25):
            if bids_keys[i]:
                price = bids_keys[i]
                pp = BOOK['bids'][price]
                csdata.extend([pp['price'], pp['amount']])
            if asks_keys[i]:
                price = asks_keys[i]
                pp = BOOK['asks'][price]
                csdata.extend([pp['price'], -pp['amount']])

        # create string of array to compare with checksum
        cs_str = ':'.join(map(str, csdata))
        print('bids:', sorted(BOOK['bids'].keys()))
        print('asks:', sorted(BOOK['asks'].keys()))
        cs_str_bytes = cs_str.encode('utf-8')
        cs_calc_unsigned = zlib.crc32(cs_str_bytes)
        cs_calc_signed = to_signed_32_bit(cs_calc_unsigned)
        if cs_calc_signed != checksum:
            print('CHECKSUM FAILED', cs_calc_signed, checksum, 'len:', len(csdata))
            # exit(-1) # should not necessarily exit here, problem is usually on the server side (some info arrives
            # after the checksomes are compared)
        else:
            print('Checksum: ' + str(checksum) + ' success!', BOOK['mcnt'], 'len:', len(csdata))
        return

    # handle book. create book or update/delete price points
    if BOOK['mcnt'] == 0: # snapshot
        for pp in msg[1]:
            pp = {'price': pp[0], 'cnt': pp[1], 'amount': pp[2]}
            side = 'bids' if pp['amount'] >= 0 else 'asks'
            pp['amount'] = abs(pp['amount'])
            BOOK[side][pp['price']] = pp

        # inserting initial snapshot to sql table
        connection = connect_to_database()
        cursor = connection.cursor()

        try:
            for channel_id, data in BOOK['bids'].items():
                cursor.execute("INSERT INTO risklab1.orderBook (channel_id, price, count, amount, side) VALUES (%s, %s, %s, %s, %s)", (channel_id, data['price'], data['cnt'], data['amount'], 'bid'))
                connection.commit()

            for channel_id, data in BOOK['asks'].items():
                cursor.execute("INSERT INTO risklab1.orderBook (channel_id, price, count, amount, side) VALUES (%s, %s, %s, %s, %s)", (channel_id, data['price'], data['cnt'], data['amount'], 'ask'))
                connection.commit()
        except Exception as e:
            print("Error executing SQL statement:", e)

    else: # update
        msg = msg[1]
        connection = connect_to_database()
        cursor = connection.cursor()
        try:
            cursor.execute("INSERT INTO risklab1.orderBookUpdates (price, count, amount, timestamp) VALUES (%s, %s, %s, %s)", (msg[0], msg[1], msg[2], current_unix_timestamp_ms()))
            connection.commit()
        except Exception as e:
            print("Error executing SQL statement:", e)

        pp = {'price': msg[0], 'cnt': msg[1], 'amount': msg[2]}

        # if count is zero, then delete price point
        if not pp['cnt']:
            found = True

            if pp['amount'] > 0:
                if BOOK['bids'].get(pp['price']):
                    del BOOK['bids'][pp['price']]
                else:
                    found = False
            elif pp['amount'] < 0:
                if BOOK['asks'].get(pp['price']):
                    del BOOK['asks'][pp['price']]
                else:
                    found = False

            if not found:
                print('Book delete failed. Price point not found')

            # print('del:', len(BOOK['bids']), len(BOOK['asks']))

        else:
            # else update price point
            side = 'bids' if pp['amount'] >= 0 else 'asks'
            pp['amount'] = abs(pp['amount'])
            BOOK[side][pp['price']] = pp

            # print('update:', len(BOOK['bids']), len(BOOK['asks']))

            # save price snapshots. Checksum relies on psnaps!
            for side in ['bids', 'asks']:
                sbook = BOOK[side]
                bprices = list(sbook.keys())
                prices = sorted(bprices, key=lambda x: -float(x) if side == 'bids' else float(x))
                BOOK['psnap'][side] = prices

        # print('psnap:', len(BOOK['bids']), len(BOOK['asks'])) # proves that it lists what to remove and add
        # every ~0.2 sec (not real time!)

    BOOK['mcnt'] += 1


# create websocket instance
ws = websocket.WebSocketApp('wss://api-pub.bitfinex.com/ws/2', on_open=on_open, on_message=on_message)

# run websocket
ws.run_forever()
