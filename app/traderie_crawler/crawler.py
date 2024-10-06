import os
import time
import urllib.parse
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from .chromedriver import ChromeDriver


class Crawler:
    def __init__(self, usernameStr, passwordStr) -> None:
        self._itemList = self._getItemList()
        self._itemCodes = {}

        self._driver = ChromeDriver()
        self._login(usernameStr, passwordStr)

    # 크롤링 할 아이템 목록
    def _getItemList(self):
        cfd = os.path.dirname(__file__)
        path = os.path.join(cfd, 'crawl_item_list.txt')
        if not os.path.exists(path):
            raise FileNotFoundError(f"[crawl_item_list] does not exist at [{path}]")

        with open(path, mode='r') as file:
            fileLines = file.readlines()

        itemList = []
        for line in fileLines:
            itemName = line.strip()
            if len(itemName) > 0:
                itemList.append(itemName)

        return itemList

    # 일단 로그인을 해야 거래 성사된 목록을 조회할 수 있다
    def _login(self, usernameStr, passwordStr):
        url = 'https://traderie.com/login'
        usernameSelector = 'div.input-row:nth-child(1) > input:nth-child(2)'
        passwordSelector = 'div.input-row:nth-child(2) > div:nth-child(2) > input:nth-child(1)'
        loginBtnSelector = 'div.login-btn-bar:nth-child(4) > button:nth-child(1)'
        d2rImageSelector = 'div.col-xs-12:nth-child(5) > a:nth-child(1) > div:nth-child(2)'

        # wait for login page
        try:
            self._driver.get(url)
            self._driver.waitAllByCssSelector(usernameSelector, passwordSelector, loginBtnSelector)
        except Exception as e:
            raise ConnectionError(f'login connection timeout')

        # process login
        username = self._driver.findElementByCssSelector(usernameSelector)
        username.send_keys(usernameStr)

        password = self._driver.findElementByCssSelector(passwordSelector)
        password.send_keys(passwordStr)

        loginBtn = self._driver.findElementByCssSelector(loginBtnSelector)
        loginBtn.click()

        # wait for login success page
        try:
            self._driver.waitAllByCssSelector(d2rImageSelector)
        except Exception as e:
            raise ConnectionError(f'login success timeout')

    # 지난 24시간 동안의 거래 내역을 모두 수집
    def crawl24HoursTradeHistorys(self, isHardcore, isLadder):
        tradeHistorys = {}
        for itemName in self._itemList:
            tradeHistory = self._crawl24HoursTradeHistory(itemName, isHardcore, isLadder)
            tradeHistorys[itemName] = tradeHistory

        return tradeHistorys

    def _crawl24HoursTradeHistory(self, itemName, isHardcore, isLadder):
        url = self._getTradeHistoryUrl(itemName, isHardcore, isLadder)
        offerRowSelector = 'div.sc-izQBue.fFOtdy'
        noListingSelector = '.no-listings'
        loadMoreSelector = '.see-all-btn-bar > button:nth-child(1)'

        # wait for trade history page
        MAX_RETRY_CNT = 3
        for i in range(MAX_RETRY_CNT):
            try:
                self._driver.get(url)
                self._driver.waitAnyByCssSelector(offerRowSelector, noListingSelector)
                break
            except Exception:
                if i == MAX_RETRY_CNT - 1:
                    return  # no listings 상태로 처리

        # check no trade history
        try:
            self._driver.findElementByCssSelector(noListingSelector)
            return  # no listings
        except Exception:
            pass

        # load more for 24 hours trade history
        while True:
            tradeElements = self._driver.findElementsByCssSelector(offerRowSelector)
            lastTradeElement = tradeElements[-1]
            _, _, elapsed24Hours = self._parseOneTrade(lastTradeElement.text)
            if elapsed24Hours:
                break  # 24시간 초과 항목까지 불러오기 완료

            try:
                loadMoreBtn = self._driver.findElementByCssSelector(loadMoreSelector)
                loadMoreBtn.send_keys(Keys.ENTER)
                time.sleep(1)
            except Exception:
                break  # load more 버튼이 없음. 더 이상 불러올 항목이 없음

        # parse all trade history
        tradeHistory = []

        tradeElements = self._driver.findElementsByCssSelector(offerRowSelector)
        for tradeElement in tradeElements:
            tradeCnt, tradeItemPackages, elapsed24Hours = self._parseOneTrade(tradeElement.text)
            if elapsed24Hours:
                break  # 시간순으로 정렬되어 표시되기에, 이 항목부터는 볼 필요가 없다
            if not tradeItemPackages:
                continue  # 유효하지 않은 거래

            oneTrade = {'tradeCnt': tradeCnt, 'tradeItemPackages': tradeItemPackages}
            tradeHistory.append(oneTrade)

        return tradeHistory

    # 거래 내역 주소
    def _getTradeHistoryUrl(self, itemName, isHardcore, isLadder):
        if itemName not in self._itemCodes:
            self._crawlItemCode(itemName)

        baseUrl = 'https://traderie.com/diablo2resurrected'
        itemCode = self._itemCodes[itemName]
        mode = "hardcore" if isHardcore else "softcore"
        ladder = "true" if isLadder else "false"

        return f'{baseUrl}/product/{itemCode}/recent?prop_Platform=PC&prop_Mode={mode}&prop_Ladder={ladder}'

    # 트레더리 전용 아이템 코드. 웹 페이지에서 직접 검색하여 알아내고, 저장해놓자
    def _crawlItemCode(self, itemName):
        encodedItemName = urllib.parse.quote(itemName)
        searchUrl = f'https://traderie.com/diablo2resurrected/products?search={encodedItemName}'
        itemSelector = '.item-container-img-icon'

        # 아이템 아이콘의 링크 url을 보고 아이템 코드 알아내기
        MAX_RETRY_CNT = 3
        for i in range(MAX_RETRY_CNT):
            try:
                self._driver.get(searchUrl)
                self._driver.waitAllByCssSelector(itemSelector)
                break
            except Exception as e:
                if i == MAX_RETRY_CNT - 1:
                    raise ConnectionError(f'crawl item code timeout. itemName: {itemName}')

        itemIcon = self._driver.findElementByCssSelector(itemSelector)
        a_tag = itemIcon.find_element(By.TAG_NAME, 'a')
        href = a_tag.get_attribute('href')  # 예시) https://traderie.com/diablo2resurrected/product/3214752119

        self._itemCodes[itemName] = href.split('/')[-1]

    # 하나의 거래 내역에 대하여 필요한 정보를 추출
    def _parseOneTrade(self, text):
        lines = text.split('\n')

        # 몇개를 묶어서 팔았는가
        title = lines[0]
        tradeCntStr = title[:title.index(' X ')]
        tradeCntStr = tradeCntStr.replace(",", "")  # 천 단위가 넘는 미친 거래가 있을 수도 있다
        tradeCnt = int(tradeCntStr)

        # 어떤 아이템들에 팔았는가
        tradeItemPackages = self._parseSellingLines(lines[6:-2])

        # 오래된 거래 내역인가
        elapsed24Hours = self._checkSellingTimeElapsed24Hours(lines[-1])

        return tradeCnt, tradeItemPackages, elapsed24Hours

    # 하나의 거래 내역에 대하여 어떤 아이템들에 팔았다고 나오는가
    def _parseSellingLines(self, lines):

        # OR 단위로 끊어서 정리
        tradeItemPackages = []
        tradeItemLines = []
        for line in lines:
            if ' (each)' in line:
                continue  # 그냥 많이 판다는 의미. 무시하자
            if ' OR' in line:
                tradeItemPackages.append(tradeItemLines)
                tradeItemLines = []
                continue  # OR 단위로 한번 끊음

            tradeItemLines.append(line)

        tradeItemPackages.append(tradeItemLines)

        # 룬과 퍼자만 취급한다. 다른 템이 섞인 거래내역은 취급 안 함
        for tradeItemPackage in tradeItemPackages:
            for tradeItem in tradeItemPackage:
                if ' Rune' in tradeItem:
                    continue  # 어떠한 종류의 룬이든 ok
                if ' Perfect Amethyst' in tradeItem:
                    continue  # 퍼팩트 자수정 ok

                return []  # 기타 다른 아이템이 섞이면 거래 내역 통째로 무시

        # 갯수 숫자는 따로 분리
        tradeItemWithCntPackages = []
        for tradeItemPackage in tradeItemPackages:
            tradeItemWithCntPackage = []
            for tradeItem in tradeItemPackage:
                if ' X ' in tradeItem:
                    itemInfo = tradeItem.split(' X ')
                    itemCntStr = itemInfo[0]
                    itemCntStr = itemCntStr.replace(",", "")  # 천 단위가 넘는 미친 거래가 있을 수도 있다
                    itemCnt = int(itemCntStr)
                    itemName = itemInfo[1]
                else:
                    itemCnt = 1
                    itemName = tradeItem

                tradeItemWithCnt = (itemCnt, itemName)
                tradeItemWithCntPackage.append(tradeItemWithCnt)

            tradeItemWithCntPackages.append(tradeItemWithCntPackage)

        return tradeItemWithCntPackages

    # '초', '분', '시간' 이라는 용어가 없으면 24시간 지난 내역
    def _checkSellingTimeElapsed24Hours(self, sellingTimeStr):
        findWords = ['초', '분', '시간', 'sec', 'min', 'hour']
        return not any(word in sellingTimeStr for word in findWords)

    def Exit(self):
        self._driver.quit()
