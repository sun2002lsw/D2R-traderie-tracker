class Appraiser:
    def __init__(self) -> None:
        self._itemValuesQueue = None
        self._itemValues = None

    # 아이템 가치 감별 전체 작업
    def appraise(self, tradeHistorys):
        self._itemValuesQueue = {}
        self._itemValues = {'Perfect Amethyst': 1}  # 모든 아이템 가치의 기준은 퍼자

        # OR 묶음이 있으면 감별하기 너무 힘들다... 깔끔한 거래만 취급하자
        # 기껏 수집한 데이터 날려버리는게 아깝지만, 계산할 능력이 없다
        simpleTradeHistorys = {}
        for itemName, tradeHistory in tradeHistorys.items():
            simpleTradeHistorys[itemName] = []

            for trade in tradeHistory:
                tradeItemPackages = trade['tradeItemPackages']
                if len(tradeItemPackages) != 1:
                    continue  # OR 묶음이 있는 거래

                # 가끔씩 아이템을 동일 아이템에 파는 이상한 거래가 있다
                # 그런 것도 없애주자
                tradeItemPackage = tradeItemPackages[0]
                invalidTrade = False
                for tradeItem in tradeItemPackage:
                    tradeItemName = tradeItem[1]
                    if tradeItemName == itemName:
                        invalidTrade = True
                        break
                if invalidTrade:
                    continue  # 동일 아이템 거래

                # 구매 물품 구성이 깔끔한 거래
                tradeCnt = trade['tradeCnt']
                oneTrade = {'tradeCnt': tradeCnt, 'tradeItemPackage': tradeItemPackage}
                simpleTradeHistorys[itemName].append(oneTrade)

        # 계속 전체 거래를 순회하면서 계산할거 어디 없나 찾아본다
        while True:
            calc, keep = self._splitSimpleTradeHistorys(simpleTradeHistorys)

            # 계산 가능한 거래 내역에 대하여, 계산된 가치 값을 큐에 추가
            self._calcSimpleTradeHistorys(calc)
            if self._nothingToAppraise():
                break  # 더 이상 계산할 항목이 없다

            # 유망한 가치 큐를 선택하여 아이템 가치를 확정
            self._appraisePromisingItemValueQueue()

            # 새로운 아이템이 가치 확정되었으니,
            # 기존에 계산 못 했던 거래 항목이 계산 가능하겠지. 다시 돌려보자
            simpleTradeHistorys = keep

        # 감별에 활용된 거래 내역과 아이템 가치를 반환
        return self._itemValues

    # 거래의 종류를 2가지로 나눈다
    # 1. 한 종류의 아이템 빼고 나머지 모든 아이템의 가치를 안다. 
    #   ex) 베르 -> (로, 말, 2이스트): 베르룬, 로룬, 말룬의 가치를 알면 이스트룬의 가치를 계산
    # 2. 두 종류 이상의 아이템 가치를 모른다
    #   일단은 킵해둔다. 나중에 다시 살펴보자
    def _splitSimpleTradeHistorys(self, simpleTradeHistorys):
        calculateTradeHistorys = {}
        keepTradeHistorys = {}

        for itemName, simpleTradeHistory in simpleTradeHistorys.items():
            calculateTradeHistorys[itemName] = []
            keepTradeHistorys[itemName] = []

            for trade in simpleTradeHistory:
                tradeItemPackage = trade['tradeItemPackage']

                unknownValueCnt = 0 if itemName in self._itemValues else 1
                for tradeItem in tradeItemPackage:
                    tradeItemName = tradeItem[1]
                    unknownValueCnt += 0 if tradeItemName in self._itemValues else 1

                if unknownValueCnt == 0:
                    raise ValueError('모든 아이템의 가치를 아는 거래 항목이 있을 수 없음')
                elif unknownValueCnt == 1:
                    calculateTradeHistorys[itemName].append(trade)
                else:
                    keepTradeHistorys[itemName].append(trade)

        return calculateTradeHistorys, keepTradeHistorys

    # 한 종류의 아이템 빼고 나머지 모든 아이템의 가치를 아는 경우에 대하여
    def _calcSimpleTradeHistorys(self, simpleTradeHistorys):
        for itemName, simpleTradeHistory in simpleTradeHistorys.items():

            # 구매한 아이템들을 기반으로 판매 아이템의 가치를 감별하는 경우
            if itemName not in self._itemValues:
                for trade in simpleTradeHistory:
                    tradeCnt = trade['tradeCnt']
                    tradeItemPackage = trade['tradeItemPackage']

                    itemTotalValue = 0
                    for tradeItem in tradeItemPackage:
                        tradeItemCnt = tradeItem[0]
                        tradeItemName = tradeItem[1]
                        tradeItemValue = self._itemValues[tradeItemName]
                        itemTotalValue += tradeItemCnt * tradeItemValue

                    itemValue = itemTotalValue / tradeCnt
                    self._addItemValueQueue(itemName, itemValue)

            # 구매 아이템들중 한 아이템을 빼고 나머지의 모든 가치를 아는 경우
            else:
                for trade in simpleTradeHistory:
                    tradeCnt = trade['tradeCnt']
                    tradeItemPackage = trade['tradeItemPackage']

                    # 모르는 한 아이템 빼고 정리하여, 그 한 종류의 가치가 얼마인가
                    # ex) 베르 -> (로, 말, 2이스트): 이스트 가치는 (베르 - 로 - 말) / 2
                    targetItemTotalValue = tradeCnt * self._itemValues[itemName]
                    for tradeItem in tradeItemPackage:
                        tradeItemCnt = tradeItem[0]
                        tradeItemName = tradeItem[1]
                        if tradeItemName in self._itemValues:
                            targetItemTotalValue -= tradeItemCnt * self._itemValues[tradeItemName]
                        else:
                            targetItem = tradeItem  # 가치를 모르는 그 아이템

                    targetItemCnt = targetItem[0]
                    targetItemName = targetItem[1]
                    targetItemValue = targetItemTotalValue / targetItemCnt

                    # 말도 안 되게 손해보는 거래. 허위 매물로 걸러내자
                    if targetItemValue < 0:
                        continue

                    self._addItemValueQueue(targetItemName, targetItemValue)

    def _addItemValueQueue(self, itemName, value):
        if itemName not in self._itemValuesQueue:
            self._itemValuesQueue[itemName] = []

        self._itemValuesQueue[itemName].append(value)

    def _nothingToAppraise(self):
        for queue in self._itemValuesQueue.values():
            if len(queue) > 0:
                return False

        return True

    # 각 아이템의 가치 내역에 대하여, 
    # 가장 많은 가치 내역을 가진 항목을 선정하여
    # 허위 의심 거래 항목은 제외하고 가치를 지정
    def _appraisePromisingItemValueQueue(self):
        longestQueueLen = 0
        for itemName, valueQueue in self._itemValuesQueue.items():
            if len(valueQueue) > 0 and itemName in self._itemValues:
                raise ValueError('가치가 정해진 아이템이 가치 내역을 가지는건 구현 오류')

            if len(valueQueue) > longestQueueLen:
                targetItemName = itemName
                longestQueueLen = len(valueQueue)

        valueQueue = self._itemValuesQueue[targetItemName]
        valueQueueLen = len(valueQueue)

        # 아이템 가치 내역의 상위/하위 10%는 허위 매물로 보고 삭제하자
        invalidTradeCnt = round(valueQueueLen * 0.1)
        beginIdx = invalidTradeCnt
        endIdx = valueQueueLen - invalidTradeCnt

        valueQueue.sort()
        valueQueue = valueQueue[beginIdx:endIdx]
        valueQueueLen = len(valueQueue)

        # 아이템의 가치 결정. 가치가 정해진 아이템은 가치 내역이 필요 없다
        targetItemValue = sum(valueQueue) / valueQueueLen
        self._itemValues[targetItemName] = targetItemValue
        self._itemValuesQueue[targetItemName] = []
