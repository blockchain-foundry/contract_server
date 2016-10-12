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

    def clean_function_inputs(self):
        function_inputs = json.loads((self.cleaned_data['function_inputs']))
        inputs = []
        for i in function_inputs:
            try:
                type_check(i['type'], i['value'])
            except ValueError:
                raise forms.ValidationError('Can not convert \'{value}\' to type \'{data_type}\''.format(value=i['value'], data_type=i['type']))
        return function_inputs
