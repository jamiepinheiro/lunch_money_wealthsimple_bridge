from os import environ
from typing import NamedTuple

# Lunch money auth
LUNCH_MONEY_API_KEY = environ["LUNCH_MONEY_API_KEY"]

# Wealthsimple auth
WS_USERNAME = environ["WS_USERNAME"]
WS_PASSWORD = environ["WS_PASSWORD"]

# Mapping from Wealthsimple accounts to Lunch Money assets
class AssetLink(NamedTuple):
    wsAccountId: str
    isWsTradeAccount: bool
    lunchMoneyAssetId: str

def toAssetLink(rawAssetLink: str):
    parts = rawAssetLink.split(",")
    return AssetLink(parts[0], parts[1] == "True", parts[2])

ASSET_LINKS = list(map(toAssetLink, environ["ASSET_LINKS"].split(" ")))

# How often to refresh access tokens and sync data
#  (25 minutes worked well in testing)
REFRESH_INTERVAL_SECS = environ.get("REFRESH_INTERVAL_SECS", 25 * 60)

# How many times to retry logging in before giving up
RETRY_LOGIN_TIMES = environ.get("RETRY_LOGIN_TIMES", 5)
