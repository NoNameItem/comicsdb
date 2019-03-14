from django import forms

from comics_db import models


class PublisherForm(forms.Form):
    logo = forms.ImageField(required=False)
    poster = forms.ImageField(required=False)
    desc = forms.CharField(required=False)


class UniverseForm(forms.Form):
    poster = forms.ImageField(required=False)
    desc = forms.CharField(required=False)


class TitleForm(forms.ModelForm):
    class Meta:
        model = models.Title
        fields = ["name", "desc", "title_type", "image"]

