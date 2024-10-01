import requests
import json
import time
import random
import re
from base64 import b64encode
from urllib.parse import urlencode
from config import CAP_GURU_API_KEY


def generate_fp_cookie_value():
    e = list("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
    t = len(e)
    n = str(int(time.time() * 1000))[::-1]
    r = ['_'] * 36
    r[8] = r[13] = r[18] = r[23] = "_"
    r[14] = "4"
    for i in range(36):
        if not r[i]:
            o = int(random.random() * t)
            r[i] = e[19] if i == 19 else e[(3 & o) | 8]
    return "verify_" + n + "_" + "".join(r)


def left_most_point(a, b):
    if a[0] < b[0]:
        return 0
    elif a[0] > b[0]:
        return 1
    else:
        if a[1] < b[1]:
            return 0
        else:
            return 1


def random_point_to_left_of(a, b, scale_down_factor=None):
    if scale_down_factor is None or not str(scale_down_factor).isdigit():
        scale_down_factor = 1
    scale_down_factor = float(scale_down_factor)
    random_x = random.random() * a[0] * scale_down_factor
    random_y = random.random() * b
    return [int(random_x), int(random_y)]


def random_point_between(a, b, h, scale_down_factor=None):
    if scale_down_factor is None or not str(scale_down_factor).isdigit():
        scale_down_factor = 1
    scale_down_factor = float(scale_down_factor)
    random_x = a[0] * scale_down_factor + random.random() * \
        (b[0] * scale_down_factor - a[0] * scale_down_factor)
    random_y = random.random() * h
    return [int(random_x), int(random_y)]


def random_point_to_right_bottom_of(a, l, b, scale_down_factor=None):
    if scale_down_factor is None or not str(scale_down_factor).isdigit():
        scale_down_factor = 1
    scale_down_factor = float(scale_down_factor)
    random_x = a[0] * scale_down_factor + random.random() * l
    random_y = a[1] * scale_down_factor + random.random() * b
    return [int(random_x), int(random_y)]


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
            "app_version": "33.6.3",

            "mode": "",
            "type": "verify",
            "detail": self.detail,
            "subtype": "3d",
            "challenge_code": 3058,
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

    def __solve_captcha(self, image_url: str) -> dict:
        captcha_image_download_response = requests.get(
            url=image_url)
        captcha_image_content = b64encode(
            captcha_image_download_response.content).decode('utf-8')

        send_captcha_image_response = requests.post(
            url="http://api.cap.guru/in.php",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "key": CAP_GURU_API_KEY,
                "method": "base64",
                "click": "geetest",
                "body": captcha_image_content,
                "json": 1,
                "textinstructions": "abc",
            })
        )

        response_body_json = send_captcha_image_response.json()
        request_id = response_body_json["request"]

        captcha_result_gotten = False
        solved_response_body_json = None

        while not captcha_result_gotten:
            captcha_solution_response = requests.get(
                url=f"http://api.cap.guru/res.php?key={CAP_GURU_API_KEY}&action=get&id={request_id}&json=1"
            )
            solved_response_body_json = captcha_solution_response.json()
            if solved_response_body_json["request"] != "CAPCHA_NOT_READY":
                captcha_result_gotten = True

        math_result = re.search(
            r'x=(\d+),y=(\d+);x=(\d+),y=(\d+)', solved_response_body_json["request"])
        incoming_point_on_x1 = int(math_result.group(1))
        incoming_point_on_y1 = int(math_result.group(2))
        incoming_point_on_x2 = int(math_result.group(3))
        incoming_point_on_y2 = int(math_result.group(4))

        fp = generate_fp_cookie_value()
        first_time_stamp = int(time.time() * 1000)
        about_thirty_five_seconds = 35000 + random.randint(1, 1000)
        about_thirty_five_seconds_before_anything_time_stamp = first_time_stamp - \
            about_thirty_five_seconds
        distance_between_first_and_second = random.randint(1, 200)
        second_time_stamp = first_time_stamp + distance_between_first_and_second
        distance_between_second_and_third = random.randint(1, 1000)
        third_time_stamp = second_time_stamp + distance_between_second_and_third
        distance_between_third_and_fourth = random.randint(1, 200)
        fourth_time_stamp = third_time_stamp + distance_between_third_and_fourth
        distance_between_fourth_and_fifth = random.randint(1, 1000)
        fifth_time_stamp = fourth_time_stamp + distance_between_fourth_and_fifth
        distance_between_fifth_and_sixth = 100 + random.randint(1, 200)
        sixth_time_stamp = fourth_time_stamp + distance_between_fifth_and_sixth

        checking = left_most_point([incoming_point_on_x1, incoming_point_on_y1], [
            incoming_point_on_x2, incoming_point_on_y2])

        if checking == 0:
            x1, x2, y1, y2 = incoming_point_on_x1, incoming_point_on_x2, incoming_point_on_y1, incoming_point_on_y2
        else:
            x1, x2, y1, y2 = incoming_point_on_x2, incoming_point_on_x1, incoming_point_on_y2, incoming_point_on_y1
        scale_down_factor = 303 / 552

        first_random_point_x, first_random_point_y = random_point_to_left_of(
            [x1, y1], 344, scale_down_factor)

        second_random_point_x, second_random_point_y = random_point_between(
            [x1, y1], [x2, y2], 344, scale_down_factor)

        third_random_point_x, third_random_point_y = random_point_to_right_bottom_of(
            [x2, y2], 552, 344, scale_down_factor)

        t = [
            {
                'x': first_random_point_x + round(random.random(), 14),
                'y': first_random_point_y + round(random.random(), 14),
                'force': 0,
                'time': first_time_stamp,
            },
            {
                'x': second_random_point_x + round(random.random(), 14),
                'y': second_random_point_y + round(random.random(), 14),
                'force': 0,
                'time': third_time_stamp,
            },
            {
                'x': third_random_point_x + round(random.random(), 14),
                'y': third_random_point_y + round(random.random(), 14),
                'force': 0,
                'time': fifth_time_stamp,
            }
        ]

        x_axis_decimal_additive = round(random.random(), 14)
        y_axis_decimal_additive = round(random.random(), 14)

        point_one = {
            'x': x1 * scale_down_factor + x_axis_decimal_additive,
            'y': y1 * scale_down_factor + y_axis_decimal_additive,
        }

        point_two = {
            'x': x2 * scale_down_factor + x_axis_decimal_additive,
            'y': y2 * scale_down_factor + y_axis_decimal_additive,
        }

        point_one_with_time = {**point_one, 'time': second_time_stamp}
        point_two_with_time = {**point_two, 'time': fourth_time_stamp}

        the_two_points = [point_one_with_time, point_two_with_time]

        simpler_models = {
            'x': {},
            'y': {},
            'z': [],
            't': t,
        }

        models = {**simpler_models, 'm': the_two_points}

        reply = [point_one, point_two]

        # JSONStringifiedSimplerModels = json.dumps(simpler_models)
        # JSONStringOfTheTwoPoints = json.dumps(the_two_points)

        answer_payload = {
            'modified_img_width': 303 + round(random.random() * 0.7, 13),
            'mode': '3d',
            'reply': reply,
            'models': models,
            # 'log_params': json.dumps({
            #     'aid': 1233,
            #     'did': self.__device_id,
            #     'iid': self.__install_id,
            #     'type': 2,
            #     'h5_sdk_version': '2.27.6',
            #     'h5_sdk_use_type': 'cdn',
            #     'platform': 'app',
            #     'os_name': dev_info['os'],
            #     'once': about_thirty_five_seconds_before_anything_time_stamp,
            #     'challenge_code': captcha_challenge_code,
            #     'mode': mode,
            #     'verify_host': 'https://rc-verification-i18n.tiktokv.com/',
            #     'lang': dev_info['language'],
            #     'app_name': dev_info['appName'],
            #     'locale': dev_info['language'],
            #     'ch': dev_info['channel'],
            #     'channel': dev_info['channel'],
            #     'app_key': '',
            #     'vc': dev_info['appVersion'],
            #     'app_version': dev_info['appVersion'],
            #     'region': captcha_region,
            #     'use_native_report': '1',
            #     'use_jsb_request': '1',
            #     'orientation': '1',
            #     'resolution': f"{dev_info['screenHeight']}*{dev_info['screenWidth']}",
            #     'sdk_version': '2.2.1.i18n',
            #     'os_version': dev_info['osVersion'],
            #     'device_brand': dev_info['deviceBrand'],
            #     'device_model': dev_info['deviceModel'],
            #     'version_code': dev_info['appVersionCode'],
            #     'device_type': dev_info['deviceModel'],
            #     'device_platform': dev_info['os'],
            #     'os_type': '0',
            #     'fp': fp,
            #     'product_host': 'sf16-website-login.neutral.ttwstatic.com',
            #     'product_path': '/obj/tiktok_web_login_static/bric-captcha-ttweb/core-captcha/in/2.27.6/1.0.0.90/index.html',
            #     'flag': 0,
            #     'swapped_mode': "3d",
            #     'key': 'h5_action',
            #     'webdriver': 'false',
            #     'challenge_id': captcha_id,
            #     'moveArr': JSONStringOfTheTwoPoints,
            #     'models': JSONStringifiedSimplerModels,
            #     'moveArr2': JSONStringOfTheTwoPoints,
            #     'models2': JSONStringifiedSimplerModels,
            #     'time': sixth_time_stamp,
            # }),
            'reply2': reply,
            'models2': models,
        }

        return answer_payload

    def __post_captcha(self, solve: dict) -> dict:
        params = self.__params()

        # body = {
        #     "modified_img_width": 552,
        #     "id": solve["id"],
        #     "mode": "slide",
        #     "reply": list(
        #         {
        #             "relative_time": i * solve["randlenght"],
        #             "x": round(
        #                 solve["maxloc"] / (solve["randlenght"] / (i + 1))
        #             ),
        #             "y": solve["tip"],
        #         }
        #         for i in range(
        #             solve["randlenght"]
        #         )
        #     ),
        # }

        body = solve

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
        # __tip_y = __captcha_challenge["data"]["question"]["ques"]

        solve = self.__solve_captcha(
            __captcha_challenge["data"]["question"]["url1"]
        )

        solve.update(
            {
                "id": __captcha_id,
            }
        )

        return self.__post_captcha(solve)
