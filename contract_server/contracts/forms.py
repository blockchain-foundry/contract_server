import json

from django import forms


def type_check(data_type, value):
    if data_type == 'string':
        return str(value)
    elif data_type == 'int':
        return int(value)

class ContractFunctionPostForm(forms.Form):
    function_id = forms.IntegerField(min_value=1)
    function_inputs = forms.CharField()
    from_address = forms.CharField(required=False)
    to_address = forms.CharField(required=False)
    amount = forms.IntegerField(required=False, min_value=1)
    color = forms.IntegerField(required=False, min_value=0)

    is_payment = False

    def clean_function_inputs(self):
        function_inputs = json.loads((self.cleaned_data['function_inputs']))
        inputs = []
        for i in function_inputs:
            try:
                type_check(i['type'], i['value'])
            except ValueError:
                raise forms.ValidationError('Can not convert \'{value}\' to type \'{data_type}\''.format(value=i['value'], data_type=i['type']))
        return function_inputs

    def clean(self):
        super(ContractFunctionPostForm, self).clean()
        from_address = self.cleaned_data.get('from_address')
        to_address = self.cleaned_data.get('to_address')
        amount = self.cleaned_data.get('amount')
        color = self.cleaned_data.get('color')

        if from_address and to_address and amount and color:
            self.is_payment = True
