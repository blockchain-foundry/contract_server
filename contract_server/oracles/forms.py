from django import forms


class RegisterOracleForm(forms.Form):
    name = forms.CharField(required=True, max_length=100)
    url = forms.URLField(required=True)
