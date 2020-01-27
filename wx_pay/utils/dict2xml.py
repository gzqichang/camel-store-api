# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import six

from wechatpy.utils import to_text


def dict_to_xml(data):
    xml = ['<xml>\n']
    for k in sorted(data):
        # use sorted to avoid test error on Py3k
        v = data[k]
        if isinstance(v, six.integer_types) or v.isdigit():
            xml.append('<{0}>{1}</{0}>\n'.format(to_text(k), to_text(v)))
        else:
            xml.append(
                '<{0}><![CDATA[{1}]]></{0}>\n'.format(to_text(k), to_text(v))
            )
    xml.append('</xml>')
    return ''.join(xml)

