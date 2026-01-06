import os
import time
import requests
import math
from decimal import Decimal, ROUND_DOWN
from binance.client import Client
from dotenv import load_dotenv

# Wczytywanie zmiennych z pliku .env (jeśli uruchamiasz lokalnie)
load_dotenv()

# Pobieranie kluczy ze zmiennych środowiskowych
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

# Inicjalizacja klienta Binance Spot
if not API_KEY or not API_SECRET:
    print("❌ BŁĄD: Brak kluczy API! Upewnij się, że plik .env jest poprawny.")
    exit(1)

client = Client(API_KEY, API_SECRET)

SYMBOL = "BTCPLN"  # Para handlowa
MAX_ILOSC_ZLECEN = 100

def round_to_tick(price, tick_size):
    d_price = Decimal(str(price))
    d_tick = Decimal(str(tick_size))
    return float((d_price // d_tick) * d_tick)

def log_message(message):
    """ Zapisuje wiadomości do pliku logbtcpln.txt, dodając je na początku """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    try:
        if os.path.exists("logbtcpln.txt"):
            with open("logbtcpln.txt", "r") as log_file:
                content = log_file.read()
        else:
            content = ""
    except Exception:
        content = ""

    new_content = f"[{timestamp}] {message}\n" + content

    with open("logbtcpln.txt", "w") as log_file:
        log_file.write(new_content)

    print(f"[{timestamp}] {message}")

def synchronize_binance_time():
    """ Synchronizuje czas z giełdą Binance """
    server_time = client.get_server_time()['serverTime']
    local_time = int(time.time() * 1000)
    client.timestamp_offset = server_time - local_time

def get_open_sell_orders():
    """ Pobiera ceny najniższego i najwyższego zlecenia sprzedaży """
    open_orders = client.get_open_orders(symbol=SYMBOL)
    sell_orders = [order for order in open_orders if order["side"] == "SELL"]

    if not sell_orders:
        return None

    # Sort sell orders by price in ascending order
    sell_orders.sort(key=lambda x: float(x["price"]))

    return sell_orders

def buy_btc_for_pln(amount_pln, symbol_name):
    symbol_name = symbol_name.upper()
    price = float(client.get_symbol_ticker(symbol=symbol_name)["price"])
    exchange_info = client.get_symbol_info(symbol_name)

    step_size = 0.0
    tick_size = 0.0
    min_notional = 0.0
    for f in exchange_info["filters"]:
        if f["filterType"] == "LOT_SIZE":
            step_size = float(f["stepSize"])
        if f["filterType"] == "PRICE_FILTER":
            tick_size = float(f["tickSize"])
        if f["filterType"] == "MIN_NOTIONAL":
            min_notional = float(f["minNotional"])

    if amount_pln < min_notional:
        log_message(f"❌ Kwota {amount_pln} PLN jest zbyt niska. Min: {min_notional}")
        return None

    btc_amount = amount_pln / price
    btc_amount = math.floor(btc_amount / step_size) * step_size
    btc_amount_str = "{:.8f}".format(btc_amount).rstrip('0').rstrip('.')

    log_message(f"✅ Kupuję {btc_amount_str} BTC za {amount_pln} PLN")
    order = client.order_market_buy(symbol=symbol_name, quantity=btc_amount_str)

    time.sleep(1)

    avg_price = float(order['cummulativeQuoteQty']) / float(order['executedQty'])
    raw_sell_price = avg_price * 1.01
    sell_price = round_to_tick(raw_sell_price, tick_size)

    sell_quantity = float(order['executedQty']) * 0.999
    sell_quantity = round(sell_quantity, 6)
    sell_quantity_str = format(Decimal(str(sell_quantity)), 'f').rstrip('0').rstrip('.')

    log_message(f"📈 Wystawiam SELL LIMIT: {sell_quantity_str} BTC po {sell_price} PLN")
    sell_order = client.order_limit_sell(
        symbol=symbol_name,
        quantity=sell_quantity_str,
        price=sell_price
    )
    return order, sell_order

def floor_5(value):
    return math.floor(value * 10**5) / 10**5

def get_balance():
    balances = client.get_account()["balances"]
    price = float(client.get_symbol_ticker(symbol=SYMBOL)["price"])

    balancebtc = 0.0
    balancepln = 0.0

    for b in balances:
        if b["asset"] == "BTC":
            balancebtc = (float(b["free"]) + float(b["locked"])) * price
        if b["asset"] == "PLN":
            balancepln = float(b["free"]) + float(b["locked"])

    wielkosc_zlecenia = floor_5((balancebtc + balancepln) / MAX_ILOSC_ZLECEN)
    return balancebtc, balancepln, balancebtc + balancepln, wielkosc_zlecenia

def get_ath():
    klines = client.get_historical_klines(SYMBOL, Client.KLINE_INTERVAL_1WEEK, "8 year ago UTC")
    prices = [float(c[2]) for c in klines]
    return max(prices)

def get_bigest_sell_order():
    open_orders = client.get_open_orders(symbol=SYMBOL)
    sell_orders = [order for order in open_orders if order["side"] == "SELL"]

    if not sell_orders:
        return None, None

    highest_price_sell_order = max(sell_orders, key=lambda order: float(order["price"]))
    return highest_price_sell_order.get("orderId"), highest_price_sell_order.get("origQty")

def cancel_specific_order(symbol, order_id):
    try:
        result = client.cancel_order(symbol=symbol, orderId=order_id)
        log_message(f"✅ Anulowano zlecenie ID: {order_id}")
        return result
    except Exception as e:
        log_message(f"❌ Błąd anulowania {order_id}: {e}")
        return None

def sell_action(symbol, quantity, price):
    sell_order = client.order_limit_sell(
        symbol=symbol,
        quantity=quantity,
        price=price
    )
    log_message(f"✅ Zlecenie SELL złożone: {price}")
    return sell_order

# GŁÓWNA PĘTLA PROGRAMU
while True:
    try:
        log_message("Runing...")
        synchronize_binance_time()

        open_sell_orders = get_open_sell_orders()
        if open_sell_orders and len(open_sell_orders) > 2:
            orders_to_cancel = sorted(open_sell_orders, key=lambda x: float(x['price']), reverse=True)
            while len(orders_to_cancel) > 2:
                order_to_cancel = orders_to_cancel.pop(0)
                cancel_specific_order(SYMBOL, order_to_cancel['orderId'])
                


        balances = get_balance()
        current_pln_balance = balances[1]
        trade_size_pln = balances[3]

        ath = get_ath()
        price_ticker = float(client.get_symbol_ticker(symbol=SYMBOL)["price"])
        
        open_orders_info = get_open_sell_orders()


        if current_pln_balance >= trade_size_pln:
            if open_orders_info is None:
                buy_btc_for_pln(trade_size_pln, SYMBOL)
            else:
                min_order_price = float(open_orders_info[0]['price'])
                # Warunek wejścia (kupujemy jeśli cena spadnie o odpowiedni procent)
                if price_ticker <= min_order_price - ((min_order_price * 0.00125 + (ath * 0.01))):
                    buy_btc_for_pln(trade_size_pln, SYMBOL)
        else:
            # Scenariusz gdy brakuje PLN na koncie - zarządzanie istniejącymi zleceniami
            if open_orders_info is not None:
                min_order_price = float(open_orders_info[0]['price'])
                if price_ticker <= min_order_price - ((min_order_price * 0.00125 + (ath * 0.01))):
                    log_message("Za mały balans PLN - przesuwam najwyższe zlecenie niżej")
                    order_id, quantity = get_bigest_sell_order()
                    if order_id:
                        cancel_specific_order(SYMBOL, order_id)
                        new_sell_price = int(price_ticker + (price_ticker * 0.01))
                        sell_action(SYMBOL, quantity, new_sell_price)

    except Exception as e:
        log_message(f"X Błąd główny: {e}")

    time.sleep(5)
