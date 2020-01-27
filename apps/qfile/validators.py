import os


class FileValidator(object):
    FILE_TYPE = [
        ('image', ('png', 'jpg', 'jpeg', 'gif', 'bmp', 'img', 'image')),
        ('xls', ('xlsx', 'xlsm', 'xltx', 'xltm', 'xlsb', 'xlam', 'xls', 'xls')),
        ('doc', ('docx', 'docm', 'dotx', 'dotm', 'doc', 'doc')),
        ('ppt', ('pptx', 'pptm', 'ppt', 'ppsx', 'ppsm', 'potx', 'potm', 'ppt')),
        ('pdf', ('pdf', 'pdf')),
        ('txt', ('txt', 'txt')),
        ('tar', ('rar', 'zip', 'gz', 'bz2', 'tar', 'tar')),
    ]

    @classmethod
    def get_file_attr(cls, suffix):
        for attr, suffix_tuple in cls.FILE_TYPE:
            if suffix in suffix_tuple:
                return attr
        return 'other'

    @classmethod
    def generate_file_name(cls, file_str):
        name, suffix = os.path.splitext(os.path.basename(file_str))

        return "{}-{}".format(
            "".join(name.split(" ")),
            cls.get_file_attr(suffix),
        )

    @classmethod
    def get_file_suffix(cls, file_str):
        _, suffix = os.path.splitext(os.path.basename(file_str))
        return suffix.strip(".")
