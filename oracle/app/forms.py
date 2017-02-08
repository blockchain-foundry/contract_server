from django import forms


class SignForm(forms.Form):
    tx = forms.CharField(required=True)
    script = forms.CharField(required=True)
    input_index = forms.IntegerField(required=True)
    user_address = forms.CharField(required=True)
    multisig_address = forms.CharField(required=True)
    color_id = forms.CharField(required=True)
    amount = forms.IntegerField(required=True)
