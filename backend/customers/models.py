from django.db import models

# Create your models here.
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin

class Client(TenantMixin):
    name = models.CharField(max_length=100)
    created_on = models.DateField(auto_now_add=True)

    # Bu alan true ise, bu "public" şemadır (ana siten)
    auto_create_schema = True
    # Admin'den silindiğinde ilgili PostgreSQL şemasını da DROP eder
    auto_drop_schema = True

class Domain(DomainMixin):
    pass