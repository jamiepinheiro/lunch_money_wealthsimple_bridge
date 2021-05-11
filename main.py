import sys
import requests
import json
from typing import NamedTuple
from datetime import datetime, timedelta
from config import *

WS_OAUTH_URL = "https://api.production.wealthsimple.com/v1/oauth/token"
WS_TRADE_BALANCE_URL = "https://trade-service.wealthsimple.com/account/history/1m?account_id="
WS_NON_TRADE_BALANCE_URL = "https://my.wealthsimple.com/graphql"
BALANCE_GRAPHQL_QUERY = "{\"operationName\":\"getPortfolioValue\",\r\n\"variables\":{\"clientId\":\"%s\",\"currency\":\"CAD\",\"today\":\"%s\",\"tomorrow\":\"%s\"},\"query\":\"query getPortfolioValue($clientId: ID!, $currency: Currency!, $today: String!, $tomorrow: String!) {\\n  client(id: $clientId) {\\n    id\\n    profile {\\n      preferredFirstName: preferred_first_name\\n      __typename\\n    }\\n    ...ClientAccounts\\n    netDeposits: net_deposits(start_date: $today, end_date: $tomorrow, resolution: daily) {\\n      ...ClientEmptyStateNetDeposits\\n      results {\\n        accountId: account_id\\n        totalWithdrawals: total_withdrawals {\\n          amount\\n          __typename\\n        }\\n        __typename\\n      }\\n      __typename\\n    }\\n    netLiquidationValues: net_liquidation_values(resolution: daily, start_date: $today, end_date: $tomorrow, currency: $currency) {\\n      ...ClientNetLiquidationValue\\n      date\\n      accountId: account_id\\n      netLiquidationValue: net_liquidation_value\\n      __typename\\n    }\\n    __typename\\n  }\\n}\\n\\nfragment ClientAccounts on Client {\\n  id\\n  accounts {\\n    id\\n    __typename\\n  }\\n  __typename\\n}\\n\\nfragment ClientNetLiquidationValue on NetLiquidationValue {\\n  date\\n  netLiquidationValue: net_liquidation_value\\n  __typename\\n}\\n\\nfragment ClientEmptyStateNetDeposits on NetDepositsResponse {\\n  results {\\n    totalDeposits: total_deposits {\\n      amount\\n      __typename\\n    }\\n    __typename\\n  }\\n  __typename\\n}\\n\"}"
LUNCH_MONEY_ASSET_URL = "https://dev.lunchmoney.app/v1/assets/"

class WsSession(NamedTuple):
	accessToken: str
	refreshToken: str
	userId: str

class Balance(NamedTuple):
	amount: str
	asOf: str

def loginToWs(optCode: str):
	result = requests.post(
		WS_OAUTH_URL,
		data = {
			"grant_type":"password",
			"username":WS_USERNAME,
			"password":WS_PASSWORD,
			"skip_provision":True,
			"otp_claim":None,
			"scope":"invest.read invest.write mfda.read mfda.write mercer.read mercer.write trade.read trade.write empower.read empower.write tax.read tax.write",
			"client_id":"4da53ac2b03225bed1550eba8e4611e086c7b905a3855e6ed12ea08c246758fa"
		},
		headers = {
			"x-wealthsimple-otp" : optCode
		}
	)
	response = json.loads(result.content)
	return WsSession(response["access_token"], response["refresh_token"], response["resource_owner_id"])

def getWsTradeBalance(ws: WsSession, assetLink: AssetLink):
	result = requests.get(
		WS_TRADE_BALANCE_URL + assetLink.wsAccountId,
		headers = {
			"Authorization": "Bearer " + ws.accessToken
		}
	)
	balance = json.loads(result.content)["results"][-1]
	
	if balance:
		return Balance(balance["value"]["amount"], balance["date"])

	return None

def getWsNonTradeBalance(ws: WsSession, assetLink: AssetLink):
	response = requests.post(
		WS_NON_TRADE_BALANCE_URL,
		headers={
			"Authorization": "Bearer " + ws.accessToken,
			"Content-Type": "application/json"
		}, 
		data=BALANCE_GRAPHQL_QUERY % (
			ws.userId,
			datetime.today().strftime("%Y-%m-%d"),
			(datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
		)
	)

	balances = json.loads(response.content)["data"]["client"]["netLiquidationValues"]
	for balance in balances:
		if balance["accountId"] == assetLink.wsAccountId:
			return Balance(balance["netLiquidationValue"], balance["date"])
	
	return None

def updateLunchMoneyAsset(balance: Balance, assetLink: AssetLink):
	response = requests.put(
		LUNCH_MONEY_ASSET_URL + assetLink.lunchMoneyAssetId,
		data = {
			"balance": balance.amount,
			"balance_as_of": balance.asOf,
		},
		headers = {
			"Authorization": "Bearer " + LUNCH_MONEY_API_KEY
		}
	)

	print(response.content)

if len(sys.argv) != 2:
	print("Usage: main.py <otp_code>")
	sys.exit(1)
otpCode = sys.argv[1]

ws = loginToWs(otpCode)

for assetLink in ASSET_LINKS:
	balance = getWsTradeBalance(ws, assetLink) if assetLink.isWsTradeAccount else getWsNonTradeBalance(ws, assetLink)
	if balance:
		updateLunchMoneyAsset(balance, assetLink)
