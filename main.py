import sys
import requests
import json
import logging
import time
import os
from typing import NamedTuple
from datetime import datetime, timedelta
from config import *

WS_OAUTH_URL = "https://api.production.wealthsimple.com/v1/oauth/token"
WS_TRADE_AUTH_URL = "https://trade-service.wealthsimple.com/auth/login"
WS_TRADE_AUTH_REFRESH_URL = "https://trade-service.wealthsimple.com/auth/refresh"
WS_TRADE_BALANCE_URL = "https://trade-service.wealthsimple.com/account/history/1d?account_id="
WS_NON_TRADE_BALANCE_URL = "https://my.wealthsimple.com/graphql"
BALANCE_GRAPHQL_QUERY = "{\"operationName\":\"getPortfolioValue\",\r\n\"variables\":{\"clientId\":\"%s\",\"currency\":\"CAD\",\"today\":\"%s\",\"tomorrow\":\"%s\"},\"query\":\"query getPortfolioValue($clientId: ID!, $currency: Currency!, $today: String!, $tomorrow: String!) {\\n  client(id: $clientId) {\\n    id\\n    profile {\\n      preferredFirstName: preferred_first_name\\n      __typename\\n    }\\n    ...ClientAccounts\\n    netDeposits: net_deposits(start_date: $today, end_date: $tomorrow, resolution: daily) {\\n      ...ClientEmptyStateNetDeposits\\n      results {\\n        accountId: account_id\\n        totalWithdrawals: total_withdrawals {\\n          amount\\n          __typename\\n        }\\n        __typename\\n      }\\n      __typename\\n    }\\n    netLiquidationValues: net_liquidation_values(resolution: daily, start_date: $today, end_date: $tomorrow, currency: $currency) {\\n      ...ClientNetLiquidationValue\\n      date\\n      accountId: account_id\\n      netLiquidationValue: net_liquidation_value\\n      __typename\\n    }\\n    __typename\\n  }\\n}\\n\\nfragment ClientAccounts on Client {\\n  id\\n  accounts {\\n    id\\n    __typename\\n  }\\n  __typename\\n}\\n\\nfragment ClientNetLiquidationValue on NetLiquidationValue {\\n  date\\n  netLiquidationValue: net_liquidation_value\\n  __typename\\n}\\n\\nfragment ClientEmptyStateNetDeposits on NetDepositsResponse {\\n  results {\\n    totalDeposits: total_deposits {\\n      amount\\n      __typename\\n    }\\n    __typename\\n  }\\n  __typename\\n}\\n\"}"
LUNCH_MONEY_ASSET_URL = "https://dev.lunchmoney.app/v1/assets/"

class WsNonTradeSession(NamedTuple):
	accessToken: str
	refreshToken: str
	userId: str

class WsTradeSession(NamedTuple):
	accessToken: str
	refreshToken: str

class WsSessions(NamedTuple):
	ws: WsNonTradeSession
	wsTrade: WsTradeSession

class Balance(NamedTuple):
	amount: str

def loginToWs(nonWsTradeAccounts: bool, wsTradeAccounts: bool, optCode: str):
	ws, wsTrade = None, None

	if nonWsTradeAccounts:
		for _ in range(RETRY_LOGIN_TIMES):
			try:
				result = requests.post(
					WS_OAUTH_URL,
					data = {
						"grant_type": "password",
						"username": WS_USERNAME,
						"password": WS_PASSWORD,
						"skip_provision": True,
						"otp_claim": None,
						"scope": "invest.read invest.write mfda.read mfda.write mercer.read mercer.write trade.read trade.write empower.read empower.write tax.read tax.write",
						"client_id": "4da53ac2b03225bed1550eba8e4611e086c7b905a3855e6ed12ea08c246758fa"
					},
					headers = {
						"x-wealthsimple-otp": optCode
					}
				)
				response = json.loads(result.content)
				ws = WsNonTradeSession(response["access_token"], response["refresh_token"], response["resource_owner_id"])
				logging.info("Logged into Wealthsimple Non Trade")
				break
			except Exception as e:
				logging.exception("Failed to log into Wealthsimple Non Trade")
				continue
		if not ws:
			raise Exception("Failed to log into Wealthsimple Non Trade")

	if wsTradeAccounts:
		for _ in range(RETRY_LOGIN_TIMES):
			try:
				result = requests.post(
					WS_TRADE_AUTH_URL,
					data = {
						"email": WS_USERNAME,
						"password": WS_PASSWORD,
						"otp": optCode
					}
				)
				wsTrade = WsTradeSession(result.headers["X-Access-Token"], result.headers["X-Refresh-Token"])
				logging.info("Logged into Wealthsimple Trade")
				break
			except Exception as e:
				logging.exception("Failed to log into Wealthsimple Trade")
				continue
		if not wsTrade:
			raise Exception("Failed to log into Wealthsimple Trade")
	
	return WsSessions(ws, wsTrade)

def getWsTradeBalance(wsSessions: WsSessions, assetLink: AssetLink):
	result = requests.get(
		WS_TRADE_BALANCE_URL + assetLink.wsAccountId,
		headers = {
			"Authorization": "Bearer " + wsSessions.wsTrade.accessToken
		}
	)
	data = json.loads(result.content)

	if "results" not in data:
		raise Exception("Failed to get Wealthsimple trade account data", data)

	balance = json.loads(result.content)["results"][-1]
	return Balance(balance["value"]["amount"])

def getWsNonTradeBalance(wsSessions: WsSessions, assetLink: AssetLink):
	response = requests.post(
		WS_NON_TRADE_BALANCE_URL,
		headers={
			"Authorization": "Bearer " + wsSessions.ws.accessToken,
			"Content-Type": "application/json"
		}, 
		data=BALANCE_GRAPHQL_QUERY % (
			wsSessions.ws.userId,
			datetime.today().strftime("%Y-%m-%d"),
			(datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
		)
	)

	balances = json.loads(response.content)["data"]["client"]["netLiquidationValues"]
	for balance in balances:
		if balance["accountId"] == assetLink.wsAccountId:
			return Balance(balance["netLiquidationValue"])
	
	raise ("Wealthsimple Non-trade account not found", balances)

def updateLunchMoneyAsset(balance: Balance, assetLink: AssetLink):
	response = requests.put(
		LUNCH_MONEY_ASSET_URL + assetLink.lunchMoneyAssetId,
		data = {
			"balance": balance.amount
		},
		headers = {
			"Authorization": "Bearer " + LUNCH_MONEY_API_KEY
		}
	)

	if response.status_code != 200:
		raise "Failed to update lunch money asset"

	return response.content.decode("utf-8")

def refreshTokens(wsSessions: WsSessions):
	ws, wsTrade = None, None
	
	if wsSessions.ws:
		result = requests.post(
			WS_OAUTH_URL,
			data = {
				"grant_type": "refresh_token",
				"refresh_token": wsSessions.ws.refreshToken,
				"username": WS_USERNAME,
				"password": WS_PASSWORD,
				"skip_provision": True,
				"otp_claim": None,
				"scope": "invest.read invest.write mfda.read mfda.write mercer.read mercer.write trade.read trade.write empower.read empower.write tax.read tax.write",
				"client_id": "4da53ac2b03225bed1550eba8e4611e086c7b905a3855e6ed12ea08c246758fa"
			}
		)
		response = json.loads(result.content)
		ws = WsNonTradeSession(response["access_token"], response["refresh_token"], response["resource_owner_id"])
		logging.info("Refreshed Wealthsimple Non Trade access token")

	if wsTradeAccounts:
		result = requests.post(
			WS_TRADE_AUTH_REFRESH_URL,
			data = {
				"refresh_token": wsSessions.wsTrade.refreshToken
			}
		)
		wsTrade = WsTradeSession(result.headers["X-Access-Token"], result.headers["X-Refresh-Token"])
		logging.info("Refreshed Wealthsimple Trade access token")

	return WsSessions(ws, wsTrade)

if not os.path.isdir("logs"):
	os.mkdir("logs")
logging.basicConfig(
	filename = "logs/%s-%d.log" % (WS_USERNAME, int(time.time())),
	filemode = "w",
	format = "%(asctime)s: %(levelname)s - %(message)s",
	level = logging.INFO
)

if len(sys.argv) != 2:
	print("Usage: main.py <otp_code>")
	sys.exit(1)
otpCode = sys.argv[1]

logging.info("Logging in and syncing %s's Wealthsimple Accounts" % WS_USERNAME)

nonWsTradeAccounts = any(map(lambda assetLink: not assetLink.isWsTradeAccount, ASSET_LINKS))
wsTradeAccounts = any(map(lambda assetLink: assetLink.isWsTradeAccount, ASSET_LINKS))

ws = None
try:
	ws = loginToWs(nonWsTradeAccounts, wsTradeAccounts, otpCode)
except Exception as e:
	logging.error("Failed to login")
	sys.exit(1)

while True:
	for assetLink in ASSET_LINKS:
		logging.info("Updating - %s" % str(assetLink))

		balance = None
		try:
			balance = getWsTradeBalance(ws, assetLink) if assetLink.isWsTradeAccount else getWsNonTradeBalance(ws, assetLink)
			logging.info("Successfully got - %s" % str(balance))
		except Exception as e:
			logging.exception("Failed to get Wealthsimple balance")
			continue

		try:
			updatedAsset = updateLunchMoneyAsset(balance, assetLink)
			logging.info("Successfully updated Lunch Money asset - %s" % str(updatedAsset))
		except Exception as e:
			logging.exception("Failed to update Lunch Money asset")

	time.sleep(REFRESH_INTERVAL_SECS)

	try:
		ws = refreshTokens(ws)
		logging.info("Successfully refreshed access tokens")
	except Exception as e:
		logging.exception("Failed to refresh access tokens")
