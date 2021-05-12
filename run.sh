#!/bin/bash

export LUNCH_MONEY_API_KEY="1234567890abcdefg"
export WS_USERNAME="me@emil.com"
export WS_PASSWORD="mysecurepassword"
export ASSET_LINKS="ws-trade-account-id,True,lunch-money-related-asset-id ws-invest-account-id,False,lunch-money-related-asset-id ws-cash-account-id,False,lunch-money-related-asset-id"
python main.py $1
