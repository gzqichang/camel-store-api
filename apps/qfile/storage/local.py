from django.core.files.storage import FileSystemStorage


def save(name, content):
    FileSystemStorage()._save(name, content)
