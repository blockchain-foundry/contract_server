from django import forms


class NotifyForm(forms.Form):
    tx_hash = forms.CharField(max_length=100)
    subscription_id = forms.CharField(max_length=100)
    notification_id = forms.CharField(max_length=100)
