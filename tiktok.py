import requests
import os
import uuid
import time
from urllib.parse import urlencode
import hashlib
import random


class ExternalApi:
    def __init__(self, apikey: str) -> None:
        self._endpoint = "https://tiktok-device-registeration.p.rapidapi.com"
        self._headers = {
            "X-RapidAPI-Key": apikey,
            "X-RapidAPI-Host": "tiktok-device-registeration.p.rapidapi.com"
        }

    def register_device(self, params: dict):
        return requests.get(
            self._endpoint+"/Tiktok_Device_Gen/", headers=self._headers, params=params)

    def signature(self, data: dict):
        return requests.post(self._endpoint+"/Get_Sign/", json=data, headers=self._headers)

    @staticmethod
    def generate_data(device_info: dict, params: str, payload: str) -> dict:
        Cookies = '; '.join(
            [f'{key}={value}' for key, value in device_info['Cookies'].items()])

        return {
            "Params": params,
            "Payload": payload,
            "Sig_Token": device_info['secDeviceIdToken'],
            "Cookies": Cookies,
            "Bd_Lanusk": "",  # This data Comes in response headers after login tiktok account like this  #vqj9gCzgfSa0PaRvV/oiwGJ5lAO9VjDgLYBWp533J1ALNvAsld3tDLOZb5kTXd7Q9OM7ZhobWkDWyQAn
            "Bd_Kmsv": "",  # Same Comes in response headers after login like this 0 int value
            "Seed_Token": device_info['Seed_Token'],
            "Seed_Algorithm": device_info['Seed_Algorithm']
        }


class Utils:
    @staticmethod
    def generate_device() -> dict:
        return {'Openudid': os.urandom(8).hex(),
                'Req_id': str(uuid.uuid4()),
                'Cdid':  str(uuid.uuid4()),
                'Clientuuid': str(uuid.uuid4()),
                'Google_aid':  str(uuid.uuid4()), }

    @staticmethod
    def encrypt(string: str) -> str:
        encrypted = [hex(ord(c) ^ 5)[2:] for c in string]
        return "".join(encrypted)

    @staticmethod
    def generate_query(device_info: dict, extra: dict = None) -> str:
        output = {
            "passport-sdk-version": "19",
            "iid": device_info['Device_Info']["iid"],
            "device_id": device_info['Device_Info']["device_id"],
            "ac": "wifi",
            "channel": device_info['Device_Info']["channel"],
            "aid": device_info['Device_Info']["aid"],
            "app_name": "musical_ly",
            "version_code": device_info['Device_Info']["version_code"],
            "version_name": device_info['Device_Info']["version_name"],
            "device_platform": "android",
            "os": "android",
            "ab_version": device_info['Device_Info']["ab_version"],
            "ssmix": "a",
            "device_type": device_info['Device_Info']["device_type"],
            "device_brand": device_info['Device_Info']["device_brand"],
            "language": device_info['Device_Info']["language"],
            "os_api": device_info['Device_Info']["os_api"],
            "os_version": device_info['Device_Info']["os_version"],
            "openudid": device_info['Device_Info']["openudid"],
            "manifest_version_code": device_info['Device_Info']["manifest_version_code"],
            "resolution": device_info['Device_Info']["resolution"],
            "dpi": device_info['Device_Info']["dpi"],
            "update_version_code": device_info['Device_Info']["update_version_code"],
            "_rticket": str(round(time.time() * 1000)),
            "app_type": "normal",
            "sys_region":  device_info['Device_Info']["sys_region"],
            "mcc_mnc": device_info['Device_Info']["mcc_mnc"],
            "timezone_name": device_info['Device_Info']["timezone_name"],
            "ts": str(round(time.time())),
            "timezone_offset": device_info['Device_Info']["timezone_offset"],
            "build_number": device_info['Device_Info']["build_number"],
            "region":  device_info['Device_Info']["region"],
            "carrier_region": device_info['Device_Info']["carrier_region"],
            "uoo": "0",
            "app_language":  device_info['Device_Info']["app_language"],
            "locale": device_info['Device_Info']["locale"],
            "op_region":  device_info['Device_Info']["op_region"],
            "ac2": "wifi",
            "host_abi": device_info['Device_Info']["host_abi"],
            "cdid": device_info['Device_Info']["cdid"],
            "support_webview": "1",
            "okhttp_version": device_info['Device_Info']["okhttp_version"],
            "use_store_region_cookie": "1"
        }
        if extra:
            output.update(extra)

        return urlencode(output).replace('%2A', '*')

    @staticmethod
    def generate_stub(payload: str) -> str:
        return hashlib.md5(payload.encode()).hexdigest().upper()

    @staticmethod
    def generate_header(signatures: dict, device_info: dict, payload: str, Endpoint: str = 'api16-normal-useast5.us.tiktokv.com') -> dict:
        return {
            'connection': 'Keep-Alive',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'host': Endpoint,
            'passport-sdk-version': '19',
            'pns_event_id': str(random.randint(100, 250)),
            'sdk-version': '2',
            'user-agent': device_info['Device_Info']['user-agent'],
            'x-argus': signatures['X-Argus'],
            'x-gorgon': signatures['X-Gorgon'],
            'x-khronos': signatures['X-Khronos'],
            'x-ladon':  signatures['X-Ladon'],
            'x-ss-req-ticket': str(int(signatures['X-Khronos'])*1000),
            'x-ss-stub': hashlib.md5(payload.encode()).hexdigest().upper(),
            'x-tt-bypass-dp': '1',
            'x-tt-dm-status': 'login=0;ct=0;rt=7',
            'x-vc-bdturing-sdk-version': '2.3.5.i18n',
        }

    @staticmethod
    def account_header(device_info: dict, logged_in_headers: dict, csrf: str, signatures=None, payload=None, Endpoint: str = 'api16-normal-useast5.us.tiktokv.com') -> dict:
        output = {
            'Accept-Encoding': 'gzip, deflate',
            'connection': 'Keep-Alive',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'host': Endpoint,
            'passport-sdk-version': '19',
            'pns_event_id': str(random.randint(100, 250)),
            'sdk-version': '2',
            'user-agent': device_info['Device_Info']['user-agent'],
            'x-tt-bypass-dp': '1',
            'x-tt-dm-status': 'login=1;ct=1;rt=1',
            'x-vc-bdturing-sdk-version': '2.3.5.i18n',
            'X-Ss-Req-Ticket': str(round(time.time() * 1000)),
            'X-Bd-Kmsv': logged_in_headers["X-Bd-Lanusv"],
            'X-Bd-Client-Key': logged_in_headers["X-Bd-Lanusk"],
            'X-Tt-Token': logged_in_headers["X-Tt-Token"],
            'X-Tt-Multi-Sids': logged_in_headers["X-Tt-Multi-Sids"],
        }

        if csrf:
            output.update({'X-Tt-Passport-Csrf-Token': csrf})

        if signatures:
            output.update({
                'x-argus': signatures['X-Argus'],
                'x-gorgon': signatures['X-Gorgon'],
                'x-khronos': signatures['X-Khronos'],
                'x-ladon':  signatures['X-Ladon'],
                'x-ss-req-ticket': str(int(signatures['X-Khronos'])*1000),
            })
        if payload:
            output.update(
                {'x-ss-stub': hashlib.md5(payload.encode()).hexdigest().upper()})

        return output

    @staticmethod
    def timeinms():
        return str(round(time.time() * 1000))

    @staticmethod
    def generate_hash_id(string):
        return hashlib.sha256(f"{string}aDy0TUhtql92P7hScCs97YWMT-jub2q9".encode()).hexdigest()


class TikTokApi:
    def __init__(self, device_info, logged_in_headers, cookies, proxy, external_api, host='api16-normal-useast5.us.tiktokv.com') -> None:
        self.proxy = proxy
        self.device_info = device_info
        self.logged_in_headers = logged_in_headers
        self.cookies = cookies
        self.external_api = external_api

        self.Endpoint = host

    def usernameToInfo(self, tiktokusername):
        common_query = Utils.generate_query(
            self.device_info, {"id": tiktokusername})

        external_data = self.external_api.generate_data(
            self.device_info, common_query, "")
        signatures = self.external_api.signature(external_data).json()
        if "passport_csrf_token_default" in self.cookies:
            csrf = self.cookies['passport_csrf_token_default']
        else:
            csrf = None
        headers = Utils.account_header(
            self.device_info, self.logged_in_headers, csrf, signatures, Endpoint=self.Endpoint)

        res = requests.get(
            "https://" + self.Endpoint + "/aweme/v1/user/uniqueid/?" + common_query, headers=headers,
            proxies={
                'http': self.proxy,
                'https': self.proxy
            },
            cookies=self.cookies
        )

        print(res.text, res.status_code)

        return res.json()

    def follow(self, user_info, follow=True):
        if follow:
            type = 1
        else:
            type = 0
        extra = {
            "user_id": user_info["uid"],
            "sec_user_id": user_info["sec_uid"],
            "type": type,
            "channel_id": 3,
            "from": 19,
            "from_pre": 13,
            "previous_page": "homepage_hot",
            "action_time": Utils.timeinms(),
            "is_network_available": "true",
        }

        common_query = Utils.generate_query(self.device_info, extra)

        external_data = self.external_api.generate_data(
            self.device_info, common_query, "")
        signatures = self.external_api.signature(external_data).json()
        if "passport_csrf_token_default" in self.cookies:
            csrf = self.cookies['passport_csrf_token_default']
        else:
            csrf = None
        headers = Utils.account_header(
            self.device_info, self.logged_in_headers, csrf, signatures, Endpoint=self.Endpoint)

        res = requests.get(
            "https://" + self.Endpoint + "/aweme/v1/commit/follow/user/?" + common_query, headers=headers,
            proxies={
                'http': self.proxy,
                'https': self.proxy
            },
            cookies=self.cookies
        )
        print(res.text, res.status_code)

        return res.json()

    def like(self, post_id, like=True):
        if like:
            type = 1
        else:
            type = 0
        extra = {
            "aweme_id": post_id,
            "enter_from": "homepage_follow",
            "friends_upvote": "false",
            "type": type,
            "channel_id": 1,
        }
        common_query = Utils.generate_query(self.device_info, extra)
        external_data = self.external_api.generate_data(
            self.device_info, common_query, "")

        signatures = self.external_api.signature(external_data).json()
        if "passport_csrf_token_default" in self.cookies:
            csrf = self.cookies['passport_csrf_token_default']
        else:
            csrf = None

        headers = Utils.account_header(
            self.device_info, self.logged_in_headers, csrf, signatures, Endpoint=self.Endpoint)

        res = requests.get(
            "https://" + self.Endpoint + "/aweme/v1/commit/item/digg/?" + common_query, headers=headers,
            proxies={
                'http': self.proxy,
                'https': self.proxy
            },
            cookies=self.cookies
        )
        print(res.text, res.status_code)

        return res.json()

    def comment(self, post_id, comment):
        common_query = Utils.generate_query(self.device_info)

        comment_data = urlencode({
            'aweme_id': post_id,
            'text': comment,
            'text_extra': '[]',
            'image_extra': '[]',
            'is_self_see': 0,
            'channel_id': 3,
            'action_type': 0,
            'publish_scenario': 0,
            'skip_rethink': 0,
        })
        external_data = self.external_api.generate_data(
            self.device_info, common_query, comment_data)

        signatures = self.external_api.signature(external_data).json()
        if "passport_csrf_token_default" in self.cookies:
            csrf = self.cookies['passport_csrf_token_default']
        else:
            csrf = None

        headers = Utils.account_header(
            self.device_info, self.logged_in_headers, csrf, signatures, comment_data, Endpoint=self.Endpoint)

        res = requests.post(
            "https://" + self.Endpoint + "/aweme/v1/comment/publish/?" + common_query, headers=headers,
            data=comment_data,
            proxies={
                'http': self.proxy,
                'https': self.proxy
            },
            cookies=self.cookies
        )
        print(res.text, res.status_code)

        return res.json()
