from django import forms


class PublisherForm(forms.Form):
    logo = forms.ImageField(required=False)
    poster = forms.ImageField(required=False)
    desc = forms.CharField(required=False)

