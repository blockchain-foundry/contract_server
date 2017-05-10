from django import forms


class ProposeForm(forms.Form):
    source_code = forms.CharField(required=False)
    conditions = forms.CharField(required=False)


class SignForm(forms.Form):
    raw_tx = forms.CharField(required=True)
    script = forms.CharField(required=True)
    input_index = forms.IntegerField(required=True)
    sender_address = forms.CharField(required=True)
    multisig_address = forms.CharField(required=True)
    color = forms.CharField(required=True)
    amount = forms.IntegerField(required=True)


class MultisigAddrFrom(forms.Form):
    pubkey = forms.CharField(required=True)
    multisig_address = forms.CharField(required=True)


class NotifyForm(forms.Form):
    tx_hash = forms.CharField(max_length=100)
    subscription_id = forms.CharField(max_length=100)
    notification_id = forms.CharField(max_length=100)
