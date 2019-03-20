import os
from PIL import Image
from django.core import checks
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
        f = self.open()
        img = Image.open(f)
        image_format = img.format

        if self.field.thumb_width and self.field.thumb_height:
            img.thumbnail((self.field.thumb_width, self.field.thumb_height), Image.ANTIALIAS)
        elif self.field.thumb_width:
            new_width = self.field.thumb_width
            new_height = int(new_width * img.height / img.width)
            img = img.resize((new_width, new_height), Image.ANTIALIAS)
        elif self.field.thumb_height:
            new_height = self.field.thumb_height
            new_width = int(new_height * img.width / img.height)
            img = img.resize((new_width, new_height), Image.ANTIALIAS)
        img.save(self.thumb_path, image_format)

    def delete(self, save=True):
        if os.path.exists(self.thumb_path):
            os.remove(self.thumb_path)
        super().delete(save)


class ThumbnailImageField(ImageField):
    attr_class = ThumbnailImageFieldFile

    def __init__(self, thumb_width=None, thumb_height=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.thumb_width = thumb_width
        self.thumb_height = thumb_height

    def check(self, **kwargs):
        return [
            *super().check(**kwargs),
            *self._check_thumb_size_attributes(**kwargs),
        ]

    def _check_thumb_size_attributes(self, **kwargs):
        if self.thumb_width is None and self.thumb_height is None:
            return [
                checks.Error(
                    "ThumbnailImageField must define a 'thumb_width' or 'thumb_height' attribute.",
                    obj=self,
                    id='comics_db.E001',
                )
            ]
        else:
            if self.thumb_width and ((not isinstance(self.thumb_width, int) or isinstance(self.thumb_width, bool) or
                                      self.thumb_width <= 0)):
                return [
                    checks.Error(
                        "'thumb_width' must be a positive integer.",
                        obj=self,
                        id='comics_db.E001',
                    )
                ]
            if self.thumb_height and ((not isinstance(self.thumb_height, int) or isinstance(self.thumb_height, bool) or
                                      self.thumb_height <= 0)):
                return [
                    checks.Error(
                        "'thumb_height' must be a positive integer.",
                        obj=self,
                        id='comics_db.E001',
                    )
                ]
        return []
