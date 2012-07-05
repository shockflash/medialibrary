from django.contrib import admin

from medialibrary.models import Category, CategoryAdmin, MediaFile, MediaFileAdmin, Licence, LicenceAdmin

admin.site.register(Category, CategoryAdmin)
admin.site.register(MediaFile, MediaFileAdmin)
admin.site.register(Licence, LicenceAdmin)