import bybit
import time
import datetime
import sys
import pandas as pd
import calendar
from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5.QtCore import *

copyOrderList_XRP = []
copyOrderList_ETH = []
copyOrderList_BTC = []

maxBalance = 1000
isFirstLoop_XRP = True
isFirstLoop_ETH = True
isFirstLoop_BTC = True

coinName = ["BTC", "ETH", "XRP"]
coinTicker = ["BTCUSD", "ETHUSD", "XRPUSD"]
leverage = [5, 3, 3]
revenue = [0, 0, 0]
control = "MANUAL"
divine = 0

form_class = uic.loadUiType("SHORT.ui")[0]
client = bybit.bybit(test=False, api_key="CRNPTAOFIQNMCQEREP", api_secret="MJHETUERUADUELHBQLDMOVZZVOKRURDDEQBU")


class Worker(QThread):
    uiRefresh = pyqtSignal()

    def run(self):
        while True:
            try:
                global isFirstLoop_XRP
                global isFirstLoop_ETH
                global isFirstLoop_BTC
                global leverage
                global revenue
                global control
                global divine

                global coinName
                global coinTicker

                self.uiRefresh.emit()


                # print("leverage : ", leverage)
                # print("control : ", control)
                # print("divine : ", divine)

                for i in range(len(coinName)):
                    # print(coinTicker[i], "레버리지 : ", leverage[i], "최소수익률 : ", revenue[i])
                    # print("코인티커 : ", coinTicker[i])
                    wallet = self.get_MyWallet(coinName[i])
                    # print(coinTicker[i], " wallet : ", wallet)

                    importance = self.get_Importance(wallet)

                    if coinName[i] == "BTC":
                        if isFirstLoop_BTC:
                            print(coinName[i], " importance : ", importance, " SHORT SHORT SHORT SHORT SHORT SHORT SHORT SHORT SHORT")
                            isFirstLoop_BTC = False
                            if importance >= 25:
                                print(coinTicker[i], "비중이 25%를 넘었다")
                                self.set_FirstOnlyOrderListInit(coinTicker[i])

                    if importance == 0:
                        candle_data = self.get_ohlcv(coinTicker[i], "1")
                    else:
                        candle_data = self.get_ohlcv(coinTicker[i], "1")

                    df = pd.DataFrame(candle_data)
                    df = df['close'].astype(float)
                    # print("df : ", df)
                    # print("df 마지막 : ", df.loc[199])
                    currentPrice = df.loc[199]

                    # RSI 계산
                    def rsi(ohlc: pd.DataFrame, period: int = 14):
                        delta = ohlc.diff()

                        up, down = delta.copy(), delta.copy()
                        up[up < 0] = 0
                        down[down > 0] = 0

                        _gain = up.ewm(com=(period - 1), min_periods=period).mean()
                        _loss = down.abs().ewm(com=(period - 1), min_periods=period).mean()

                        RS = _gain / _loss
                        return pd.Series(100 - (100 / (1 + RS)), name="RSI")

                    rsi = round(rsi(df, 14).iloc[-1], 4)
                    # print(coinTicker[i], " rsi : ", rsi)
                    #
                    # print("importance : ", importance)

                    if importance == 0:
                        # 아직 포지션이 없는 상태
                        # RSI조건에 맞으면 매수하려고 대기중
                        if float(rsi) >= 70:
                            print("RSI 걸림")
                            self.buy_FirstCoin(wallet, coinTicker[i], leverage[i])
                            # 포지션을 잡은 최초에만 포지션을 기준으로 거미줄 매수 예약
                            self.set_SpiderLine(wallet, 0, coinTicker[i], leverage[i], True)

                    elif importance > 0:
                        # 포지션이 있는 상태
                        # 1.거미줄을 넘기고 더 내려간 경우
                        #   - 시장가보다 -1% 구간에서 다시 거미줄 매수 예약
                        # 2.거미줄중간에 올라간 경우
                        #   - 매수된 거미줄이 있는지 체크하고 만약 있다면 해당 거미줄의 목표 매도가에 매도 예약
                        # 3. 거미줄보다 위로 올라간 경우
                        #   - 거미줄이 있는지 체크하고 없다면 거미줄을 전부 리셋하고(만약 거미줄 매도예약이 걸려있으면 그건 제외) 평단가 위라면 평단가 -1%부터 거미줄 매수 예약
                        # 4. 거미줄 중간에서 횡보하는 경우
                        #   -

                        # 비중이 25% 이하인 경우 20%구간에서 반매도, 나머지는 RSI70 이상에서 전부 매도
                        # 비중이 25% 이상인 경우 평단가에서 비중 25% 남기고 전부 매도

                        if float(wallet['order_margin']) == 0:
                            # 1.거미줄을 넘기고 더 내려간 경우
                            # 매수 주문이 없을때 추가로 거미줄세팅
                            if importance < 50:
                                print("새로운 거미줄 importance : ", importance)
                                if currentPrice > float(self.get_AverageUnitPrice(coinTicker[i])):
                                    self.set_SpiderLine(wallet, currentPrice, coinTicker[i], leverage[i], False)
                                else:
                                    self.set_SpiderLine(wallet, 0, coinTicker[i], leverage[i], False)

                        # 2.거미줄중간에 올라간 경우
                        # isAnyEnd = self.check_SpiderLine(currentPrice, coinTicker[i])
                        #
                        # # isAnyEnd가 True일 경우 모든 매수예약을 취소하고 시장가 기준 -1%부터 새로 거미줄 매수 예약
                        # if isAnyEnd:
                        #     if currentPrice > float(self.get_AverageUnitPrice(coinTicker[i])):
                        #         print("isAnyEnd가 True일 경우 모든 매수예약을 취소하고 시장가 기준 -1%부터 새로 거미줄 매수 예약")
                        #         self.cancle_BuyReserve(coinTicker[i])
                        #         self.set_SpiderLine(wallet, currentPrice, coinTicker[i], False)

                        # 3. 거미줄보다 위로 올라간 경우
                        # 현재 수익률 체크가 필요함
                        # if self.get_RevenuePercent(currentPrice) >= 20:
                        #     print("수익률이 20%이상이다. 반매도할까?")
                        #     myPosition = self.get_MyPosition()
                        #     qty = myPosition["size"]
                        #     client.Order.Order_new(side="Sell", symbol="XRPUSD", order_type="Market", qty=qty, time_in_force="GoodTillCancel").result()
                        # print(coinTicker[i], " 수익률 : ", self.get_RevenuePercent(currentPrice, coinTicker[i], 5))
                        # RSI가 30보다 작을 경우 전포지션 매도
                        # print(coinTicker[i], " 수익률 : ",
                        #       self.get_RevenuePercent(currentPrice, coinTicker[i], leverage[i]))
                        if rsi <= 30:
                            if self.get_Side(coinTicker[i]) == "BUY":
                                if importance >= 40:
                                    print(coinTicker[i], " 수익률 : ",
                                          self.get_RevenuePercent(currentPrice, coinTicker[i], leverage[i]))
                                    myPosition = self.get_MyPosition(coinTicker[i])
                                    qty = myPosition["size"]
                                    client.Order.Order_new(side="Buy", symbol=coinTicker[i], order_type="Market", qty=qty,
                                                           time_in_force="GoodTillCancel").result()
                                    self.cancle_BuyReserve(coinTicker[i])
                                else:
                                    if float(self.get_RevenuePercent(currentPrice, coinTicker[i], leverage[i])) >= float(leverage[i]):
                                        print(coinTicker[i], " 수익률 : ",
                                                  self.get_RevenuePercent(currentPrice, coinTicker[i], leverage[i]))
                                        myPosition = self.get_MyPosition(coinTicker[i])
                                        qty = myPosition["size"]
                                        client.Order.Order_new(side="Buy", symbol=coinTicker[i], order_type="Market",
                                                               qty=qty,
                                                               time_in_force="GoodTillCancel").result()
                                        self.cancle_BuyReserve(coinTicker[i])
                    time.sleep(0.5)

            except:
                print('run error :', sys.exc_info()[0])

    def check_SpiderGap(self, coinTicker):
        aPrice = float(self.get_AverageUnitPrice(coinTicker))
        activeOrder = self.get_ActiveOrder(coinTicker)

        aPrice = aPrice + (aPrice * 0.015)

        count = 0
        for order in activeOrder:
            if float(order['price']) > aPrice:
                count += 1
        # print(coinTicker, "aPrice : ", aPrice, "count : ", count)

        if count < 5:
            return False
        else:
            return True

    def manual_BuyFirstCoin(self):
        global control

        if control == "MANUAL":
            print("수동으로 코인 매수")

    def manual_AllCoin(self):
        global control

        if control == "MANUAL":
            print("모든 코인 청산")



    def buy_FirstCoin(self, walletData, coinTicker, leverage):
        # RSI가 조건에 맞을때 최초로 한번만 사는곳
        # 거미줄매수는 다른 곳에서 관리
        try:
            print(coinTicker, " walletData : ", walletData)
            # walletData = walletData[0]['result']
            # walletData = walletData['XRP']

            # available = float(walletData['available_balance'])
            usedMargin = float(walletData['used_margin'])
            orderQty = self.get_TradeQty(walletData, 20, int(leverage), coinTicker)
            print("orderQty : ", orderQty)

            if usedMargin <= 0:
                # 시장가 매수
                client.Order.Order_new(side="Sell", symbol=coinTicker, order_type="Market", qty=orderQty,
                                       time_in_force="GoodTillCancel").result()
                print(coinTicker, " 구매")
        except:
            print('buy_FirstCoin error :', sys.exc_info()[0])

    def check_CopyOrderList(self, coinTicker):
        try:
            global copyOrderList_XRP
            global copyOrderList_ETH
            global copyOrderList_BTC

            if coinTicker == "XRPUSD":
                tempList = []
                if copyOrderList_XRP:
                    for order in copyOrderList_XRP:
                        if order['status'] == 'RESERVE_SELL':
                            tempList.append(order)

                copyOrderList_XRP = []
                copyOrderList_XRP = tempList.copy()

            elif coinTicker == "ETHUSD":
                tempList = []
                if copyOrderList_ETH:
                    for order in copyOrderList_ETH:
                        if order['status'] == 'RESERVE_SELL':
                            tempList.append(order)

                copyOrderList_ETH = []
                copyOrderList_ETH = tempList.copy()

            elif coinTicker == "BTCUSD":
                tempList = []
                if copyOrderList_BTC:
                    for order in copyOrderList_BTC:
                        if order['status'] == 'RESERVE_SELL':
                            tempList.append(order)

                copyOrderList_BTC = []
                copyOrderList_BTC = tempList.copy()
            else:
                print("check_CopyOrderList 티커가 잘못들어왔다!!")

        except:
            print('check_CopyOrderList error :', sys.exc_info()[0])

    def set_SpiderLine(self, wallet, currentPrice, coinTicker, leverage, isFirst):
        try:
            global copyOrderList_XRP
            global copyOrderList_ETH
            global copyOrderList_BTC

            print("wallet : ", wallet)
            print("currentPrice : ", currentPrice)
            print("coinTicker : ", coinTicker)

            # currentPrice(현재가)가 넘어오지 않은 경우 평단가를 기준으로 거미줄 매수 예약
            order_margin = wallet['order_margin']
            if float(order_margin) <= 0:
                if currentPrice == 0:
                    # 평단가를 구함
                    entryPrice = self.get_AverageUnitPrice(coinTicker)
                else:
                    entryPrice = float(currentPrice)

                entryPrice = round(float(entryPrice), 4)
                print("entryPrice : ", entryPrice)

                # 한번에 매수할 수량을 구함
                orderQty = self.get_TradeQty(wallet, 20, int(leverage), coinTicker)
                print("거미줄 orderQty : ", orderQty)

                # copyOrderList = []
                self.check_CopyOrderList(coinTicker)

                for i in range(5):
                    if i == 0 and isFirst:
                        price = float(entryPrice) + (float(entryPrice) * (0.005 * (i + 1)))
                    elif i == 1 and isFirst:
                        price = float(entryPrice) + (float(entryPrice) * (0.01 * (i + 1))) - (
                                    float(entryPrice) * (0.005 * (i + 1)))
                    elif isFirst:
                        price = float(entryPrice) + (float(entryPrice) * (0.01 * i))
                    else:
                        price = float(entryPrice) + (float(entryPrice) * (0.01 * (i + 1)))
                    price = round(price, 4)
                    print("price : ", price)
                    client.Order.Order_new(side="Sell", symbol=coinTicker, order_type="Limit", qty=orderQty, price=price,
                                           time_in_force="GoodTillCancel").result()
                    time.sleep(0.3)

                    # 현재 들어가 있는 시드대비 비중을 구함
                    importance = self.get_Importance(wallet)

                    # 비중 25% 이상부터 매도준비 배열을 만듬
                    if importance >= 25:
                        od = {}
                        od['qty'] = orderQty
                        od['price'] = price
                        if i == 0 and isFirst:
                            aimPrice = price - (price * 0.005)
                        else:
                            aimPrice = price - (price * 0.01)
                        aimPrice = round(aimPrice, 4)
                        od['aimPrice'] = aimPrice
                        od['status'] = "RESERVE_BUY"
                        if coinTicker == "XRPUSD":
                            copyOrderList_XRP.append(od)
                        elif coinTicker == "ETHUSD":
                            copyOrderList_ETH.append(od)
                        elif coinTicker == "BTCUSD":
                            copyOrderList_BTC.append(od)
                        else:
                            print("coinTicker : ", coinTicker, "set_SpiderLine 티커가 잘못들어왔다!!")

                if coinTicker == "XRPUSD":
                    print("새로운 거미줄 세팅 copyOrderList_XRP : ", copyOrderList_XRP)
                elif coinTicker == "ETHUSD":
                    print("새로운 거미줄 세팅 copyOrderList_ETH : ", copyOrderList_ETH)
                elif coinTicker == "BTCUSD":
                    print("새로운 거미줄 세팅 copyOrderList_BTC : ", copyOrderList_BTC)
                else:
                    print("set_SpiderLine 2222222  티커가 잘못들어왔다!!")

            # time.sleep(0.5)
        except:
            print('set_SpiderLine error :', sys.exc_info()[0])

    def set_FirstOnlyOrderListInit(self, coinTicker):
        try:
            global copyOrderList_XRP
            global copyOrderList_ETH
            global copyOrderList_BTC

            activeOrder = self.get_ActiveOrder(coinTicker)
            copyOrderList_XRP = []
            for order in activeOrder:
                od = {}
                od['qty'] = order['qty']
                od['price'] = order['price']
                od['aimPrice'] = float(order['price']) - (float(order['price']) * 0.01)
                od['aimPrice'] = round(od['aimPrice'], 4)
                od['status'] = "RESERVE_BUY"

                if coinTicker == "XRPUSD":
                    copyOrderList_XRP.append(od)
                elif coinTicker == "ETHUSD":
                    copyOrderList_ETH.append(od)
                elif coinTicker == "BTCUSD":
                    copyOrderList_BTC.append(od)
                else:
                    print("coinTicker : ", coinTicker, " set_SpiderLine 티커가 잘못들어왔다!!")

            if coinTicker == "XRPUSD":
                print("맨처음 거미줄 세팅 copyOrderList_XRP : ", copyOrderList_XRP)
            elif coinTicker == "ETHUSD":
                print("맨처음 거미줄 세팅 copyOrderList_ETH : ", copyOrderList_ETH)
            elif coinTicker == "BTCUSD":
                print("맨처음 거미줄 세팅 copyOrderList_BTC : ", copyOrderList_BTC)
            else:
                print("set_FirstOnlyOrderListInit 2222222  티커가 잘못들어왔다!!")
        except:
            print('set_FirstOnlyOrderListInit error :', sys.exc_info()[0])

    def check_SpiderLine(self, cPrice, coinTicker):
        # 포지션이 있는 상태
        # 1.거미줄중간에 올라간 경우
        #   - 매수된 거미줄이 있는지 체크하고 만약 있다면 해당 거미줄의 목표 매도가에 매도 예약
        # 2.거미줄을 넘기고 더 내려간 경우
        #   - 시장가보다 -1% 구간에서 다시 거미줄 매수 예약
        # 3. 거미줄보다 위로 올라간 경우
        #   - 거미줄이 있는지 체크하고 없다면 거미줄을 전부 리셋하고(만약 거미줄 매도예약이 걸려있으면 그건 제외) 평단가 위라면 평단가 -1%부터 거미줄 매수 예약
        # 4. 거미줄 중간에서 횡보하는 경우
        #   -
        try:
            # 시장가를 거미줄 배열과 비교해서 매수된 경우 목표가에 매도를 걸어놓는다.
            global copyOrderList_XRP
            global copyOrderList_ETH
            global copyOrderList_BTC

            currentPrice = float(cPrice)
            isAnyEnd = False

            if coinTicker == "BTCUSD":
                for list in copyOrderList_BTC:
                    # 거미줄로 산 가격
                    orderPrice = float(list['price'])
                    aimPrice = float(list['aimPrice'])

                    if currentPrice >= orderPrice:
                        if list['status'] == "RESERVE_BUY":
                            print(coinTicker, "SHORT  거미줄 매수")
                            list['status'] = "BUYED"
                    # print("copyOrderList_BTC 2222222222222: ", copyOrderList_BTC)
                    # 1.거미줄중간에 내려간 경우
                    #   - 매수된 거미줄이 있는지 체크하고 만약 있다면 해당 거미줄의 목표 매도가에 매도 예약
                    # if list['status'] == "BUYED":
                    #     print("거미줄 순환 매도에 들어왔다 LONG LONG LONG LONG")
                    #     orderQty = float(list['qty'])
                    #     client.Order.Order_new(side="Buy", symbol=coinTicker, order_type="Limit", qty=orderQty,
                    #                            price=aimPrice, time_in_force="GoodTillCancel").result()
                    #     list['status'] = "RESERVE_SELL"
                    #     print("순환매도에 들어옴 copyOrderList_BTC 11111111111: ", copyOrderList_BTC)
                    #
                    # if currentPrice <= aimPrice:
                    #     if list['status'] == "RESERVE_SELL":
                    #         list['status'] = "END"
                    #         isAnyEnd = True
                    #         print("스테이터스를 엔드로바꿈 copyOrderList_BTC 2222222222222: ", copyOrderList_BTC)

                # 시장가를 추적하여 매도 건 가격으로 팔린경우 list['status'] = "END"로 변경
                # copyOrderList_BTC list['status'] = "END"가 하나라도 있는경우 거미줄예약을 전부 리셋하고 시장가대비 -1%부터 거미줄을 다시친다.
            else:
                print("coinTicker : ", coinTicker, " set_SpiderLine 티커가 잘못들어왔다!!")

            return isAnyEnd

        except:
            print('check_SpiderLine error :', sys.exc_info()[0])

    def get_CurrentPrice(self, coinTicker):
        try:
            coinInfo = client.Market.Market_symbolInfo(symbol=coinTicker).result()
            coinInfo = coinInfo[0]['result']
            # print("market : ", coinInfo)
            lastPrice = coinInfo[0]['last_price']
            return lastPrice
        except:
            print('get_CurrentPrice error :', sys.exc_info()[0])

    def get_Importance(self, walletData):
        try:
            global maxBalance
            # 현재 실려 있는 비중을 구한다.
            # 포지션
            # wallet = self.get_MyWallet("XRP")
            total = float(walletData['wallet_balance'])
            if total > float(maxBalance):
                total = float(maxBalance)
            use = float(walletData['used_margin']) - float(walletData['order_margin'])
            imp_Percent = use / total * 100
            imp_Percent = round(imp_Percent, 0)
            # print("imp_Percent : ", imp_Percent, "order_margin : ", walletData['order_margin'])
            return imp_Percent
        except:
            print('get_Importance error :', sys.exc_info()[0])

    def get_TradeQty(self, walletData, divisionCount, lever, coinTicker):
        try:
            # 511.4538
            # 0.0145를 곱해준다
            # 504
            # 7.4538
            # 주문 갯수 : ((토탈 갯수 - 토탈갯수 * 0.0145) / divisionCount) * leverage)
            leverage = lever
            division = divisionCount

            walletBalance = float(walletData['wallet_balance'])
            print(coinTicker, " walletBalance : ", walletBalance)
            if walletBalance > maxBalance:
                walletBalance = maxBalance
            walletBalanceMinus = walletBalance * 0.015

            orderQty = walletBalance - walletBalanceMinus
            print(coinTicker, " orderQty : ", orderQty, " division : ", division, " leverage : ", leverage)
            orderQty = (orderQty / division) * leverage

            print(coinTicker, " orderQty1111 : ", orderQty)

            currentMarketPrice = self.get_CurrentPrice(coinTicker)
            orderQty = orderQty * float(currentMarketPrice)
            orderQty = round(orderQty, 0)
            orderQty = int(orderQty)
            print(coinTicker, " orderQty2222 : ", orderQty)
            return orderQty
        except:
            print('get_TradeQty error :', sys.exc_info()[0])

    def get_RevenuePercent(self, currentPrice, coinTicker, leverage):
        try:
            percent = 0
            # (오르거나 떨어진 현재 주식 가격 / 내가 매수한 주식 가격) * 100 - 100
            # (현대 가격 - 내가산가격) / 내가산가격
            averageUnitPrice = self.get_AverageUnitPrice(coinTicker)
            percent = (float(averageUnitPrice) / float(currentPrice)) * 100 - 100
            percent = round(percent, 2) * float(leverage)
            # print(coinTicker, '평단가:', averageUnitPrice, '현재가 : ', currentPrice, ' 수익률 : ', percent)
            return percent
        except:
            print('get_RevenuePercent error :', sys.exc_info()[0])

            3553.4 -3.45

    def get_AverageUnitPrice(self, coinTicker):
        try:
            position = client.Positions.Positions_myPosition(symbol=coinTicker).result()
            position = position[0]['result']
            # print("position : ", position)
            entryPrice = position['entry_price']
            return entryPrice
        except:
            print('get_AverageUnitPrice error :', sys.exc_info()[0])

    def cancle_BuyReserve(self, coinTicker):
        # 거미줄로 걸려 있는 모든 매수 예약을 취소한다.
        try:
            activeOrder = self.get_ActiveOrder(coinTicker)

            for order in activeOrder:
                if order['side'] == 'Sell':
                    client.Order.Order_cancel(symbol=coinTicker, order_id=order['order_id']).result()
        except:
            print('cancle_BuyReserve error :', sys.exc_info()[0])

    def get_Side(self, coinTicker):
        try:
            order = client.Market.Market_orderbook(symbol=coinTicker).result()
            order = order[0]["result"]
            l_Buy = []
            l_Sell = []
            for o in order:
                if o['side'] == 'Buy':
                    l_Buy.append(o)
                elif o['side'] == 'Sell':
                    l_Sell.append(o)
            buySize = int(l_Buy[0]['size'])
            sellSize = int(l_Sell[0]['size'])

            side = 'NA'

            if buySize > sellSize:
                side = 'BUY'
            elif buySize < sellSize:
                side = 'SELL'

            return side
        except:
            print('get_Side error :', sys.exc_info()[0])

    def get_MyWallet(self, coinName):
        try:
            # print("coinName : ", coinName)
            wallet = client.Wallet.Wallet_getBalance(coin=coinName).result()
            # print("wallet: ", wallet)
            wallet = wallet[0]['result']
            wallet = wallet[coinName]
            return wallet
        except:
            print('get_MyWallet error :', sys.exc_info()[0])

    def get_MyPosition(self, coinTicker):
        try:
            position = client.Positions.Positions_myPosition(symbol=coinTicker).result()
            position = position[0]['result']
            return position
        except:
            print('get_MyPosition error :', sys.exc_info()[0])

    def get_ActiveOrder(self, coinTicker):
        try:
            activeOrder = client.Order.Order_getOrders(symbol=coinTicker, order_status="New").result()
            # activeOrder = order = client.Order.Order_query(symbol="XRPUSD", order_id="").result()
            print("activeOrder `========================", activeOrder)
            activeOrder = activeOrder[0]['result']
            activeOrder = activeOrder['data']
            rOrder = []

            for ao in activeOrder:
                dic = {}
                dic['symbol'] = ao['symbol']
                dic['side'] = ao['side']
                dic['price'] = ao['price']
                dic['qty'] = ao['qty']
                dic['order_id'] = ao['order_id']
                rOrder.append(dic)
            return rOrder
        except:
            print('get_ActiveOrder error :', sys.exc_info()[0])

    def get_ohlcv(self, symbol, interval, end_str=None):
        try:
            """Get Historical Klines from Bybit

            See dateparse docs for valid start and end string formats http://dateparser.readthedocs.io/en/latest/

            If using offset strings for dates add "UTC" to date string e.g. "now UTC", "11 hours ago UTC"

            :param symbol: Name of symbol pair -- BTCUSD, ETCUSD, EOSUSD, XRPUSD
            :type symbol: str
            :param interval: Bybit Kline interval -- 1 3 5 15 30 60 120 240 360 720 "D" "M" "W" "Y"
            :type interval: str
            :param start_str: Start date string in UTC format
            :type start_str: str
            :param end_str: optional - end date string in UTC format
            :type end_str: str

            :return: list of OHLCV values

            """
            # set parameters for kline()
            timeframe = str(interval)
            limit = 200
            start_ts = int(datetime.datetime.now().timestamp())
            start_ts -= int(interval) * 60 * 200

            end_ts = None

            # init our list
            output_data = []
            # it can be difficult to know when a symbol was listed on Binance so allow start time to be before list date
            symbol_existed = False
            temp_dict = client.Kline.Kline_get(symbol=symbol, interval=timeframe, limit=200,
                                               **{'from': start_ts}).result()

            if not symbol_existed and len(temp_dict):
                symbol_existed = True

            if symbol_existed:
                temp_data = temp_dict[0]['result']
                output_data += temp_data
            return output_data
        except:
            print('get_ohlcv error :', sys.exc_info()[0])





class MyWindow(QMainWindow, form_class):

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # self.initUpbit()
        # self.checkMyBalance()

        # timer = QTimer(self)
        # timer.start(1000)
        # timer.timeout.connect(self.test)

        self.worker = Worker()
        self.worker.uiRefresh.connect(self.refreshUI)
        self.Short_Buy.clicked.connect(self.worker.manual_BuyFirstCoin)
        self.Short_Sell.clicked.connect(self.worker.manual_AllCoin)

        # self.worker.sellfinished.connect(self.refreshSellCoin)
        self.worker.start()

    @pyqtSlot()
    def refreshUI(self):
        try:
            global leverage
            global revenue
            global control
            global divine

            # leverage = self.Leverage.toPlainText().split(',')
            # revenue = self.Revenue.toPlainText().split(',')
            # divine = self.Divine.toPlainText()
            # control = self.TMethod.currentText()

        except:
            print('refreshUI error :', sys.exc_info()[0])


app = QApplication(sys.argv)
window = MyWindow()
window.show()
app.exec_()


