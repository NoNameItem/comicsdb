from django import forms

from comics_db import models


class PublisherForm(forms.ModelForm):
    logo = forms.ImageField(required=False)
    poster = forms.ImageField(required=False)

    class Meta:
        model = models.Publisher
        fields = ["logo", "poster", "desc"]


class UniverseForm(forms.ModelForm):
    poster = forms.ImageField(required=False)

    class Meta:
        model = models.Universe
        fields = ["poster", "desc"]


class TitleForm(forms.ModelForm):
    image = forms.ImageField(required=False)

    class Meta:
        model = models.Title
        fields = ["name", "desc", "title_type", "image", "api_image", "start_year", "end_year"]


class TitleCreateForm(forms.ModelForm):
    image = forms.ImageField(required=False)

    class Meta:
        model = models.Title
        fields = ["name", "desc", "title_type", "image", "publisher", "universe", "path_key", "api_image", "start_year",
                  "end_year"]


class IssueForm(forms.ModelForm):
    number = forms.IntegerField(required=False)
    main_cover = forms.ImageField(required=False)
    publish_date = forms.DateField(input_formats=['%d.%m.%Y'])

    class Meta:
        model = models.Issue
        fields = ["name", "number", "desc", "publish_date", "main_cover", "title", "api_image"]


class ReadingListForm(forms.ModelForm):
    class Meta:
        model = models.ReadingList
        fields = ["name", "desc", "owner", "sorting"]


class CreatorForm(forms.ModelForm):
    photo = forms.ImageField(required=False)
    image = forms.ImageField(required=False)

    class Meta:
        model = models.Creator
        fields = ["name", "bio", "photo", "image", "api_image"]


class CharacterForm(forms.ModelForm):
    image = forms.ImageField(required=False)

    class Meta:
        model = models.Character
        fields = ["name", "desc", "image", "publisher", "api_image"]


class EventForm(forms.ModelForm):
    image = forms.ImageField(required=False)
    start = forms.DateField(input_formats=['%d.%m.%Y'], required=False)
    end = forms.DateField(input_formats=['%d.%m.%Y'], required=False)

    class Meta:
        model = models.Event
        fields = ["name", "desc", "image", "publisher", "start", "end", "api_image"]
