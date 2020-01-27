import base64
import qrcode
from io import BytesIO


def generate_base64_qr_code(data):
    qr = qrcode.make(data)
    buffer = BytesIO()
    qr.save(buffer)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")
