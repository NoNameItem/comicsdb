import os
from PIL import Image
from django.db.models.fields.files import ImageField, ImageFieldFile

__author__ = 'nonameitem'


def _add_thumb(s):
    parts = s.split('.')
    parts.insert(-1, 'thumb')
    parts[-1] = 'png'
    return '.'.join(parts)


class ThumbnailImageFieldFile(ImageFieldFile):
    @property
    def thumb_path(self):
        return _add_thumb(self.path)

    @property
    def thumb_url(self):
        if os.path.exists(_add_thumb(self.path)):
            return _add_thumb(self.url)
        else:
            return self.url

    def save(self, name, content, save=True):
        super().save(name, content, save)
        img = Image.open(self.path)
        img.thumbnail((self.field.thumb_width, self.field.thumb_height), Image.ANTIALIAS)
        img.save(self.thumb_path, 'PNG')

    def delete(self, save=True):
        if os.path.exists(self.thumb_path):
            os.remove(self.thumb_path)
        super().delete(save)


class ThumbnailImageField(ImageField):
    attr_class = ThumbnailImageFieldFile

    def __init__(self, thumb_width=200, thumb_height=200, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.thumb_width = thumb_width
        self.thumb_height = thumb_height
