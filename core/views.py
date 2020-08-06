import random
import string

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.generic import ListView, DetailView, View

from .forms import CheckoutForm, CouponForm, RefundForm, PaymentForm
from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund, UserProfile
from django.db.models import Q
from django.core.paginator import Paginator

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


def products(request):
    context = {
        'items': Item.objects.all()
    }
    return render(request, "products.html", context)


def is_valid_form(valores):
    valido = True
    for campo in valores:
        if campo == '':
            valido = False
    return valido


class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False) # Guarda en order la orden del usuario que está ingresando y que no fue ordenada
            form = CheckoutForm() # Formulario de chechout
            context = {
                'form': form,
                'couponform': CouponForm(),
                'order': order,
                'DISPLAY_COUPON_FORM': True
            } # contexto para la plantilla

            shipping_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='S',
                default=True
            ) #objetos de tipo dirección filtrados por el usuario correspondiente, del tipo envío, por defecto
            if shipping_address_qs.exists(): # si existen objetos de lo anterior
                context.update(
                    {'default_shipping_address': shipping_address_qs[0]}) # actualiza el contexto agregandole el
                                                                          # el primer objeto de la lista

            billing_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='B',
                default=True
            ) # #objetos de tipo dirección filtrados por el usuario correspondiente, del tipo facturación, por defecto
            if billing_address_qs.exists(): # si existen objetos de lo anterior
                context.update(
                    {'default_billing_address': billing_address_qs[0]}) # actualiza el contexto agregandole el
                                                                        # el primer objeto de la lista
            return render(self.request, "checkout.html", context) # retorna el render con el request, la plantilla,
                                                                  # y el contexto que aplica a la plantilla
        except ObjectDoesNotExist: # si el objeto no existe
            messages.info(self.request, "No tienes una orden activa") # Mensaje de error
            return redirect("core:checkout") # redirecciona a la url que contiene como name: "checkout", de la app "core"

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None) # formulario de checkeo, ver los parámetros
        try:
            order = Order.objects.get(user=self.request.user, ordered=False) # orden del usuario sin ordenar
            if form.is_valid(): # si el formulario es valido

                use_default_shipping = form.cleaned_data.get(
                    'use_default_shipping') # usar el envío por defecto contiene los datos limpios del formulario
                if use_default_shipping: # si usa el envío por defecto
                    print("Usando la dirección de envío por defecto") #imprime
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='S',
                        default=True
                    ) # contiene las direcciones filtradas por el usuario correspondiente, de tipo envío, por defecto
                    if address_qs.exists(): # si hay algún objeto con las condiciones anteriores
                        shipping_address = address_qs[0] # guarda en esta variable el primer elemento de la lista
                        order.shipping_address = shipping_address # guarda en el atributo de la orden la dirección de envio
                        order.save() # guarda lo modificado en la orden
                    else: # si no hay objetos
                        messages.info(
                            self.request, "Direcciones de envío por defecto no disponibles")
                        return redirect('core:checkout')
                else: # si no usa el envío por defecto
                    print("Usuario está ingresando una dirección de envío nueva")
                    shipping_address1 = form.cleaned_data.get(
                        'shipping_address') # dirección de envío 1, datos limpios del form
                    shipping_address2 = form.cleaned_data.get(
                        'shipping_address2') # dirección de envío 2
                    shipping_country = form.cleaned_data.get(
                        'shipping_country') # país de envío
                    shipping_zip = form.cleaned_data.get('shipping_zip') # código postal de envío

                    if is_valid_form([shipping_address1, shipping_country, shipping_zip]): # si el form es valido con los
                                                                                           # atributos pasados por parámetro
                        shipping_address = Address(
                            user=self.request.user,
                            street_address=shipping_address1,
                            apartment_address=shipping_address2,
                            country=shipping_country,
                            zip=shipping_zip,
                            address_type='S'
                        ) # crea una direccion
                        shipping_address.save() # guarda la direccion de envio

                        order.shipping_address = shipping_address
                        order.save() # guarda la dirección de envío en la orden

                        set_default_shipping = form.cleaned_data.get(
                            'set_default_shipping') # establece el envío por defecto con los datos limpios del formulario
                        if set_default_shipping: # si hay envio por defecto
                            shipping_address.default = True # direccion de envio por defecto en true
                            shipping_address.save() # guarda

                    else: # si el formulario es inválido
                        messages.info(
                            self.request, "Por favor completa en los campos de dirección de envío requeridos")

                use_default_billing = form.cleaned_data.get(
                    'use_default_billing') # usa la facturación por defecto
                same_billing_address = form.cleaned_data.get(
                    'same_billing_address') # misma dirección de facturación

                if same_billing_address: # si es la misma
                    billing_address = shipping_address # completa la dirección de facturación con la dirección de envío
                    billing_address.pk = None # no tiene clave primaria
                    billing_address.save() # guarda
                    billing_address.address_type = 'B' # tipo de direccion
                    billing_address.save() # guarda
                    order.billing_address = billing_address # direccion de facturacion de la orden
                    order.save() # guarda la orden

                elif use_default_billing: # si usa la facturación por defecto
                    print("Usar la dirección de facturación por defecto")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='B',
                        default=True
                    )
                    if address_qs.exists():
                        billing_address = address_qs[0]
                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default billing address available")
                        return redirect('core:checkout')
                else:
                    print("User is entering a new billing address")
                    billing_address1 = form.cleaned_data.get(
                        'billing_address')
                    billing_address2 = form.cleaned_data.get(
                        'billing_address2')
                    billing_country = form.cleaned_data.get(
                        'billing_country')
                    billing_zip = form.cleaned_data.get('billing_zip')

                    if is_valid_form([billing_address1, billing_country, billing_zip]):
                        billing_address = Address(
                            user=self.request.user,
                            street_address=billing_address1,
                            apartment_address=billing_address2,
                            country=billing_country,
                            zip=billing_zip,
                            address_type='B'
                        )
                        billing_address.save()

                        order.billing_address = billing_address
                        order.save()

                        set_default_billing = form.cleaned_data.get(
                            'set_default_billing')
                        if set_default_billing:
                            billing_address.default = True
                            billing_address.save()

                    else:
                        messages.info(
                            self.request, "Please fill in the required billing address fields")

                payment_option = form.cleaned_data.get('payment_option')

                if payment_option == 'S':
                    return redirect('core:payment', payment_option='stripe')
                elif payment_option == 'P':
                    return redirect('core:payment', payment_option='paypal')
                else:
                    messages.warning(
                        self.request, "Invalid payment option selected")
                    return redirect('core:checkout')
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("core:order-summary")


class PaymentView(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        if order.billing_address:
            context = {
                'order': order,
                'DISPLAY_COUPON_FORM': False,
                'STRIPE_PUBLIC_KEY' : settings.STRIPE_PUBLIC_KEY
            }
            userprofile = self.request.user.userprofile
            if userprofile.one_click_purchasing:
                # fetch the users card list
                cards = stripe.Customer.list_sources(
                    userprofile.stripe_customer_id,
                    limit=3,
                    object='card'
                )
                card_list = cards['data']
                if len(card_list) > 0:
                    # update the context with the default card
                    context.update({
                        'card': card_list[0]
                    })
            return render(self.request, "payment.html", context)
        else:
            messages.warning(
                self.request, "You have not added a billing address")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        form = PaymentForm(self.request.POST)
        userprofile = UserProfile.objects.get(user=self.request.user)
        if form.is_valid():
            token = form.cleaned_data.get('stripeToken')
            save = form.cleaned_data.get('save')
            use_default = form.cleaned_data.get('use_default')

            if save:
                if userprofile.stripe_customer_id != '' and userprofile.stripe_customer_id is not None:
                    customer = stripe.Customer.retrieve(
                        userprofile.stripe_customer_id)
                    customer.sources.create(source=token)

                else:
                    customer = stripe.Customer.create(
                        email=self.request.user.email,
                    )
                    customer.sources.create(source=token)
                    userprofile.stripe_customer_id = customer['id']
                    userprofile.one_click_purchasing = True
                    userprofile.save()

            amount = int(order.get_total() * 100)

            try:

                if use_default or save:
                    # charge the customer because we cannot charge the token more than once
                    charge = stripe.Charge.create(
                        amount=amount,  # cents
                        currency="usd",
                        customer=userprofile.stripe_customer_id
                    )
                else:
                    # charge once off on the token
                    charge = stripe.Charge.create(
                        amount=amount,  # cents
                        currency="usd",
                        source=token
                    )

                # create the payment
                payment = Payment()
                payment.stripe_charge_id = charge['id']
                payment.user = self.request.user
                payment.amount = order.get_total()
                payment.save()

                # assign the payment to the order

                order_items = order.items.all()
                order_items.update(ordered=True)
                for item in order_items:
                    item.save()

                order.ordered = True
                order.payment = payment
                order.ref_code = create_ref_code()
                order.save()

                messages.success(self.request, "Your order was successful!")
                return redirect("/")

            except stripe.error.CardError as e:
                body = e.json_body
                err = body.get('error', {})
                messages.warning(self.request, f"{err.get('message')}")
                return redirect("/")

            except stripe.error.RateLimitError as e:
                # Too many requests made to the API too quickly
                messages.warning(self.request, "Rate limit error")
                return redirect("/")

            except stripe.error.InvalidRequestError as e:
                # Invalid parameters were supplied to Stripe's API
                print(e)
                messages.warning(self.request, "Invalid parameters")
                return redirect("/")

            except stripe.error.AuthenticationError as e:
                # Authentication with Stripe's API failed
                # (maybe you changed API keys recently)
                messages.warning(self.request, "Not authenticated")
                return redirect("/")

            except stripe.error.APIConnectionError as e:
                # Network communication with Stripe failed
                messages.warning(self.request, "Network error")
                return redirect("/")

            except stripe.error.StripeError as e:
                # Display a very generic error to the user, and maybe send
                # yourself an email
                messages.warning(
                    self.request, "Something went wrong. You were not charged. Please try again.")
                return redirect("/")

            except Exception as e:
                # send an email to ourselves
                messages.warning(
                    self.request, "A serious error occurred. We have been notifed.")
                return redirect("/")

        messages.warning(self.request, "Invalid data received")
        return redirect("/payment/stripe/")

def homeview(request):
    queryset= request.GET.get("buscar")
    if queryset:
        items = Item.objects.filter(
            Q(title__icontains = queryset) |
            Q(description__icontains = queryset)
        ).distinct()
    else:
        items = Item.objects.all()
    paginator = Paginator(items, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'object_list': items,
        'page_number': page_number,
        'page_obj': page_obj
    }
    return render(request, "home.html", context)

#class HomeView(ListView):
#    model = Item
#    paginate_by = 10
#    template_name = "home.html"
#    def get(self, *args, **kwargs):
#        queryset= self.request.GET.get("buscar")
#        print(queryset)
#        if queryset:
#            items = Item.objects.filter(
#                Q(title = queryset) |
#                Q(description = queryset) |
#                Q(category = queryset)
#            ).distinct()
#        else:
#            items = Item.objects.all()
#        context = {
#            'object_list': items
#        }
        #try:
        #    order = Order.objects.get(user=self.request.user, ordered=False)
        #    context = {
        #        'object': order
        #    }
        #    return render(self.request, 'order_summary.html', context)
        #except ObjectDoesNotExist:
        #    messages.warning(self.request, "You do not have an active order")
        #    return redirect("/")
        #return render(self.request, "home.html", context)


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, 'order_summary.html', context)
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("/")

def item_detail_view(request, slug):
    context={
        'object': Item.objects.get(slug=slug)
    }
    print(context)
    return render(request, 'product.html', context)

#class ItemDetailView(DetailView):
#    model = Item
#    template_name = "product.html"


@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            order.items.add(order_item)
            messages.info(request, "This item was added to your cart.")
            return redirect("core:order-summary")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart.")
        return redirect("core:order-summary")


@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item)
            order_item.delete()
            messages.info(request, "This item was removed from your cart.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug)


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug)


def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request, "This coupon does not exist")
        return redirect("core:checkout")


class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(
                    user=self.request.user, ordered=False)
                order.coupon = get_coupon(self.request, code)
                order.save()
                messages.success(self.request, "Successfully added coupon")
                return redirect("core:checkout")
            except ObjectDoesNotExist:
                messages.info(self.request, "You do not have an active order")
                return redirect("core:checkout")


class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form': form
        }
        return render(self.request, "request_refund.html", context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            # edit the order
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                # store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.info(self.request, "Your request was received.")
                return redirect("core:request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order does not exist.")
                return redirect("core:request-refund")
