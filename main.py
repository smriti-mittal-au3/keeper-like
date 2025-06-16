# Project: Keeper-Style Transaction Review Module for Zoho Books

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import requests
from dotenv import load_dotenv
import json
import urllib.parse

load_dotenv()

from datetime import datetime, timedelta
from pathlib import Path

TOKENS_DIR = Path("tokens")
TOKENS_DIR.mkdir(exist_ok=True)  # ensure it exists
# OK. so why did I use FastAPI? 
# Django vs Flask vs FastAPI 
# 
app = FastAPI()

# allow_origins=["*"] and allow_credentials=True, the browser will block the request 
# and you'll get the CORS error you described.
# Why MAN!!!!!!!
# I guess bcoz you are allowing credentials, like auth token, header
# so how can you allow it from ALL 
origins = [
    "http://localhost:3000",  # Allows your local React development server to access the API.
    "https://keeper-like.onrender.com",  # Your backend's own domain, useful if it makes self-requests.
    "https://childokay.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 'access_token': '1000.72021b6d32d386181371947edf151054.da65ce63b22e653b9fc184a7878f6183', 
# 'refresh_token': '1000.0291c11abf826a821aa1ac465c9dd4a8.242d7a4a4e6b4ba06f047691d0f6d183', 
# 'scope': 'ZohoBooks.fullaccess.all', 
# 'api_domain': 'https://www.zohoapis.in', 
# 'token_type': 'Bearer', 
# 'expires_in': 3600

ZOHO_ORG_ID = os.getenv("ZOHO_ORG_ID")
ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
ZOHO_BASE_URL = os.getenv("ZOHO_BASE_URL")
ZOHO_CODE = os.getenv("ZOHO_CODE")
MY_WEB_CLIENT_SECRET = os.getenv("MY_WEB_CLIENT_SECRET")
MY_WEB_CLIENT_ID = os.getenv("MY_WEB_CLIENT_ID")

# ZOHO_REFRESH_TOKEN = ""
# ZOHO_ACCESS_TOKEN = ""

app.state.my_data = {"ZOHO_REFRESH_TOKEN": "1000.0291c11abf826a821aa1ac465c9dd4a8.242d7a4a4e6b4ba06f047691d0f6d183", "ZOHO_ACCESS_TOKEN": ""}


# ZOHO_ACCESS_TOKEN = os.getenv("ZOHO_ACCESS_TOKEN")
# ZOHO_BASE_URL = "https://books.zoho.com/api/v3"


def get_new_access_and_refresh_token():
    url = 'https://accounts.zoho.in/oauth/v2/token?scope=ZohoBooks.fullaccess.all' + '&code=' + ZOHO_CODE + '&client_id=' + ZOHO_CLIENT_ID + '&client_secret=' + ZOHO_CLIENT_SECRET + '&redirect_uri=' + ZOHO_BASE_URL + '/bills&grant_type=authorization_code'
    headers = { 'Content-Type': 'application/json' }
    response = requests.post(url, headers=headers)

    # check if error, try / catch
    # {'error': 'invalid_code'}
    print(response.json(), 'response json() get_new_access_and_refresh_token')
    ZOHO_ACCESS_TOKEN = response.json()['access_token']
    ZOHO_REFRESH_TOKEN = response.json()['refresh_token']

    app.state.my_data["ZOHO_ACCESS_TOKEN"] = ZOHO_ACCESS_TOKEN
    app.state.my_data["ZOHO_REFRESH_TOKEN"] = ZOHO_REFRESH_TOKEN

    # app.state.my_data.set("ZOHO_ACCESS_TOKEN", ZOHO_ACCESS_TOKEN)
    # app.state.my_data.set("ZOHO_REFRESH_TOKEN", ZOHO_REFRESH_TOKEN)


    # print(ZOHO_ACCESS_TOKEN, "new access token")
    # print(ZOHO_REFRESH_TOKEN, "new refresh token")
    return response



def get_access_token_from_refresh_token():
    # refresh token is PERMANENT. use it to generate an access token
    url = 'https://accounts.zoho.in/oauth/v2/token?refresh_token=' + app.state.my_data.get("ZOHO_REFRESH_TOKEN") + '&client_id=' + ZOHO_CLIENT_ID + '&client_secret=' + ZOHO_CLIENT_SECRET + '&redirect_uri=' + ZOHO_BASE_URL + '/bills&grant_type=refresh_token'
    headers = { 'Content-Type': 'application/json' }
    # data = { 'key': 'value' }

    response = requests.post(url, headers=headers)
    print(response, 'egrgdfgdgf')
    ZOHO_ACCESS_TOKEN = response.json()['access_token']
    # set() ???
    app.state.my_data["ZOHO_ACCESS_TOKEN"] = ZOHO_ACCESS_TOKEN
    # app.state.my_data.set("ZOHO_ACCESS_TOKEN", ZOHO_ACCESS_TOKEN)

    return ZOHO_ACCESS_TOKEN



# oauth 2.0 vs authentication (by login)
# oauth = giving access to someone w/o sharing ur username or password
# oauth = authorization

# json bcoz - 
# env can't store date strings and all
# env updated, then need to restart BE (remember react?)
def token_file_path(org_id: str) -> Path:
    return TOKENS_DIR / f"{org_id}.json"

def load_token(org_id: str) -> dict | None:
    file_path = token_file_path(org_id)
    if not file_path.exists():
        return None
    with file_path.open("r") as f:
        return json.load(f)

def save_token(org_id: str, access_token: str, refresh_token: str, expires_in: int):
    file_path = token_file_path(org_id)
    expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
    token_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at
    }
    # will this create a new .json file too 
    with file_path.open("w") as f:
        json.dump(token_data, f, indent=2)

def get_access_token(org_id: str) -> str | None:
    token = load_token(org_id)
    if not token:
        return None
    if datetime.fromisoformat(token["expires_at"]) <= datetime.utcnow():
        return None  # expired
    return token["access_token"]

def get_refresh_token(org_id: str) -> str | None:
    token = load_token(org_id)
    return token["refresh_token"] if token else None



# one time activity => i need to save refresh token etc per client ..
# FOR Web Based applications!!
@app.get("/auth/zoho/initiate")
def initiate_zoho_oauth():
    # my client id, secret, code => my refresh, access token right?
    # the prefix 1000.... is associated with the India data center (zoho.in
    client_id = MY_WEB_CLIENT_ID
    # diff url for prod / local
    # http://localhost:8000/auth/zoho/callback
    # Redirect URI passed does not match with the one configured
    redirect_uri = "https://keeper-like.onrender.com/auth/zoho/callback"
    # invalid scope, doesn't exist
    # ZohoBooks.contacts.ALL ZohoBooks.transactions.ALL 
    scope = "ZohoBooks.fullaccess.ALL"
    state = "testing"  # For CSRF protection

    # /v2/auth? vs /v2/token?
    # oh getting my code is also automated hence?

    # READ -- StatReload detected changes in 'main.py'
    # An error occurred while processing your request. - token? vs auth?
    # READ -- waait .. how was url not encoded this time!!! redirect url was / and not %F2 etc!!
    # https://accounts.zoho.in/oauth/v2/auth?scope=ZohoBooks.fullaccess.all&client_id=1000.FA5LKYNIB8T5E7F0NT6G3O528FA6JZ&state=secure_random_state&prompt=consent&redirect_uri=https://localhost:8000/auth/zoho/callback&response_type=code
    # Client ID passed does not exist
    # 1000.FA5LKYNIB8T5E7F0NT6G3O528FA6JZ
    # 1000.FA5LKYNIB8T5E7F0NT6G3O528FA6JZ
    # https://accounts.zoho.com/oauth/v2/auth?scope=ZohoBooks.invoices.CREATE,ZohoBooks.invoices.READ,ZohoBooks.invoices.UPDATE,ZohoBooks.invoices.DELETE&client_id=1000.0SRSxxxxxxxxxxxxxxxxxxxx239V&state=testing&response_type=code&redirect_uri=http://www.zoho.com/books&access_type=offline&prompt=consent
    # If you are using a local development environment, ensure that the redirect_uri is accessible 
    # from the internet, as Zoho's API needs to redirect to a publicly accessible URL.
    auth_url = 'https://accounts.zoho.in/oauth/v2/auth?scope=' + scope + '&client_id=' + client_id + '&access_type=offline' + '&state=' + state + '&prompt=consent' + '&redirect_uri=' + redirect_uri + '&response_type=code'


    # what auth url it is?
    print(auth_url, "auth_url ....");

    return {"url": auth_url}



@app.get("/auth/zoho/callback")
async def handle_callback(request: Request):
    # sent by /auth
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    token_url = "https://accounts.zoho.in/oauth/v2/token"

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data={
                            "grant_type": "authorization_code",
                            "client_id": MY_WEB_CLIENT_ID,
                            "client_secret": MY_WEB_CLIENT_SECRET,
                            "redirect_uri": "https://keeper-like.onrender.com/auth/zoho/callback",
                            "code": code
                        })

        token_data = response.json()
        # my tokens or theirs no ?
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        expires_in = token_data["expires_in"]

        # Fetch org ID
        async with httpx.AsyncClient() as client1:
            org_resp = await client1.get(
                "https://books.zoho.in/api/v3/organizations",
                headers={"Authorization": f"Zoho-oauthtoken {access_token}"}
            )
            print(org_resp, "... org_resp ...")
            organization_id = org_resp.json()["organizations"][0]["organization_id"]

            # Save access_token, refresh_token, organization_id and expires_in to DB
            save_token(organization_id, access_token, refresh_token, expires_in)
            print(organization_id, access_token, refresh_token, expires_in, "...organization_id, access_token, refresh_token, expires_in")
            return {"access_token": access_token, "refresh_token": refresh_token, "org_id": organization_id, "expires_in": expires_in}




# ERROR:    Exception in ASGI application
@app.get("/reviews/transactions")
async def review_transactions():
    # {'Authorization': 'Zoho-oauthtoken '} headers
    ZOHO_ACCESS_TOKEN = app.state.my_data.get("ZOHO_ACCESS_TOKEN")
    ZOHO_REFRESH_TOKEN = app.state.my_data.get("ZOHO_REFRESH_TOKEN")

    print("access:", ZOHO_ACCESS_TOKEN, " refresh:", ZOHO_REFRESH_TOKEN)

    # or error, call inside this function
    # only once right, at first login
    if ZOHO_REFRESH_TOKEN == "" and ZOHO_ACCESS_TOKEN == "":
        get_new_access_and_refresh_token()

    if ZOHO_ACCESS_TOKEN == "":
      ZOHO_ACCESS_TOKEN = get_access_token_from_refresh_token()

    headers = { 'Authorization': f"Zoho-oauthtoken {ZOHO_ACCESS_TOKEN}" }
    print(headers, "headers")
    
    async with httpx.AsyncClient() as client:
        response = await client.get("https://www.zohoapis.in/books/v3" + "/expenses?organization_id=" + ZOHO_ORG_ID, headers=headers)
        print(response.json().keys(), response.json().get("code", ""), response.json().get("message", ""), "response")
        # dict_keys(['code', 'message', 'expenses', 'page_context']
        # dict_keys(['code', 'message']) 
        # 57 response
        transactions = response.json().get("expenses", [])

        # 'expense_id', 'date', 'user_name', 'paid_through_account_name', 
        # 'account_name', 'description', 'currency_id', 'currency_code', 
        # 'bcy_total', 'bcy_total_without_tax', 'total', 'total_without_tax', 
        # 'is_billable', 'reference_number', 'customer_id', 'is_personal', 
        # 'customer_name', 'vendor_id', 'vendor_name', 'status', 'created_time', 
        # 'last_modified_time', 'expense_receipt_name', 'exchange_rate', 'distance', 
        # 'mileage_rate', 'mileage_unit', 'mileage_type', 'expense_type', 'report_id',
        # 'start_reading', 'end_reading', 'report_name', 
        # 'report_number', 'has_attachment', 'custom_fields_list'
        # print(transactions[0], "transactions [0].....")
        # IndexError: list index out of range

        code = response.json().get("code", "")
        message = response.json().get("message", "")
        contacts = response.json().get("contacts", [])

        # File "/opt/render/project/src/main.py", line 275, in review_transactions
        # print(code, message, len(contacts), contacts[0], "contacts")
        print(code, message, len(contacts), "contacts")

        flagged = []
        seen = set()
        print(len(seen), len(transactions))


        async with httpx.AsyncClient() as client3:
            vendors = await client3.get("https://www.zohoapis.in/books/v3" + "/contacts?organization_id=" + ZOHO_ORG_ID, headers=headers)
            all_vendors = vendors.json()

        for txn in transactions:
            # Choose relevant keys to identify a unique transaction
            # ok? not extensive no? ignore meta data like ids etc

            # comments / chats where do they go?
            # or user reads from Keeper only?
            # auto-comment too? ask her what she writes most of the time?
            comparison_dict = {
                "amount": txn["total"],
                "date": txn["date"],
                "vendor_name": txn.get("vendor_name"),
                "reference_number": txn.get("reference_number"),
            }

            hashable = json.dumps(comparison_dict, sort_keys=True)

            if hashable in seen:
                flagged.append({"issue": "Possible Duplicates", **txn})
            else:
                seen.add(hashable)

            if not txn.get('vendor_name'):
                flagged.append({"issue": "Missing Vendors", **txn})

        return flagged
