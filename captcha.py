import requests
import random
import time
from urllib.parse import urlencode
import base64
from solver import PuzzleSolver


class Captcha:
    def __init__(self, did, iid, cookies="", proxy="", detail="", device_redirect_info="", host=""):
        self.__host = host
        self.__device_id = did
        self.__install_id = iid
        # self.__cookies = cookies
        self.__client = cookies
        self.proxy = proxy
        self.detail = detail
        self.device_redirect_info = device_redirect_info

    def __params(self):
        params = {
            "lang": "en",
            "app_name": "musical_ly",
            "h5_sdk_version": "2.32.7",
            "h5_sdk_use_type": "cdn",
            "sdk_version": "2.3.6.i18n",
            "iid": self.__install_id,
            "did": self.__device_id,
            "device_id": self.__device_id,
            "ch": "googleplay",
            "aid": 1233,  # "1233",
            "os_type": 0,
            "mode": "",
            "tmp": f"{int(time.time())}{random.randint(111, 999)}",
            "platform": "app",
            "webdriver": "false",
            "verify_host": f"https://{self.__host}/",
            "locale": "en",
            "channel": "googleplay",
            "app_key": "",
            "vc": "33.6.3",
            "app_verison": "33.6.3",
            "session_id": "",
            "region": ["va", "US"],
            "use_native_report": 0,
            "use_jsb_request": 1,
            "orientation": 1,
            "resolution": "900*1552",
            "os_version": 9,
            "device_brand": "samsung",
            "device_model": "SM-G973N",
            "os_name": "Android",
            "challenge_code": 1105,
            "app_version": "33.6.3",
            "subtype": "slide",
            "type": "verify",
            "detail": self.detail
        }

        return urlencode(params) + self.device_redirect_info

    def __headers(self) -> dict:

        headers = {
            "sdk-version": "2",
            "x-ss-req-ticket": str(int(time.time() * 1000)),
            # "cookie": self.__cookies,
            "content-type": "application/json; charset=utf-8",
            "host": self.__host,
            "connection": "Keep-Alive",
            "user-agent": "okhttp/3.10.0.1",
            "passport-sdk-version": "19",
        }

        return headers

    def __get_challenge(self) -> dict:

        params = self.__params()

        req = self.__client.get(
            url=(
                "https://"
                + self.__host
                + "/captcha/get?"
                + params
            ),
            headers=self.__headers(),
            proxies={
                'http': self.proxy,
                'https': self.proxy
            }
        )

        return req.json()

    def __solve_captcha(self, url_1: str, url_2: str) -> dict:
        puzzle = base64.b64encode(
            self.__client.get(
                url_1,
            ).content
        )
        piece = base64.b64encode(
            self.__client.get(
                url_2,
            ).content
        )

        solver = PuzzleSolver(puzzle, piece)
        maxloc = solver.get_position()
        randlength = round(
            random.random() * (100 - 50) + 50
        )
        time.sleep(1)
        return {
            "maxloc": maxloc,
            "randlenght": randlength
        }

    def __post_captcha(self, solve: dict) -> dict:
        params = self.__params()

        body = {
            "modified_img_width": 552,
            "id": solve["id"],
            "mode": "slide",
            "reply": list(
                {
                    "relative_time": i * solve["randlenght"],
                    "x": round(
                        solve["maxloc"] / (solve["randlenght"] / (i + 1))
                    ),
                    "y": solve["tip"],
                }
                for i in range(
                    solve["randlenght"]
                )
            ),
        }

        headers = self.__headers()

        req = self.__client.post(
            url=(
                "https://"
                + self.__host
                + "/captcha/verify?"
                + params
            ),
            headers=headers.update(
                {
                    "content-type": "application/json"
                }
            ),

            json=body,
            proxies={
                'http': self.proxy,
                'https': self.proxy
            }
        )

        return req.json()

    def solve_captcha(self):
        __captcha_challenge = self.__get_challenge()
        __captcha_id = __captcha_challenge["data"]["id"]
        __tip_y = __captcha_challenge["data"]["question"]["tip_y"]

        solve = self.__solve_captcha(
            __captcha_challenge["data"]["question"]["url1"],
            __captcha_challenge["data"]["question"]["url2"],
        )

        solve.update(
            {
                "id": __captcha_id,
                "tip": __tip_y
            }
        )

        return self.__post_captcha(solve)
