"""
    author: wilslee
    email: lwf@gzqichang.com

    清除 django 项目目录下所有 app 的 migrations 文件

    运行: python manage.py clearmigrationsfile

"""
import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):

    def handle(self, *args, **options):
        for root, sub_folders, files in os.walk(settings.BASE_DIR):
            if 'migrations' in sub_folders:
                migrations_dir = os.path.join(root, 'migrations')
                print('clear: ', migrations_dir)
                for m_root, m_sub_folders, m_files in os.walk(migrations_dir):
                    for f in m_files:
                        if f != '__init__.py':
                            os.remove(os.path.join(m_root, f))
        print("Clear Done...")
