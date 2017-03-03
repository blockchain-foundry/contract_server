from django import forms

class AskForm(forms.Form):
    url = forms.CharField(required=True)
    contract_address = forms.CharField(required=True)
    sender_address = forms.CharField(required=True)


class CryForm(forms.Form):
    signed_tx = forms.CharField(required=True)
