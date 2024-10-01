import requests
import time
import requests
import json
import base64
import random
from urllib.parse import urlencode

import cv2
import base64
import numpy as np


class PuzzleSolver:
    def __init__(self, base64puzzle, base64piece):
        self.puzzle = base64puzzle
        self.piece = base64piece

    def get_position(self):
        puzzle = self.__background_preprocessing()
        piece = self.__piece_preprocessing()
        matched = cv2.matchTemplate(
            puzzle,
            piece,
            cv2.TM_CCOEFF_NORMED
        )
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(matched)
        return max_loc[0]

    def __background_preprocessing(self):
        img = self.__img_to_grayscale(self.piece)
        background = self.__sobel_operator(img)
        return background

    def __piece_preprocessing(self):
        img = self.__img_to_grayscale(self.puzzle)
        template = self.__sobel_operator(img)
        return template

    def __sobel_operator(self, img):
        scale = 1
        delta = 0
        ddepth = cv2.CV_16S

        img = cv2.GaussianBlur(img, (3, 3), 0)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        grad_x = cv2.Sobel(
            gray,
            ddepth,
            1,
            0,
            ksize=3,
            scale=scale,
            delta=delta,
            borderType=cv2.BORDER_DEFAULT,
        )
        grad_y = cv2.Sobel(
            gray,
            ddepth,
            0,
            1,
            ksize=3,
            scale=scale,
            delta=delta,
            borderType=cv2.BORDER_DEFAULT,
        )
        abs_grad_x = cv2.convertScaleAbs(grad_x)
        abs_grad_y = cv2.convertScaleAbs(grad_y)
        grad = cv2.addWeighted(abs_grad_x, 0.5, abs_grad_y, 0.5, 0)

        return grad

    def __img_to_grayscale(self, img):
        return cv2.imdecode(
            self.__string_to_image(img),
            cv2.IMREAD_COLOR
        )

    def __string_to_image(self, base64_string):

        return np.frombuffer(
            base64.b64decode(base64_string),
            dtype='uint8'
        )


class Captcha:
    def __init__(self, device, cookies, proxy, detail: str):
        self.domain = 'rc-verification-i18n'
        self.params = device
        self.detail = detail
        self.proxy = proxy
        self.cookies = cookies

        self.__client = requests.Session()

    def __params(self):
        params = {
            'lang': self.params["app_language"],
            'app_name': self.params["app_name"],
            'h5_sdk_version': '2.31.2',
            'h5_sdk_use_type': 'cdn',
            'sdk_version': '2.3.3.i18n',
            'iid': self.params['iid'],
            'did': self.params['device_id'],
            'device_id': self.params['device_id'],
            'ch': 'googleplay',
            'aid': self.params["aid"],
            'os_type': '0',
            'mode': '',
            'tmp': str(int(time.time())),
            'platform': 'app',
            'webdriver': 'false',
            'verify_host': 'https://rc-verification-i18n.tiktokv.com/',
            'locale': self.params["locale"],
            'channel': 'googleplay',
            'app_key': '',
            'vc': self.params["version_name"],
            'app_version': self.params["version_name"],
            'session_id': '',
            'region': 'in',
            'use_native_report': '1',
            'use_jsb_request': '1',
            'orientation': '2',
            'resolution': self.params["resolution"],
            'os_version': self.params["os_version"],
            'device_brand': self.params["device_brand"],
            'device_model': self.params["device_type"],
            'os_name': self.params["os"],
            'version_code': '3153',
            'device_type': self.params["device_type"],
            'device_platform': self.params["device_platform"],
            'type': 'verify',
            'detail': self.detail,
            # 'server_sdk_env': json.dumps({'idc': 'useast5', 'region': 'I18N', 'server_type': 'passport'}, separators=(',', ':')),
            'subtype': 'slide',
            'challenge_code': '3058',
            'triggered_region': 'in',
            'device_redirect_info': ''
        }

        return urlencode(params)

    def __headers(self):
        return {
            'accept-encoding': 'gzip',
            'x-tt-request-tag': 'n=1;t=0',
            'x-vc-bdturing-sdk-version': '2.3.3.i18n',
            'x-ss-req-ticket': str(int(time.time() * 1000)),
            'x-tt-bypass-dp': '1',
            'content-type': 'application/json; charset=utf-8',
            'x-tt-dm-status': 'login=0;ct=0;rt=7',
            'x-tt-store-region': 'gb',
            'x-tt-store-region-src': 'did',
            'user-agent': self.params["user-agent"],
            'host': 'rc-verification-i18n.tiktokv.com',
            'connection': 'Keep-Alive',
            "cookie": self.cookies,
        }

    def __get_challenge(self):
        params = self.__params()

        return self.__client.get('https://%s.tiktokv.com/captcha/get?%s' % (self.domain, params),
                                 headers=self.__headers(), proxies={
            'http': self.proxy,
            'https': self.proxy
        }).json()

    def __solve_captcha(self, url_1: str, url_2: str):
        puzzle = base64.b64encode(self.__client.get(url_1).content)
        piece = base64.b64encode(self.__client.get(url_2).content)
        solver = PuzzleSolver(puzzle, piece)

        time.sleep(1)
        return {
            'maxloc': solver.get_position(),
            'randlenght': round(random.random() * (100 - 50) + 5)
        }

    def __post_captcha(self, solve: dict) -> dict:
        body = {
            'modified_img_width': 552,
            'id': solve['id'],
            'mode': 'slide',
            'reply': list({
                'relative_time': i * solve['randlenght'],
                'x': round(solve['maxloc'] / (solve['randlenght'] / (i + 1))),
                'y': solve['tip']} for i in range(solve['randlenght']))
        }

        return self.__client.post('https://%s.tiktokv.com/captcha/verify?%s' % (self.domain, self.__params()),
                                  headers=self.__headers(), json=body, proxies={
            'http': self.proxy,
            'https': self.proxy
        }).json()

    def solve_captcha(self):
        __challenge = self.__get_challenge()
        __captcha_id = __challenge['data']['id']
        __tip_y = __challenge['data']['question']['tip_y']

        solve = self.__solve_captcha(
            __challenge['data']['question']['url1'],
            __challenge['data']['question']['url2'])

        solve.update({
            'id': __captcha_id,
            'tip': __tip_y})

        return self.__post_captcha(solve)


if __name__ == '__main__':
    device = {"Cookies": {"install_id": "7343880353096468257", "store-country-code": "gb", "store-country-code-src": "did", "store-idc": "useast2a", "ttreq": "1$87b87d10044d27028f3e339880fff3eb35ad6f20"}, "Device_Info": {"Mssdk_Endpoint": "mssdk16-normal-useast2a.tiktokv.com", "ab_version": "33.3.2", "ac": "wifi", "ac2": "wifi", "aid": "1233", "app_language": "en", "app_name": "musical_ly", "app_type": "normal", "build_number": "33.3.2", "carrier_region": "GB", "cdid": "3e1bd78b-ea9a-48bd-94be-5457f7d6d967", "channel": "googleplay", "clientuuid": "41d6e1bf-f2db-4018-8b6d-632c56bdfd16", "device_brand": "tcl", "device_id": "7343876928518161952", "device_platform": "android", "device_type": "TCL_R2CIS", "dpi": "320", "google_aid": "565573d1-7508-4805-9011-693f1698169e", "host_abi": "armeabi-v7a", "iid": "7343880353096468257", "language": "en", "locale": "en", "manifest_version_code": "2023303020", "mcc_mnc": "23416",
                                                                                                                                                                                                                             "okhttp_version": "4.2.137.48-tiktok", "op_region": "GB", "openudid": "802ee958cb0b95b4", "os": "android", "os_api": "28", "os_version": "9", "passport-sdk-version": "19", "region": "GB", "req_id": "0855d3b4-72e4-4bc5-8f43-8984daac4685", "resolution": "1080*1920", "ssmix": "a", "support_webview": "1", "sys_region": "GB", "timezone_name": "Europe/London", "timezone_offset": "0", "uoo": "0", "update_version_code": "2023303020", "use_store_region_cookie": "1", "user-agent": "com.zhiliaoapp.musically/2023303020 (Linux; U; Android 9; en_GB; TCL_R2CIS; Build/N2G48H;tt-ok/3.12.13.4-tiktok)", "version_code": "330302", "version_name": "33.3.2"}, "Ri_Report": True, "Seed_Algorithm": 2, "Seed_Token": "MDGiG5zRrnYHJzoxhWsyw9LjnrMvHX5xVDAv9K9bTkaDLk6EFTY6FAR0Qxn4eE3r3+4OLgjGxhSe80KCGqz3BlHEwDuUS7ADd8R+nhcQ8Xsw+8YJDOrjo3oXY3+P7oefZfI=", "is_activated": "success", "secDeviceIdToken": "AQvR9M7RVOwz5Djxa7d6o9DOw"}
    captcha = Captcha(device['Device_Info'], 'XgCPFoWglMDJTM2KNd8AoUjZaO4Qiv52FPu0nfK9s3HS9zw3Jt*QDdAuUb42xO3urXCAlthGbdnueMUdovAGhdYNJFtkPVhYfhfuBROSbzkRFKsLxEIWtOJRWpqE1B7125v9YI9lN5I6SxkDieegMNCtH78pQnLDkF-qfmRpXNkQONVsAojF3MvrV3oAHiJrwQW6KVLgPDW4TBNGTUT1fF4HTd9apIgK7q-r1JzSGufBmiujA5ID2K6xeIUV9HN6xNVjWdt4eXR7xM76kfvr0*oZAT1lpgXiKiVmmYQ5gqVIGIUusY9Np9l3iRueq5rjVJcAq6Tfpyziy47yslkZyfrvWtlzm*L77RpRMjn7L7-36TjGy3YoTFCLmqPSgyjrIj9XIX7Um4IvqOfL5VvbMubOQ6zOdK9SN7*H86xbVzPa22SmNj9tH2HascIl')

    print(captcha.solve_captcha())
