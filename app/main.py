import os
from datetime import datetime, timezone

from app import App


# 에러 로그도 앱에서 처리하지만, 앱이 완전히 망가졌을 때를 대비한 파일 로그
def writeFileLog(fileLog):
    utcTimeStr = datetime.now(timezone.utc).strftime('%Y-%m-%d %H_%M_%S')
    fileName = utcTimeStr + '.txt'

    logDirPath = os.path.join(os.path.dirname(__file__), '../log')
    if not os.path.exists(logDirPath):
        os.makedirs(logDirPath)

    filePath = os.path.join(logDirPath, fileName)
    with open(filePath, 'w') as file:
        file.write(fileLog)


# python main.py 실행시
if __name__ == "__main__":
    try:
        app = App()
        app.Run()
    except Exception as e:
        log = str(e)
        writeFileLog(log)
