from django.shortcuts import render,redirect,HttpResponse
from .forms import ResgistrationForm
from .models import Account
from django.contrib import messages,auth
from django.contrib.auth.decorators import login_required



# verification email
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import  render_to_string
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage


from carts.views import _cart_id
from carts.models import Cart,CartItem

import requests

# Create your views here.
def register(request):
    if request.method == 'POST':
        form = ResgistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            phone_number = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            username = email.split("@")[0]
            user = Account.objects.create_user(first_name=first_name,last_name=last_name,email=email,username=username,password=password)
            user.phone_number = phone_number
            user.save()
            
            # user activate
            current_site = get_current_site(request)
            mail_subject = 'please activate your account'
            message = render_to_string('accounts/account_verification_email.html',{
                'user':user,
                'domain': current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(mail_subject,message,to=[to_email])
            send_email.send()
            
            
            # messages.success(request,'Thank you for registration with us. We have sent a verification email to your email address. Please verify it.')
            return redirect('/accounts/login/?command=verification&email='+email)
    else:      
        form = ResgistrationForm()
    return render(request,'accounts/register.html',{'form':form})

def login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        user = auth.authenticate(email=email,password=password)
        
        if user is not None:
            try:
                cart = Cart.objects.get(cart_id = _cart_id(request))
                is_cart_item_exists = CartItem.objects.filter(cart=cart).exists()
                if is_cart_item_exists:
                    cart_item = CartItem.objects.filter(cart=cart)
                    
                    
                    # gettting the product variation by card id
                    product_variation = []
                    for item in cart_item:
                        variation = item.variations.all()
                        product_variation.append(list(variation))
                        
                        
                    # get the item from the user to access his product variation
                    cart_item = CartItem.objects.filter(user= user)
                    ex_var_list=[]
                    id = []
                    for item in cart_item:
                        existing_variation = item.variations.all()
                        ex_var_list.append(list(existing_variation))
                        id.append(item.id)
                    
                    # product_variation = [1,2,3,4]
                    # ex_var_list = [2,3,5,6,7]
                    for pr in product_variation:
                        if pr in ex_var_list:
                            index = ex_var_list.index[pr]
                            item_id = id[index]
                            item = CartItem.objects.get(id= item_id)
                            item.quantity += 1
                            item.user = user
                            item.save()
                        else:
                            cart_item = CartItem.objects.filter(cart=cart)
                            for item in cart_item:
                                item.user = user
                                item.save()

            except:
                pass
            auth.login(request,user)
            messages.success(request,'You are now logged in.')
            url = request.META.get('HTTP_REFERER')
            try:
                query = requests.utils.urlparse(url).query
                params = dict(x.split('=') for x in query.split('&'))
                if 'next' in params:
                    nextPage = params['next']
                    return redirect(nextPage)
                
            except:
                return redirect('dashboard')
        else:
            messages.error(request,'Invalid login credentials')
            return redirect('login')
        
    return render(request,'accounts/login.html')


@login_required(login_url = 'login')
def logout(request):
    auth.logout(request)
    messages.success(request,'You are logged out')
    return redirect('login')



def activate(request,uidb64,token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except(TypeError,ValueError,OverflowError,Account.DoesNotExist):
        user=None
    if user is not None and default_token_generator.check_token(user,token):
        user.is_active = True
        user.save()
        messages.success(request,'Congratulations! Your account is activated.')
        return redirect('login')
    else:
        messages.error(request,'Invalid activation link')
        return redirect('register') 
 
    
@login_required(login_url = 'login')
def dashboard(request):
    return render(request,'accounts/dashboard.html')




def forgotPassword(request):
    if request.method =='POST':
        email = request.POST['email']
        if Account.objects.filter(email=email).exists():
            user = Account.objects.get(email__exact=email)
            
            
            # Reset Password
            current_site = get_current_site(request)
            mail_subject = 'Reset Your Password'
            message = render_to_string('accounts/reset_password_email.html',{
                'user':user,
                'domain': current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(mail_subject,message,to=[to_email])
            send_email.send() 
            messages.success(request,'Password reset email has been sent to your email addresss')
            return redirect('login')
        else:
            messages.error(request,'Account does not exist!')
            return redirect('forgotPassword')
    return render(request,'accounts/forgetPassword.html')



def resetpassword_validate(request,uidb64,token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except(TypeError,ValueError,OverflowError,Account.DoesNotExist):
        user=None
    if user is not None and default_token_generator.check_token(user,token):
        request.session['uid'] = uid
        messages.success(request,'Please reset your password')
        return redirect('resetPassword')
    else:
        messages.error(request,'This link has been expired!')
        return redirect('login')



def resetPassword(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        
        
        if password == confirm_password:
            uid = request.session.get('uid')
            user = Account.objects.get(pk=uid)
            user.set_password(password)
            user.save()
            messages.success(request,'Password reset successful')
            return redirect('login')
        else:
            messages.error(request,'Password does not match!')
            return redirect('resetPasword')
    else:
        return render(request,'accounts/resetPassword.html')