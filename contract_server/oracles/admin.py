from django.contrib import admin

from .models import Oracle
# Register your models here.
class OracleAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'created')

admin.site.register(Oracle, OracleAdmin)