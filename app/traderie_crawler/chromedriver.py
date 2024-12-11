import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class ChromeDriver:
    def __init__(self) -> None:
        self._options = self._getChromeOptions()
        self._exePath = self._getDriverExecutablePath()
        self._driver = uc.Chrome(options=self._options, driver_executable_path=self._exePath)
        self._driver.set_page_load_timeout(60)

    # 최대한 컴퓨팅 자원을 아끼기 위한 옵션 설정
    def _getChromeOptions(self):
        chrome_options = uc.ChromeOptions()

        chrome_options.page_load_strategy = 'eager'
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-notifications")

        return chrome_options

    # 이게 없으면 매번 최신 크롬 드라이버를 내부적으로 다운로드 받음. 파일을 갖고 있자
    def _getDriverExecutablePath(self):
        cfd = os.path.dirname(__file__)
        path = os.path.join(cfd, 'chromedriver-win64/chromedriver.exe')
        if not os.path.exists(path):
            raise FileNotFoundError(f"[chromedriver] does not exist at [{path}]")

    # 단순히 해당 페이지 접속
    def get(self, url):
        self._driver.get(url)

    # selectors에 대해 모두 로딩 될 때까지 대기
    def waitAllByCssSelector(self, *selectors):
        for selector in selectors:
            WebDriverWait(self._driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )

    # selectors에 대해 하나라도 로딩 될 때까지 대기
    def waitAnyByCssSelector(self, *selectors):
        WebDriverWait(self._driver, 60).until(
            EC.any_of(*[
                EC.presence_of_element_located((By.CSS_SELECTOR, selector)) for selector in selectors
            ])
        )

    # 제곧내
    def findElementByCssSelector(self, selector):
        return self._driver.find_element(By.CSS_SELECTOR, selector)

    def findElementsByCssSelector(self, selector):
        return self._driver.find_elements(By.CSS_SELECTOR, selector)

    def findElementsByClassName(self, className):
        return self._driver.find_elements(By.CLASS_NAME, className)

    # 크롬 드라이버 종료 (굳이 할 필요가 있을까?)
    def quit(self):
        self._driver.quit()
