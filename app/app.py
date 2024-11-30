import os

from traderie_crawler import Crawler
from item_appraiser import Appraiser
from sqs_sender import Sender


class App:
    def __init__(self) -> None:
        self._initCrawler()
        self._initAppraiser()
        self._initSender()

    # 트래더리 거래 내역 크롤러
    def _initCrawler(self):
        username = os.environ.get('TRADERIE_USERNAME')
        password = os.environ.get('TRADERIE_PASSWORD')

        if username is None:
            raise SystemError('traderie username does not exist at os.environ')
        if password is None:
            raise SystemError('traderie password does not exist at os.environ')

        self._crawler = Crawler(username, password)

    # 거래 내역에 따른 가치 감별기
    def _initAppraiser(self):
        self._appraiser = Appraiser()

    # sqs로 메시지 전송기
    def _initSender(self):
        Id = os.environ.get('SQS_ID')
        pwd = os.environ.get('SQS_PWD')
        region = os.environ.get('SQS_REGION')
        url = os.environ.get('SQS_URL')

        if Id is None:
            raise SystemError('sqs id does not exist at os.environ')
        if pwd is None:
            raise SystemError('sqs pwd does not exist at os.environ')
        if region is None:
            raise SystemError('sqs region does not exist at os.environ')
        if url is None:
            raise SystemError('sqs url does not exist at os.environ')

        self._sender = Sender(Id, pwd, region, url)

    # D2R 트래더리 추적기 실행
    def Run(self):
        self._run(False, True)  # 소코 래더
        self._run(False, False)  # 소코 스탠
        # self._run(True, True)  # 하코 래더
        # 하코 스탠은 거래 내역이 너무 없어서, 페이지 로딩이 안 됨

        self._sender.sendMsg('end of process')

    # 특정 모드/래더에 대해 작업 진행
    # 정상 완료시 json 메시지를 sqs로 전송
    # 에러 발생시 일반 메시지를 sqs로 전송
    def _run(self, isHardcore, isLadder):
        try:
            tradeHistorys = self._crawler.crawl24HoursTradeHistorys(isHardcore, isLadder)
            itemValues = self._appraiser.appraise(tradeHistorys)
            self._sender.sendItemInfos(isHardcore, isLadder, itemValues)
        except Exception as e:
            self._sender.sendMsg(e)

    def Exit(self):
        self._crawler.Exit()
