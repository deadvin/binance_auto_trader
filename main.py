
import math
import re
from binance import Client, ThreadedWebsocketManager, ThreadedDepthCacheManager
import pandas as pd
from playsound import playsound
import keys as keys
import time
import zmq


# =======   ZMQ CLIENT

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")

api_key = keys.api_key
api_secret = keys.api_secret
client = Client(api_key, api_secret,  {"verify": True, "timeout": 60})


target_precent = 1.009
stop_precent = 0.988
df_factors = pd.read_pickle('factors')
factors = df_factors.values.tolist()
win = 0
lost = 0
all = 0
first = True
counter = 0
multiplier = 15
scale = 1.3
list_tracking = []
sym_list = []

class symbol:
    def __init__(self, n):

        self.name_short = n
        self.name = n + "USDT"
        self.in_trade = False
        self.target = 0
        self.buy = 0
        self.stop = 0
        self.stop_limit = 0
        self.order_id = 0
        self.win = 0
        self.lose = 0
        self.high = 0
        self.low = 0
        self.price = 0
        self.principle = 0
        self.trade_time = 0

        self.factor_60 = 0
        self.factor_90 = 0
        self.factor_120 = 0
        self.factor_150 = 0
        self.factor_180 = 0

        for l in factors:
            if l[0] == self.name:
                self.factor_60 = (l[1] - 1) * multiplier + 1

        self.factor_90 = (self.factor_60 - 1) * scale + 1
        self.factor_120 = (self.factor_90 - 1) * scale + 1
        self.factor_150 = (self.factor_120 - 1) * scale + 1
        self.factor_180 = (self.factor_150 - 1) * scale + 1

margin_list = ['1INCH', 'ADA', 'ATOM', 'ANKR', 'ALGO', 'AVAX', 'AAVE','AUDIO', 'AR', 'AXS', 'ALICE', 'ANT', 'AGLD', 'BNB',
                'BAT', 'BCH', 'BAKE', 'BNX', 'BICO', 'BETA', 'BLZ', 'COMP','CRV', 'CHZ', 'COTI', 'CHR', 'CAKE', 'C98',
                'CHESS', 'CLV', 'CTXC', 'CELO', 'DASH', 'DOT', 'DOGE', 'DENT', 'DYDX', 'DAR', 'DUSK', 'EOS', 'ETC', 'ENJ',
                'EGLD', 'ENS', 'FTM', 'FIL', 'FET', 'FLOW', 'FTT', 'FLUX', 'GRT', 'GTC', 'GALA', 'GXS', 'HBAR', 'HIVE',
                'HOT', 'IOST', 'IOTA', 'IOTX', 'ICP', 'JASMY', 'KAVA', 'KSM', 'KLAY', 'LINK', 'LTC', 'LRC', 'LINA', 'LUNA',
                'LPT', 'MATIC', 'MANA', 'MDT', 'MIR', 'MASK', 'MBOX', 'MINA', 'NEO', 'NEAR', 'ONT', 'ONE', 'OMG',
                'POLS', 'POND', 'PEOPLE', 'QTUM', 'QUICK', 'RVN', 'ROSE','REEF', 'RAY', 'RNDR', 'SNX', 'SUSHI', 'SAND',
                 'SOL', 'SUPER', 'SLP', 'SHIB', 'SFP', 'TRX','TFUEL', 'THETA', 'TLM', 'TRIBE', 'UNI', 'UNFI', 'VET',
                'VOXEL', 'WAVES', 'WIN', 'WAXP', 'XRP', 'XLM', 'XMR','XTZ', 'XEC', 'YFI', 'YFII', 'YGG', 'ZEC', 'ZIL'
]

for s in margin_list:
    sym_list.append(symbol(s))


def play_short_margin():

    global lost, win, first, counter, in_trade

    all_pairs = client.get_all_tickers()

    counter = counter + 1

    for sym in sym_list:

        cur_price = float(next(item for item in all_pairs if item["symbol"] == sym.name).get('price'))

        if counter > 25 and in_trade < 2 and not sym.in_trade:

            enter_trade = True

            # ===================   CONDITIONS TO ENTER TRADE  =======================
            #
            #
            #
            #
            #
            #
            #


            if enter_trade:

                inf = client.get_symbol_info(sym.name)
                if inf.get('isMarginTradingAllowed'):

                    print("================= ENTER TRADE =================")
                    print(sym.name + " : " + cur_price)
                    playsound('dark.mp3')

                    try:
                        order = client.create_margin_order(
                            symbol=sym.name,
                            side="SELL",
                            type="MARKET",
                            sideEffectType='MARGIN_BUY',
                            quoteOrderQty=12)

                        print(order)

                    except Exception as e:
                        print("======= ERROR SHORTING =======")
                        print(e)
                        break

                    dic = order.get('fills')
                    buy_price = float(dic[0]["price"])
                    print("price after slippage: " + str(buy_price))

                    sym.in_trade = True
                    in_trade += 1
                    print('In Trades: ' + str(in_trade))

                    #   ====================   SET REPAY ORDER

                    details = client.get_margin_loan_details(asset=sym.name_short)
                    dic = details.get('rows')
                    principle = float(dic[0]["principal"])

                    info = client.get_symbol_info(sym.name)
                    precision = float(info['filters'][2]['minQty'])

                    dist = abs(int(math.log10((precision))))
                    sym.principle = round(principle, dist)

                    precision_price = inf['filters'][0]['minPrice']
                    price_filter = abs(int(math.log10((float(precision_price)))))

                    price = round(buy_price * stop_precent, price_filter)

                    print('Sell price: ' + str(price))

                    try:

                        order = client.create_margin_order(
                            symbol=sym.name,
                            side="BUY",
                            type='LIMIT',
                            price=price,
                            quantity=sym.principle,
                            timeInForce='GTC',
                            sideEffectType='AUTO_REPAY',
                        )

                        sym.order_id = order.get('orderId')
                        sym.target = buy_price * target_precent

                    except Exception as e:
                        print("======= ERROR REPAY ORDER =======")
                        print(e)

                        try:
                            order = client.create_margin_order(
                                symbol=sym.name,
                                side="BUY",
                                type='MARKET',
                                quantity=sym.principle,
                                sideEffectType='AUTO_REPAY',
                            )

                        except Exception as e:
                            print("======= ERROR FIX MARKET SELL =======")
                            print(e)

        elif sym.in_trade:  # ==============    IN TRADE

            order = client.get_margin_order(
                symbol=sym.name,
                orderId=sym.order_id)

            if order['status'] == 'FILLED':

                sym.in_trade = False
                in_trade -= 1
                win += 1

                # dic = order.get('fills')
                # buy_price = float(dic[0]["price"])

                print("==========    WIN  ===============")
                print(sym.name)
                print('win ' + str(win))
                print('lose ' + str(lost))

            if cur_price > sym.target:

                result = client.cancel_margin_order(
                    symbol=sym.name,
                    orderId=sym.order_id)

                order = client.create_margin_order(
                    symbol=sym.name,
                    side="BUY",
                    type='MARKET',
                    quantity=sym.principle,
                    sideEffectType='AUTO_REPAY',
                )

                sym.in_trade = False
                in_trade -= 1
                lost += 1

                print("==========    LOSE  ===============")
                print(sym.name)
                print('win ' + str(win))
                print('lose ' + str(lost))

                try:
                    details = client.get_margin_loan_details(asset=sym)
                    dic = details.get('rows')
                    principle = float(dic[0]["principal"])

                    transaction = client.repay_margin_loan(asset=sym.name_short, amount=principle)

                except:
                    print("======= ERROR CLEARING LOAN =======")

def clear_margin(sym):


    details = client.get_margin_loan_details(asset=sym)
    dic = details.get('rows')
    principle = float(dic[0]["principal"])

    info = client.get_symbol_info(sym + "USDT")
    precision = float(info['filters'][2]['minQty'])

    precision_price = info['filters'][0]['minPrice']

    dist = abs(int(math.log10((precision))))
    price_filter = abs(int(math.log10((float(precision_price)))))

    print(str(price_filter))

    order = client.create_margin_order(
                        symbol=sym + "USDT",
                        side="BUY",
                        type='MARKET',
                        quantity=round(principle, dist),
                        sideEffectType='AUTO_REPAY',
                    )

def zmq():

    global list_tracking

    while True:
        message = socket.recv()
        name = str(message)
        name = name[2:]
        name = re.sub("'", '', name)

        if not any(d['name'] == name for d in list_tracking):
            start_time = time.time()
            df_sym = get_klines(name.upper(), 30)
            vol = df_sym.iloc[-1]['vol']
            list_tracking.append({'name': name, "time": start_time, "vol": vol})
            print(name + " " + str(vol))

        socket.send(b"World")

def get_klines(sym,period):

    klines = client.get_historical_klines(sym + "USDT", Client.KLINE_INTERVAL_1MINUTE,"30 min ago UTC")

    df = pd.DataFrame(klines)
    df.columns = ['open_time',
                  'o', 'h', 'l', 'c', 'v',
                  'close_time', 'qav', 'num_trades',
                  'taker_base_vol', 'taker_quote_vol', 'ignore']

    df = df.drop('qav', 1)
    df = df.drop('taker_base_vol', 1)
    df = df.drop('taker_quote_vol', 1)
    df = df.drop('ignore', 1)
    df = df.drop('close_time', 1)

    df["v"] = df["v"].astype(str).astype(float)
    df["c"] = df["c"].astype(str).astype(float)
    df["o"] = df["o"].astype(str).astype(float)
    df["h"] = df["h"].astype(str).astype(float)
    df["l"] = df["l"].astype(str).astype(float)
    df["num_trades"] = df["num_trades"].astype(str).astype(float)

    df['vol'] = df.v.rolling(window=period).mean()

    return df


if __name__ == "__main__":

    while True:
        play_short_margin()
        time.sleep(10)

    t1 = threading.Thread(target=zmq)
    t1.start()

    while True:
        time.sleep(5)

        for s in list_tracking:
            df_sym = get_klines(s.get("name").upper(), 30)

            if df_sym.iloc[-1]['v'] > df_sym.iloc[-1]['vol'] * 3:
                print(s.get("name"))
                print(df_sym.iloc[-1]['vol'])
                print(df_sym.iloc[-1]['v'])
                print('----------------')

            if df_sym.iloc[-1]['div'] - df_btc.iloc[-1]['div'] > s.get("div") + 0.003:
                print(s.get("name").upper())
                print(str(df_sym.iloc[-1]['div'] - df_btc.iloc[-1]['div']))
                print('---------------')

            passed = time.time() - s.get("time")
            if passed//60 > 5:
                list_tracking.remove(s)











































