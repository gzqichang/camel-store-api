import os
from io import BytesIO
from PIL import Image
import requests


def download_image(image_url, destination=None, logo=None):
    """ 下载二维码 """
    resp = requests.get(image_url)
    succ = resp.status_code == 200
    data = resp.content
    if succ and data:
        try:
            image = Image.open(BytesIO(data))
            if image.mode not in ('L', 'RGB'):
                if image.mode == 'RGBA':
                    # 透明图片需要加白色底
                    image.load()
                    alpha = image.split()[3]
                    bg = alpha.point(lambda x: 255 - x)
                    image = image.convert('RGB')
                    image.paste((255, 255, 255), None, bg)
                else:
                    image = image.convert('RGB')

            if logo and os.path.exists(logo):
                icon = Image.open(logo)
                img_w, img_h = image.size
                factor = 4
                size_w = int(img_w / factor)
                size_h = int(img_h / factor)

                icon_w, icon_h = icon.size
                if icon_w > size_w:
                    icon_w = size_w
                if icon_h > size_h:
                    icon_h = size_h
                icon = icon.resize((icon_w, icon_h), Image.ANTIALIAS)

                w = int((img_w - icon_w) / 2)
                h = int((img_h - icon_h) / 2)
                icon = icon.convert("RGBA")
                image.paste(icon, (w, h), icon)
            image.save(destination)
        except OSError as e:
            print(e)
