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
    image = forms.ImageField(required=False)

    class Meta:
        model = models.Title
        fields = ["name", "desc", "title_type", "image"]


class TitleCreateForm(forms.ModelForm):
    image = forms.ImageField(required=False)

    class Meta:
        model = models.Title
        fields = ["name", "desc", "title_type", "image", "publisher", "universe", "path_key"]


class IssueForm(forms.ModelForm):
    number = forms.IntegerField(required=False)
    main_cover = forms.ImageField(required=False)
    publish_date = forms.DateField(input_formats=['%d.%m.%Y'])

    class Meta:
        model = models.Issue
        fields = ["name", "number", "desc", "publish_date", "main_cover", "title"]

