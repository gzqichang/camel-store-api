from rest_framework_xml.parsers import XMLParser


class TextTypeXMLParser(XMLParser):
    media_type = 'text/xml'