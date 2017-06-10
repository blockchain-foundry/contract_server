from django.contrib import admin

from .models import Contract, MultisigAddress


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('state_multisig_address', 'contract_multisig_address', 'is_deployed', 'created')


@admin.register(MultisigAddress)
class MultisigAddressAdmin(admin.ModelAdmin):
    list_display = ('address', 'created', 'is_state_multisig', 'script')