#!/usr/bin/env python
#import logging
#logging.basicConfig(level=logging.DEBUG)

import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import config


slack_token = config.SLACK_TOKEN
client = WebClient(token=slack_token)

try:
    response = client.chat_postMessage(
        channel="D05CT7CR97E",
		text="Bot test, please ignore"
    )
except SlackApiError as e:
    # You will get a SlackApiError if "ok" is False
    assert e.response["error"]    # str like 'invalid_auth', 'channel_not_found'