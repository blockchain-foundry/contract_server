from django import forms


class NotifyForm(forms.Form):
    tx_hash = forms.CharField(max_length=100)
    subscription_id = forms.CharField(max_length=100)
    notification_id = forms.CharField(max_length=100)


class WatchForm(forms.Form):
    multisig_address = forms.CharField(max_length=100)
    key = forms.CharField(max_length=300)
    callback_url = forms.CharField(max_length=300, required=False)
    oracle_url = forms.CharField(max_length=300)
    receiver_address = forms.CharField(max_length=100, required=False)
