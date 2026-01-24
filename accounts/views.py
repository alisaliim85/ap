from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from .forms import LoginForm, StaffUserForm
from .models import User

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
    return render(request, 'accounts/dashboard.html')

# --- إدارة المستخدمين (للوسيط فقط) ---

@login_required
def user_list(request):
    if not request.user.is_broker:
        messages.error(request, "ليس لديك صلاحية الوصول لهذه الصفحة")
        return redirect('dashboard')

    users_list = User.objects.all().order_by('-date_joined')

    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        users_list = users_list.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(related_client__name_ar__icontains=search_query)
        )

    # الترقيم
    paginator = Paginator(users_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.headers.get('HX-Request'):
        return render(request, 'accounts/partials/user_table.html', {'users': page_obj, 'page_obj': page_obj})

    return render(request, 'accounts/user_list.html', {'users': page_obj, 'page_obj': page_obj})

@login_required
def user_create(request):
    if not request.user.is_broker:
        messages.error(request, "ليس لديك صلاحية الوصول لهذه الصفحة")
        return redirect('dashboard')

    if request.method == 'POST':
        form = StaffUserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "تم إنشاء المستخدم بنجاح")
            return redirect('user_list')
    else:
        form = StaffUserForm()

    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'إضافة مستخدم جديد'})

@login_required
def user_update(request, pk):
    user_to_edit = get_object_or_404(User, pk=pk)
    if not request.user.is_broker:
        messages.error(request, "ليس لديك صلاحية الوصول لهذه الصفحة")
        return redirect('dashboard')

    if request.method == 'POST':
        form = StaffUserForm(request.POST, instance=user_to_edit)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث بيانات المستخدم بنجاح")
            return redirect('user_list')
    else:
        form = StaffUserForm(instance=user_to_edit)

    return render(request, 'accounts/user_form.html', {'form': form, 'title': f'تعديل المستخدم: {user_to_edit.username}', 'user_to_edit': user_to_edit})

@login_required
def user_delete(request, pk):
    user_to_delete = get_object_or_404(User, pk=pk)
    if not request.user.is_broker:
        messages.error(request, "ليس لديك صلاحية الوصول لهذه الصفحة")
        return redirect('dashboard')

    if request.method == 'POST':
        username = user_to_delete.username
        user_to_delete.delete()
        messages.success(request, f"تم حذف المستخدم {username} بنجاح")
        return redirect('user_list')
    
    return render(request, 'accounts/user_confirm_delete.html', {'user_to_delete': user_to_delete})