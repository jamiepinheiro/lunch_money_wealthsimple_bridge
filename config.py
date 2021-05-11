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
