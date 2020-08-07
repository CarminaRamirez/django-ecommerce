from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget


PAYMENT_CHOICES = (
    ('S', 'Stripe'),
    ('P', 'PayPal')
) # Opciones de pago


class CheckoutForm(forms.Form): # formulario de registro de pago
    shipping_address = forms.CharField(required=False) # dirección de envío es un campo char
    shipping_address2 = forms.CharField(required=False) # lo mismo pero con segunda dirección de envío
    shipping_country = CountryField(blank_label='(selecciona pais)').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={
            'class': 'custom-select d-block w-100',
        })) # País de envío es un campo "Country", en el espacio en blanco tiene escrito "(selecciona pais)" y en este campo hay un widget que
            # contiene opciones para elegir de la clase 'custom-select d-block w-100'
    shipping_zip = forms.CharField(required=False) # Código postal

    billing_address = forms.CharField(required=False) # lo mismo que arriba pero con direccion de facturación
    billing_address2 = forms.CharField(required=False)
    billing_country = CountryField(blank_label='(select country)').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={
            'class': 'custom-select d-block w-100',
        }))
    billing_zip = forms.CharField(required=False)

    same_billing_address = forms.BooleanField(required=False) # campo booleano, misma direccion de facturación. El parámetro indica que no es
                                                              # requerido necesariamente
    set_default_shipping = forms.BooleanField(required=False) # establecer envío por defecto (campo booleano también)
    use_default_shipping = forms.BooleanField(required=False) # usar envío por defecto
    set_default_billing = forms.BooleanField(required=False) # establecer facturación por defecto
    use_default_billing = forms.BooleanField(required=False) # usar facturación por defecto

    payment_option = forms.ChoiceField(
        widget=forms.RadioSelect, choices=PAYMENT_CHOICES) # opcion de pago es un campo tipo opción con un widget de RadioSelect, sus opciones son
                                                           # las que se encuentran en PAYMENT_CHOICES


class CouponForm(forms.Form): # Formulario del cupón
    code = forms.CharField(widget=forms.TextInput(attrs={ #ver bien tema de widget
        'class': 'form-control',
        'placeholder': 'Código de promo',
        'aria-label': 'Recipient\'s username',
        'aria-describedby': 'basic-addon2'
    })) # la variable code contiene un form de tipo CharField, con un widget de parámetro. El widget (en este caso) es un input que contiene un attrs
        # (Clases sin repetitivo) de parámetro


class RefundForm(forms.Form): # formulario de devolución
    ref_code = forms.CharField() # campo de un formulario tipo char
    message = forms.CharField(widget=forms.Textarea(attrs={
        'rows': 4
    })) # message contiene un campo char con un widget (área de texto) de 4 filas
    email = forms.EmailField() # email es un campo del tipo Email


class PaymentForm(forms.Form): # formulario de pago
    stripeToken = forms.CharField(required=False)
    save = forms.BooleanField(required=False)
    use_default = forms.BooleanField(required=False)

class InicioSesionForm(forms.Form):
    nombreUsuario = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Nombre de usuario'
    }))
    #email = forms.EmailField()
    contraseña = forms.CharField(widget=forms.PasswordInput)
    #recordar = forms.BooleanField()