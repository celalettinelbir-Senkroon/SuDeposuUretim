docker run --name postgres-django  -e POSTGRES_DB=senkroon -e POSTGRES_USER=senkroon  -e POSTGRES_PASSWORD=senkroon789654. -p 5432:5432 -d postgres
#veritabanı kadlırmak için gerekli docker fokyonu yukarıdaki gibidir.

# 1. Migration dosyalarını oluştur (eğer oluşmadıysa)
python manage.py makemigrations customers
python manage.py makemigrations management

# 2. Sadece SHARED_APPS içindeki tabloları public şemaya basar
python manage.py migrate_schemas --shared
python manage.py migrate_schemas

python manage.py runserver

# JWT login / refresh
# POST /api/auth/login/  -> access + refresh token dondurur
# POST /api/auth/refresh/ -> yeni access token dondurur
# Authorization header: Bearer <access_token>



# Ekomaxi şeması için admin oluştur
./manage.py tenant_command loaddata --schema=customer1




