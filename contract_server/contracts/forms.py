import ast
import json

from django import forms


class GenContractRawTxForm(forms.Form):
    source_code = forms.CharField(required=True)
    address = forms.CharField(required=True)
    m = forms.IntegerField(required=True)
    # have to change to dict
    oracles = forms.CharField(required=True)


class ContractFunctionCallFrom(forms.Form):
    from_address = forms.CharField(required=True)
    amount = forms.IntegerField(required=True)
    color = forms.IntegerField(required=True)
    function_name = forms.CharField(required=True)
    function_inputs = forms.CharField(required=True)

    def clean_function_inputs(self):
        function_inputs = self.cleaned_data['function_inputs']
        return ast.literal_eval(function_inputs)


class WithdrawFromContractForm(forms.Form):
    multisig_address = forms.CharField(required=True)
    user_address = forms.CharField(required=True)
    colors = forms.CharField(required=True)
    amounts = forms.CharField(required=True)

    def clean_colors(self):
        colors = self.cleaned_data['colors']
        return ast.literal_eval(colors)

    def clean_amounts(self):
        amounts = self.cleaned_data['amounts']
        return ast.literal_eval(amounts)
