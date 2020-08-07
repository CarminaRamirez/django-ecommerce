from django.db.models.signals import post_save
from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.shortcuts import reverse
from django_countries.fields import CountryField


CATEGORY_CHOICES = (
    ('S', 'remera'),
    ('SW', 'Ropa deportiva'),
    ('OW', 'Ropa de salir')
) # opciones de categoría

LABEL_CHOICES = (
    ('P', 'primario'),
    ('S', 'secundario'),
    ('D', 'peligroso')
) # opciones de label

ADDRESS_CHOICES = (
    ('B', 'Envío'),
    ('S', 'Facturación'),
) # opciones de dirección


class PerfilDeUsuario(models.Model): # Perfil de usuario
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE) # Usuario contiene el modelo con relación uno a uno de 'AUTH_USER_MODEL' y 'CASCADE'
    stripe_customer_id = models.CharField(max_length=50, blank=True, null=True) # id del cliente es un campo char con parámetros de diferentes
                                                                                # atributos
    one_click_purchasing = models.BooleanField(default=False) # compra con un click, campo booleano, el valor por defecto es Falso

    def __str__(self): # función str, retorna el nombre del usuario
        return self.usuario.username


class Item(models.Model): # clase item (producto) con sus atributos
    title = models.CharField(max_length=100)
    price = models.FloatField()
    discount_price = models.FloatField(blank=True, null=True) # precio con descuento, puede no tener valor (null), blanck=true indica que el campo
                                                              # no es obligatorio
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=2) # categoria es un campo char que contiene opciones y
    label = models.CharField(choices=LABEL_CHOICES, max_length=1) # el max_length contempla la "clave" de las opciones, por eso es = 1
    slug = models.SlugField() # lo que se guarda en slug se utiliza para la url de ese item
    description = models.TextField() # descripcion
    image = models.ImageField() # imagen

    def __str__(self): # función que devuelve el titulo del item
        return self.title

    def get_absolute_url(self): # retorna la url completa con el slug de este producto
        return reverse("core:product", kwargs={
            'slug': self.slug
        })

    def get_add_to_cart_url(self): # retorna la url de agregar al carrito
        return reverse("core:add-to-cart", kwargs={
            'slug': self.slug
        })

    def get_remove_from_cart_url(self): # retorna la url de eliminar del carrito
        return reverse("core:remove-from-cart", kwargs={
            'slug': self.slug
        })


class OrderItem(models.Model): # modelo de orden del item
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE) # usuario con clave foranea de los modelos 'AUTH_USER_MODEL' y 'CASCADE'
    ordered = models.BooleanField(default=False) # ordenado, booleano
    item = models.ForeignKey(Item, on_delete=models.CASCADE) # item de clave foranea entre 'Item' y 'CASCADE'
    quantity = models.IntegerField(default=1) # cantidad de productos, como defecto = 1

    def __str__(self): # retorna un string con las variables cantidad y titulo (utiliza f al comienzo del string para poder iterar con las variables)
        return f"{self.quantity} of {self.item.title}"

    def get_total_item_price(self): # retorna el total del precio del item (precio*cantidad)
        return self.quantity * self.item.price

    def get_total_discount_item_price(self): # retorna el total del precio de descuento del item (precio*cantidad)
        return self.quantity * self.item.discount_price

    def get_amount_saved(self): # retorna la cantidad ahorrada con el precio de descuento
        return self.get_total_item_price() - self.get_total_discount_item_price()

    def get_final_price(self): # precio final
        if self.item.discount_price:
            return self.get_total_discount_item_price()
        return self.get_total_item_price()


class Order(models.Model): # orden
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    ref_code = models.CharField(max_length=20, blank=True, null=True)
    items = models.ManyToManyField(OrderItem)
    start_date = models.DateTimeField(auto_now_add=True)
    ordered_date = models.DateTimeField()
    ordered = models.BooleanField(default=False)
    shipping_address = models.ForeignKey(
        'Address', related_name='shipping_address', on_delete=models.SET_NULL, blank=True, null=True)
    billing_address = models.ForeignKey(
        'Address', related_name='billing_address', on_delete=models.SET_NULL, blank=True, null=True)
    payment = models.ForeignKey(
        'Payment', on_delete=models.SET_NULL, blank=True, null=True)
    coupon = models.ForeignKey(
        'Coupon', on_delete=models.SET_NULL, blank=True, null=True)
    being_delivered = models.BooleanField(default=False)
    received = models.BooleanField(default=False)
    refund_requested = models.BooleanField(default=False)
    refund_granted = models.BooleanField(default=False)

    '''
    1. Item added to cart
    2. Adding a billing address
    (Failed checkout)
    3. Payment
    (Preprocessing, processing, packaging etc.)
    4. Being delivered
    5. Received
    6. Refunds
    '''

    def __str__(self):
        return self.user.username

    def get_total(self):
        total = 0
        for order_item in self.items.all():
            total += order_item.get_final_price()
        if self.coupon:
            total -= self.coupon.amount
        return total


class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    street_address = models.CharField(max_length=100)
    apartment_address = models.CharField(max_length=100)
    country = CountryField(multiple=False)
    zip = models.CharField(max_length=100)
    address_type = models.CharField(max_length=1, choices=ADDRESS_CHOICES)
    default = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name_plural = 'Addresses'


class Payment(models.Model):
    stripe_charge_id = models.CharField(max_length=50)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.SET_NULL, blank=True, null=True)
    amount = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username


class Coupon(models.Model):
    code = models.CharField(max_length=15)
    amount = models.FloatField()

    def __str__(self):
        return self.code


class Refund(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    reason = models.TextField()
    accepted = models.BooleanField(default=False)
    email = models.EmailField()

    def __str__(self):
        return f"{self.pk}"


def userprofile_receiver(sender, instance, created, *args, **kwargs):
    if created:
        userprofile = PerfilDeUsuario.objects.create(user=instance)


post_save.connect(userprofile_receiver, sender=settings.AUTH_USER_MODEL)
