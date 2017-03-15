from django import forms


class WatchForm(forms.Form):
    multisig_address = forms.CharField(max_length=100)
    event_name = forms.CharField(max_length=300)
    contract_address = forms.CharField(max_length=100, required=False)
