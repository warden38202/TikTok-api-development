from flask import Flask, jsonify, request, g
from flask_apscheduler import APScheduler
from tiktok import *
import json
import pickle
import requests
from functools import wraps
from captchatest import Captcha
from captcha import Captcha as SlideCaptcha
# from captchav2 import Captcha as SlideCaptcha
import os
from config import RAPID_API_KEY, DOMAIN, PROXY, PROXY_TYPE, REGION
from mongoengine import connect, ValidationError, DoesNotExist
from bson import ObjectId
from model.user import User
from model.transaction import Transaction

from model.funding_request import FundingRequest

import random
import string
from datetime import datetime
from pymongo import UpdateOne
import threading

app = Flask(__name__)

# Map to store API keys to user IDs
apiKeyToUserIdMap = {}

errorneousAPIKeyAttemptMap = {}

userTransactionsState = {}

userBalanceMap = {}

requestAndTheirCost = {
    'balance':0.00,
    'requestFunding':0.00,
    'acceptFundingRequest':0.00,
    'login':0.00,
    'follow':0.00,
    'unfollow':0.00,
    'like':0.00,
    'comment':0.00
}
# Connect to MongoDB
connect(db='kitkot-1', host='localhost', port=27017)

rapid_api_key = RAPID_API_KEY
proxy = PROXY
proxy_type = PROXY_TYPE
Endpoint = DOMAIN
region = REGION
external_api = ExternalApi(rapid_api_key)


# APScheduler Configuration
class Config:
    SCHEDULER_API_ENABLED = True


app.config.from_object(Config())

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()


def consolidateUserTransactions(user_id_str, transactions=[]):
    try:
        # Convert user_id_str to ObjectId
        user_id = ObjectId(user_id_str)

        # Calculate the total value based on direction
        total_value = 0.0
        bulk_operations = []
        for txn in transactions:
            if txn.direction == "1":  # Credit
                total_value += txn.amount
            elif txn.direction == "0":  # Debit
                total_value -= txn.amount
            
            # Prepare bulk update operation
            bulk_operations.append(
                UpdateOne(
                    {'_id': txn.id},
                    {'$set': {'status': "1", 'updatedOn': datetime.utcnow()}}
                )
            )

        # Perform bulk write operation
        if bulk_operations:
            Transaction._get_collection().bulk_write(bulk_operations)

        # Update the user's balance using $inc operator
        User._get_collection().update_one(
            {'_id': user_id},
            {'$inc': {'balance': total_value}}
        )

        # Return the calculated value
        return total_value

    except (DoesNotExist, ValidationError) as e:
        raise ValueError(f"Error in consolidating transactions: {e}")


# Global lock for task synchronization
consolidation_lock = threading.Lock()


# Task to run every minute
@scheduler.task('interval', id='consolidateExistingTransactions', minutes=1)
def consolidateExistingTransactions():
    if consolidation_lock.acquire(blocking=False):
        try:
            transactions = Transaction.objects(status="2")
            simpleMap = {}
            for transaction in transactions:
                user_id_str = str(transaction.user)
                if user_id_str not in simpleMap:
                    simpleMap[user_id_str] = []
                simpleMap[user_id_str].append(transaction)
            for key in simpleMap:
                userTransactionsState[key] = False  # Can not do any transaction for now
                consolidateUserTransactions(key, simpleMap[key])
                userTransactionsState[key] = True  # Can now do transactions
        
            print("Consolidation task completed successfully.")
        except Exception as e:
            print(f"Error during consolidation task: {e}")
        finally:
            consolidation_lock.release()
    else:
        print("Consolidation task is already running.")


def debitUser(user_id_str, amount, transactionType, note=""):
    try:
        # Convert user_id_str to ObjectId
        user_id = ObjectId(user_id_str)
        transaction = Transaction(
                status="2",
                user=user_id,
                type=transactionType,
                direction="0",
                amount=amount,
                note=note
        )
        transaction.save()
    except Exception as e:
            print(f"Error during debitUser: {e}")


def establishAPIKey(apiKey):
    if isinstance(apiKey, str):
        apiKey = apiKey.strip()
        
        if len(apiKey) == 32:
            parts = [apiKey[i:i + 8].strip() for i in range(0, 32, 8)]
            
            if all(len(part) == 8 and ' ' not in part for part in parts):
                if apiKey not in apiKeyToUserIdMap:
                    try:
                        user = User.objects.get(d1=parts[0], d2=parts[1], d3=parts[2], d4=parts[3])
                        if user.status == "1":
                            apiKeyToUserIdMap[apiKey] = str(user.id)
                            userTransactionsState[apiKeyToUserIdMap[apiKey]] = False  # Can not do any transaction for now
                            try:
                                # Fetch transactions that are completed but not consolidated
                                transactions = Transaction.objects(user=apiKeyToUserIdMap[apiKey], status="2")
                                calculated_value = consolidateUserTransactions(apiKeyToUserIdMap[apiKey], transactions)
                                userBalanceMap[apiKeyToUserIdMap[apiKey]] = user.balance + calculated_value
                                userTransactionsState[apiKeyToUserIdMap[apiKey]] = True  # Can now do transactions
                            except ValueError as e:
                                # userTransactionsState[apiKeyToUserIdMap[apiKey]] = True # Can now do transactions
                                pass
                    except DoesNotExist:
                        pass


def generate_random_string(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def login_check(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        data = request.json
        username = data.get('username')
        try:
            with open(f"devices/{username}-info.json", "r") as file:
                g.device_info = json.load(file)

            with open(f"Cookies/{username}-loggedIn-headers.json", "r") as file:
                g.logged_in_headers = json.load(file)

            with open(f'Cookies/{username}-cookies.pkl', 'rb') as f:
                g.cookies = pickle.load(f)

            with open(f'Cookies/{username}-region.json', 'r') as f:
                g.region_info = json.load(f)
        except FileNotFoundError:
            response = jsonify(
                {'message': 'You are not logged in or username is inavlid'})
            return response

        return func(*args, **kwargs)

    return wrapper


# Middleware to check API key
@app.before_request
def check_api_key():
    print("request.endpoint", request.endpoint)
    if request.endpoint in requestAndTheirCost:
        apiKey = request.headers.get('X-API-KEY')
        if apiKey in errorneousAPIKeyAttemptMap:
            return jsonify({"code":500}), 500
        if len(apiKey) == 32:
            parts = [apiKey[i:i + 8].strip() for i in range(0, 32, 8)]
            
            if all(len(part) == 8 and ' ' not in part for part in parts):
                if apiKey not in apiKeyToUserIdMap:
                    establishAPIKey(apiKey)
            else:
                errorneousAPIKeyAttemptMap[apiKey] = True
        if apiKey not in apiKeyToUserIdMap:
            return jsonify({"error": "Unauthorized"}), 401
        else:
            g.userId = apiKeyToUserIdMap[apiKey]
            if userBalanceMap[g.userId] >= requestAndTheirCost[request.endpoint]:
                pass
            else:
                return jsonify({"error": "Insufficient fund"}), 401
                
    else:
        print("not aaaa")


@app.route('/', methods=["GET"])
def index():
    return jsonify({"message": "Server is running"}), 200


@app.route('/request-api-key', methods=['POST'])
def requestAPIKey():
    try:
        user = User(
            status='1',
            createdOn=datetime.utcnow(),
            d1=generate_random_string(),
            d2=generate_random_string(),
            d3=generate_random_string(),
            d4=generate_random_string(),
            balance=0.0,
            ipAddress=request.remote_addr,
            userAgent=request.headers.get('User-Agent')
        )
        user.save()
        return jsonify({"code":201, "apiKey":f"{user.d1}{user.d2}{user.d3}{user.d4}", "message": "Request Successful"}), 201
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400


@app.route('/balance', methods=["GET"])
def balance():
    return jsonify({"message": "Server is running", "balance":userBalanceMap[g.userId]}), 200


@app.route('/request-funding', methods=['POST'])
def requestFunding():
    data = request.json
    amount = data.get('amount')
    try:
        funding_request = FundingRequest(
            status='2',  # Initial status
            user=g.userId,
            amount=amount,
            initiatedOn=datetime.utcnow(),
            updatedOn=datetime.utcnow()
        )
        funding_request.save()
        return jsonify({"code": 201, "balance":userBalanceMap[g.userId], "fundingRequestId":str(funding_request.id)}), 201
    except ValidationError as e:
        return jsonify({"code": 500, "balance":userBalanceMap[g.userId], "error":f"Error creating funding request: {e}"}), 500


@app.route('/accept-funding-request/<fundingRequestId>', methods=['POST'])
def acceptFundingRequest(fundingRequestId):
    # "g.userId"
    print("g", g)
    print("g.userId", g.userId)
    try:
        funding_request = FundingRequest.objects.get(id=fundingRequestId)
        if funding_request.status == "2":
            transaction = Transaction(
                status="2",
                user=g.userId,
                type="2",
                direction="1",
                amount=funding_request.amount,
                note=""
            )
            transaction.save()
            funding_request.transaction = transaction.id
            funding_request.approvedBy = g.userId
            funding_request.status = "1"
            funding_request.save()
            consolidateExistingTransactions()
            userBalanceMap[g.userId] = userBalanceMap[g.userId] + funding_request.amount
            return jsonify({"code": 201, "balance":userBalanceMap[g.userId]}), 201
        else:
            return jsonify({"code": 500, "balance":userBalanceMap[g.userId], "error":"That fund request was already accepted."}), 500
    except DoesNotExist:
        return jsonify({"code": 500, "balance":userBalanceMap[g.userId], "error":"Funding request does not exist."}), 500


@app.route('/login', methods=['POST'])
def login():
    userBalanceMap[g.userId] = userBalanceMap[g.userId] - requestAndTheirCost[request.endpoint]
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        try:
            with open(f"devices/{username}.json", "r") as file:
                device = json.load(file)
        except FileNotFoundError:
            device = Utils.generate_device()
            with open(f"devices/{username}.json", "w") as file:
                json.dump(device, file)

        try:
            with open(f"devices/{username}-info.json", "r") as file:
                device_info = json.load(file)
        except FileNotFoundError:
            device_info = external_api.register_device({"Proxy": proxy,
                                                        "Country": region, **device}).json()
            with open(f"devices/{username}-info.json", "w") as file:
                json.dump(device_info, file)

        if "Device_Info" not in device_info:
            os.remove(f"devices/{username}-info.json")
            userBalanceMap[g.userId] = userBalanceMap[g.userId] + requestAndTheirCost[request.endpoint]
            return jsonify({"error": True, "message": "Please try again later"}), 500

        query_params = Utils.generate_query(device_info)

        session = requests.Session()

        headers = {
            "X-Ss-Stub": "",
            'connection': 'Keep-Alive',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'passport-sdk-version': '19',
            'pns_event_id': str(random.randint(100, 250)),
            'sdk-version': '2',
            'user-agent': device_info['Device_Info']['user-agent'],
            'x-tt-bypass-dp': '1',
            'x-tt-dm-status': 'login=0;ct=0;rt=7',
            'x-vc-bdturing-sdk-version': '2.3.5.i18n',
        }
        region_info = session.post(
            f"https://{DOMAIN}/passport/app/region/?{query_params}", urlencode({
                "hashed_id": Utils.generate_hash_id(username),
                "type": 3
            }), headers=headers).json()

        print(region_info)

        session.post(
            f"https://api22-normal-c-alisg.tiktokv.com/passport/app/region/?{query_params}", urlencode({
                "hashed_id": Utils.generate_hash_id(username),
                "type": 3
            }), headers=headers)
        Endpoint = region_info["data"]["domain"]
        captcha_domain = region_info["data"]["captcha_domain"]

        if "device_redirect_info" in region_info["data"]:
            extra = urlencode(
                {"device_redirect_info": region_info["data"]["device_redirect_info"]})
        else:
            extra = ""

        query_params = query_params + extra

        login_data = urlencode({
            'username': Utils.encrypt(username),
            'password': Utils.encrypt(password),
            'account_sdk_source': 'app',
            'mix_mode': '1',
            'multi_login': '1'
        })

        external_data = external_api.generate_data(
            device_info, query_params, login_data)

        signatures = external_api.signature(external_data).json()

        headers = Utils.generate_header(
            signatures, device_info, login_data, Endpoint)

        loginResponse = session.post(
            url=(
                "https://" + Endpoint + "/passport/user/login?"
                +query_params
            ),
            data=login_data,
            headers=headers,
            cookies=device_info["Cookies"],
            proxies={
                'http': f'{proxy_type}://{proxy}',
                'https': f'{proxy_type}://{proxy}'
            }
        )
        debitUser(g.userId, 0.01, '7', "login")
        print("loginResponse.text 001: ", loginResponse.text)
        try:
            response = loginResponse.json()
        except requests.exceptions.JSONDecodeError:
            return jsonify(loginResponse.text), 200

        print('loginResponse.text 001a response["data"]: ', response["data"])
        if "user_id" in response["data"]:
            print("Logged in")
            with open(f'Cookies/{username}-loggedIn-data.json', 'w') as f:
                json.dump(response, f)
            # print(loginResponse.headers, loginResponse.cookies)
            with open(f'Cookies/{username}-loggedIn-headers.json', 'w') as f:
                json.dump(dict(loginResponse.headers), f)
            with open(f'Cookies/{username}-cookies.pkl', 'wb') as f:
                pickle.dump(loginResponse.cookies, f)
            with open(f'Cookies/{username}-region.json', 'w') as f:
                json.dump(region_info["data"], f)

            debitUser(g.userId, 0.01, '7', "login")
            return jsonify(response), 200

        elif "verify_center_decision_conf" in response["data"]:
            print("\n\nverify_center_decision_conf in response data\n\n\n\n")
            captcha = json.loads(response["data"]["verify_center_decision_conf"])
            print("captcha", captcha)
            description = captcha["detail"]

            if captcha["subtype"] == "3d":
                print("3d captcha")
                print(Captcha(device_info['Device_Info']["device_id"],
                            device_info['Device_Info']["iid"], session, f"{proxy_type}://{proxy}", description, extra, host=captcha_domain).solve_captcha())
            if captcha["subtype"] == "slide":
                print(SlideCaptcha(device_info['Device_Info']["device_id"],
                                device_info['Device_Info']["iid"], session, f"{proxy_type}://{proxy}", description, extra, host=captcha_domain).solve_captcha())
                # print(SlideCaptcha(device_info['Device_Info'], session,
                #       f"{proxy_type}://{proxy}", description, host=captcha_domain).solve_captcha())

            loginResponse = session.post(
                url=(
                    "https://" + Endpoint + "/passport/user/login?"
                    +query_params
                ),
                data=login_data,
                headers=headers,
                cookies=loginResponse.cookies,
                proxies={
                    'http': f'{proxy_type}://{proxy}',
                    'https': f'{proxy_type}://{proxy}'
                }
            )
            print("loginResponse.text 002", loginResponse.text)
            debitUser(g.userId, 0.01, '7', "login")
            try:
                response = loginResponse.json()
            except requests.exceptions.JSONDecodeError:
                return jsonify(loginResponse.text), 200

            if "user_id" in response["data"]:
                print("Logged in")
                with open(f'Cookies/{username}-loggedIn-data.json', 'w') as f:
                    json.dump(response, f)
                # print(loginResponse.headers, loginResponse.cookies)
                with open(f'Cookies/{username}-loggedIn-headers.json', 'w') as f:
                    json.dump(dict(loginResponse.headers), f)
                with open(f'Cookies/{username}-cookies.pkl', 'wb') as f:
                    pickle.dump(loginResponse.cookies, f)
                with open(f'Cookies/{username}-region.json', 'w') as f:
                    json.dump(region_info["data"], f)

                debitUser(g.userId, 0.01, '7', "login")
                return jsonify(response), 200

            debitUser(g.userId, 0.01, '7', "login")
            return jsonify(loginResponse.json()), 200
        else:
            userBalanceMap[g.userId] = userBalanceMap[g.userId] + requestAndTheirCost[request.endpoint]
            return jsonify(loginResponse.json()), 401
    except Exception as e:
        userBalanceMap[g.userId] = userBalanceMap[g.userId] + requestAndTheirCost[request.endpoint]
        return jsonify({'code':500, 'message': f"Login request failed: {e}", "data": data}), 500

# Follow endpoint


@app.route('/follow/<tiktokusername>', methods=['POST'])
@login_check
def follow(tiktokusername):
    try:
        userBalanceMap[g.userId] = userBalanceMap[g.userId] - requestAndTheirCost[request.endpoint]
        if tiktokusername.startswith("@"):
            tiktokusername = tiktokusername.replace("@", "")

        tiktok_api = TikTokApi(g.device_info, g.logged_in_headers, g.cookies,
                            f'{proxy_type}://{proxy}', external_api, host=g.region_info["domain"])
        user_info = tiktok_api.usernameToInfo(tiktokusername)

        data = tiktok_api.follow(user_info)
        
        debitUser(g.userId, 0.01, '7', f"followed {tiktokusername}")
        return jsonify({'message': f'You are now following @{tiktokusername}', "data": data}), 200
    except Exception as e:
        userBalanceMap[g.userId] = userBalanceMap[g.userId] + requestAndTheirCost[request.endpoint]
        return jsonify({'code':500, 'message': f"Follow request failed: {e}", "data": data}), 500

# Unfollow endpoint


@app.route('/unfollow/<tiktokusername>', methods=['POST'])
@login_check
def unfollow(tiktokusername):
    try:
        userBalanceMap[g.userId] = userBalanceMap[g.userId] - requestAndTheirCost[request.endpoint]
        if tiktokusername.startswith("@"):
            tiktokusername = tiktokusername.replace("@", "")

        tiktok_api = TikTokApi(g.device_info, g.logged_in_headers, g.cookies,
                            f'{proxy_type}://{proxy}', external_api, host=g.region_info["domain"])
        user_info = tiktok_api.usernameToInfo(tiktokusername)

        data = tiktok_api.follow(user_info, False)

        debitUser(g.userId, 0.01, '7', f"unfollowed {tiktokusername}")
        return jsonify({'message': f'You unfollowed @{tiktokusername}', "data": data}), 200
    except Exception as e:
        userBalanceMap[g.userId] = userBalanceMap[g.userId] + requestAndTheirCost[request.endpoint]
        return jsonify({'code':500, 'message': f"Unfollow request failed: {e}", "data": data}), 500

# Like endpoint


@app.route('/like/<int:post_id>', methods=['POST'])
@login_check
def like(post_id):
    try:
        userBalanceMap[g.userId] = userBalanceMap[g.userId] - requestAndTheirCost[request.endpoint]
        tiktok_api = TikTokApi(g.device_info, g.logged_in_headers, g.cookies,
                            f'{proxy_type}://{proxy}', external_api, host=g.region_info["domain"])

        data = tiktok_api.like(post_id)

        # Logic to like the post
        debitUser(g.userId, 0.01, '7', f"liked {post_id}")
        return jsonify({'message': f'You liked post {post_id}', "data": data}), 200
    except Exception as e:
        userBalanceMap[g.userId] = userBalanceMap[g.userId] + requestAndTheirCost[request.endpoint]
        return jsonify({'code':500, 'message': f"Like request failed: {e}", "data": data}), 500
# Comment endpoint


@app.route('/comment/<int:post_id>', methods=['POST'])
@login_check
def comment(post_id):
    try:
        userBalanceMap[g.userId] = userBalanceMap[g.userId] - requestAndTheirCost[request.endpoint]
        data = request.json
        comment = data.get('text')
        tiktok_api = TikTokApi(g.device_info, g.logged_in_headers, g.cookies,
                            f'{proxy_type}://{proxy}', external_api, host=g.region_info["domain"])

        data = tiktok_api.comment(post_id, comment)
        debitUser(g.userId, 0.01, '7', f"commented on {post_id}")
        return jsonify({'message': f'Comment posted on post {post_id}: {comment}', "data": data}), 200
    except Exception as e:
        userBalanceMap[g.userId] = userBalanceMap[g.userId] + requestAndTheirCost[request.endpoint]
        return jsonify({'code':500, 'message': f"Comment request failed: {e}", "data": data}), 500


# Run consolidation immediately on startup
consolidateExistingTransactions()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
