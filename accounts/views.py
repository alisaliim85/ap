from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import LoginForm

def login_view(request):
    # 1. إذا كان المستخدم مسجلاً للدخول مسبقاً، حوله للوحة التحكم فوراً
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    # 2. إذا ضغط الزر (POST Request)
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "اسم المستخدم أو كلمة المرور غير صحيحة")
    
    # 3. إذا كان مجرد فتح للصفحة (GET Request)
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "تم تسجيل الخروج بنجاح")
    return redirect('login')

@login_required
def dashboard(request):
    # هذا الكود البسيط للوحة التحكم مؤقتاً
    return render(request, 'accounts/dashboard.html')