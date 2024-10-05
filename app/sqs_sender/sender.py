import json
import boto3
from datetime import datetime, timezone


class Sender:
    def __init__(self, Id, pwd, region, url) -> None:
        self._sqsClient = boto3.client(
            'sqs',
            aws_access_key_id=Id,
            aws_secret_access_key=pwd,
            region_name=region
        )
        self._queueUrl = url

    def _send(self, data):
        response = self._sqsClient.send_message(
            QueueUrl=self._queueUrl,
            MessageBody=json.dumps(data)
        )
        if len(response) == 0:
            raise ConnectionError(f'sqs response is empty')

    def reportError(self, error):
        self._send(str(error))

    def sendItemInfos(self, isHardcore, isLadder, itemValues):
        mode = "Hardcore" if isHardcore else "Softcore"
        ladder = "Ladder" if isLadder else "NonLadder"
        roundItemValues = {}
        for itemName, itemValue in itemValues.items():
            if itemValue < 1:
                roundItemValues[itemName] = round(itemValue, 2)
            elif itemValue < 10:
                roundItemValues[itemName] = round(itemValue, 1)
            else:
                roundItemValues[itemName] = round(itemValue, 0)

        data = {
            'mode': mode,
            'ladder': ladder,
            'curTime': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            'itemValues': roundItemValues
        }

        self._send(data)
