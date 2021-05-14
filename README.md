# Lunch Money Wealthsimple Bridge

A python script to sync balances from Wealthsimple Invest, Trade, and Cash accounts to Lunch Money.

## How it works
This script uses the [Unofficial Wealthsimple API's](https://github.com/MarkGalloway/wealthsimple-trade) to fetch balances and then pushes those balances to the corresponding asset in Lunch Money. The script periodically refreshes the access tokens to Wealthsimple so that a OTP code does not need to be entered each time (only once at the start).

## Prerequisites
- An installation of [Python3](https://www.python.org/downloads/).

## Running
1) Modify `run.sh` (unix) or `run.bat` (windows) with your account details.

| Field                 | Required               | Notes                                                                                                                                                                                               |
|-----------------------|------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| LUNCH_MONEY_API_KEY   | ✔️                     | Obtained from [Lunch Money Developer Settings](https://my.lunchmoney.app/developers).                                                                                                                           |
| WS_USERNAME           | ✔️                     | Email associated with Wealthsimple accounts.                                                                                                                                                                    |
| WS_PASSWORD           | ✔️                     | Password associated with Wealthsimple accounts.                                                                                                                                                                 |
| ASSET_LINKS           | ✔️                     | List of mappings from Wealthsimple accounts to Lunch Money assets. Each entry is of the form: `<wealthsimple_account_id>,<is_wealthsimple_trade_account>,<lunch_money_asset_id>`. Entries are separated by spaces.|
| REFRESH_INTERVAL_SECS | Default of 25 minutes  | How often to sync balances. Recommended to be at least 30 minutes or the access tokens may expire.                                                                                                               |
| RETRY_LOGIN_TIMES     | Default of 3           | How many times to retry logging in if the login fails.                                                                                                                                                           |

### Example
A correctly setup `run.sh` for a Wealthsimple Trade(`ws-trade-1`), a Wealthsimple Invest(`ws-invest-1`), and a WealthsimpleCash(`ws-cash-1`) accounts mapping to Lunch Money assets with IDs `lm-1`, `lm-2`, and `lm-3` respectfully.
```
#!/bin/bash

export LUNCH_MONEY_API_KEY="1234567890abcdefg"
export WS_USERNAME="me@emil.com"
export WS_PASSWORD="mysecurepassword"
export ASSET_LINKS="ws-trade-1,True,lm-1 ws-invest-1,False,lm-2 ws-cash-1,False,lm-3"
python main.py $1
```

2) In your terminal, execute `./run.sh <otp>` where `<otp>` is the one time passcode obtained from your authenticator app.

## Errors
The unofficial APIs at times are flaky and don't always provide balance details. Detailed logs of the script's actions are outputted into the `logs` directory. If there is a persistent issue, feel free to open an issue on Github with a redacted log file (or submit a PR fixing it!), and I'll be happy to take a look!
