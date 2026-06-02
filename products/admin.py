from django.contrib import admin

from products.models import ProductCategory, Product, Basket

admin.site.register(ProductCategory)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'quantity')
    fields = ('name', 'description', 'category', ('price', 'quantity'), 'image')
    readonly_fields = ('description',)
    search_fields = ('name',)
    ordering = ('name',)

class BasketAdmin(admin.TabularInline):
    model = Basket
    fields = ('product', 'quantity', 'created_timestamp')
    readonly_fields = ('created_timestamp',)
    extra = 0