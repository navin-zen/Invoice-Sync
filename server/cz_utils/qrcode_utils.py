import base64
import io

import cv2
import numpy as np
import qrcode
import requests
import six

GOOGLE_CHARTS_URL = "https://chart.googleapis.com/chart"


def str_to_qrcode(s, width=100, height=100, chld="Q|1"):
    """
    Converts data and returns URL to QR Code image.

    width and height are those of the QR code to be generated (in pixels)

    See https://developers.google.com/chart/infographics/docs/qr_codes

    """
    params = {
        "cht": "qr",
        "chs": f"{width}x{height}",
        "chl": s,
        "chld": chld,
    }
    v = f"{GOOGLE_CHARTS_URL}?{six.moves.urllib.parse.urlencode(params)}"
    return v


def str_to_qrcode_img(s, *, width=100, height=100, format="png"):
    """
    Return QR image bytes in the specified format
    """
    img = qrcode.make(s)
    img._img = img._img.resize((width, height))
    f = io.BytesIO()
    img.save(f, format=format)
    return f.getvalue()


def str_to_qrcode_local(s, width=100, height=100, chld="Q|1"):
    """
    Converts data and returns URL to QR Code image.

    width and height are those of the QR code to be generated (in pixels)

    See https://pypi.org/project/qrcode/

    Returns a base64 encoded png image that can be used within <img src="...">
    """
    imgbytes = str_to_qrcode_img(s, width=width, height=height, format="png")
    return "data:image/png;charset=utf-8;base64,{}".format(base64.b64encode(imgbytes).decode("ascii"))


def url_to_bmp_image(url):
    response = requests.get(url)
    if response.status_code == 200:
        image_data = np.frombuffer(response.content, np.uint8)
        image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
    else:
        return None
    is_success, bmp_image_data = cv2.imencode(".bmp", image)
    if not is_success:
        return None
    return bmp_image_data.tobytes()
