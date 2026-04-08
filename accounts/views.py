from django.shortcuts import redirect, render
from django.forms import inlineformset_factory
from django.http import HttpResponse

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie

from .forms import OrderForm, CreateUserForm
from .models import Customer, Order, Product
from .filters import OrderFilter
from .decorators import unauthenticated_user, allowed_users, admin_only


# ================= REGISTER =================
@unauthenticated_user
def registerPage(request):
    form = CreateUserForm()

    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')

            # Assign group
            group, created = Group.objects.get_or_create(name='customer')
            user.groups.add(group)

            # ✅ FIXED: create only once
            Customer.objects.create(
                user=user,
                name=username,
                email=user.email
            )

            messages.success(request, 'Account was created for ' + username)
            return redirect('login')

    context = {'form': form}
    return render(request, 'accounts/register.html', context)


# ================= LOGIN =================
@ensure_csrf_cookie
@unauthenticated_user
def loginPage(request):

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # ✅ FIXED redirect logic
            if user.is_superuser:
                return redirect('home')
            else:
                return redirect('user-page')

        else:
            messages.error(request, 'Username OR password is incorrect')

    return render(request, 'accounts/login.html')


# ================= LOGOUT =================
def logoutUser(request):
    logout(request)
    return redirect('login')


# ================= ADMIN DASHBOARD =================
@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
@admin_only
def home(request):
    orders = Order.objects.all()
    customers = Customer.objects.all()

    total_customers = customers.count()
    total_orders = orders.count()
    delivered = orders.filter(status='Delivered').count()
    pending = orders.filter(status='Pending').count()

    context = {
        'orders': orders,
        'customers': customers,
        'total_customers': total_customers,
        'total_orders': total_orders,
        'delivered': delivered,
        'pending': pending
    }

    return render(request, 'accounts/dashboard.html', context)


# ================= USER PAGE =================
@login_required(login_url='login')
def userPage(request):
    # ✅ FIX: safe customer access
    customer, created = Customer.objects.get_or_create(user=request.user)

    orders = customer.order_set.all()

    total_orders = orders.count()
    delivered = orders.filter(status='Delivered').count()
    pending = orders.filter(status='Pending').count()

    context = {
        'customer': customer,
        'orders': orders[:3],
        'total_orders': total_orders,
        'delivered': delivered,
        'pending': pending
    }

    return render(request, 'accounts/user.html', context)


# ================= ACCOUNT SETTINGS =================
@login_required(login_url='login')
@allowed_users(allowed_roles=['customer'])
def accountSettings(request):
    customer, created = Customer.objects.get_or_create(user=request.user)

    form = CustomerForm(instance=customer)

    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES, instance=customer)
        if form.is_valid():
            form.save()

    context = {'form': form}
    return render(request, 'accounts/account_settings.html', context)


# ================= CUSTOMER DETAILS =================
@login_required(login_url='login')
def customer(request, pk):
    customer = Customer.objects.get(id=pk)

    orders = customer.order_set.all()
    orders_count = orders.count()

    myFilter = OrderFilter(request.GET, queryset=orders)
    orders = myFilter.qs

    context = {
        'customer': customer,
        'orders': orders,
        'orders_count': orders_count,
        'myFilter': myFilter
    }

    return render(request, 'accounts/customer.html', context)


# ================= PRODUCTS =================
def products(request):
    products = Product.objects.all()
    return render(request, 'accounts/products.html', {'products': products})


# ================= CREATE ORDER =================
@login_required(login_url='login')
def createOrder(request, pk):
    OrderFormSet = inlineformset_factory(Customer, Order, fields=('product', 'status'), extra=10)

    customer = Customer.objects.get(id=pk)

    if request.method == 'POST':
        formset = OrderFormSet(request.POST, instance=customer)
        if formset.is_valid():
            formset.save()
            return redirect('/')
    else:
        formset = OrderFormSet(queryset=Order.objects.none(), instance=customer)

    context = {'formset': formset}
    return render(request, 'accounts/order_form.html', context)


# ================= UPDATE ORDER =================
@login_required(login_url='login')
def updateOrder(request, pk):
    order = Order.objects.get(id=pk)

    form = OrderForm(instance=order)

    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            return redirect('/')

    context = {'form': form}
    return render(request, 'accounts/order_form.html', context)


# ================= DELETE ORDER =================
@login_required(login_url='login')
def deleteOrder(request, pk):
    order = Order.objects.get(id=pk)

    if request.method == 'POST':
        order.delete()
        return redirect('/')

    context = {'item': order}
    return render(request, 'accounts/delete.html', context)