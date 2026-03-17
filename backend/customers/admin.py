from django.contrib import admin
from django.db import connection
from django_tenants.admin import TenantAdminMixin
from .models import Client, Domain

# Domain (Subdomain) bilgilerini Şirket ile aynı ekranda görebilmek için
class DomainInline(admin.TabularInline):
    model = Domain
    max_num = 1
    can_delete = False

# Sadece 'public' şemasındayken bu alanı gösterelim
if connection.schema_name == 'public':
    @admin.register(Client)
    class ClientAdmin(TenantAdminMixin, admin.ModelAdmin):
        list_display = ('name', 'schema_name', 'created_on')
        # Şema ismini elle değiştirmek tehlikeli olabilir, readonly yapabiliriz
        prepopulated_fields = {'schema_name': ('name',)} 
        inlines = [DomainInline]
        
        def save_model(self, request, obj, form, change):
            # Şema ismi boşluk içermemeli ve küçük harf olmalı
            obj.schema_name = obj.schema_name.lower().replace(" ", "_")
            super().save_model(request, obj, form, change)