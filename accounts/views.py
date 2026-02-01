from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from .forms import LoginForm, StaffUserForm, HRStaffForm, ProfileForm
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
    # مسار لوحة تحكم HR
    if request.user.is_hr:
        client = request.user.related_client
        if not client:
            messages.error(request, "لم يتم ربط حسابك بشركة محددة، يرجى التواصل مع الدعم الفني")
            return redirect('login')
            
        # إحصائيات الأعضاء
        from members.models import Member
        members = Member.objects.filter(client=client)
        
        stats = {
            'total_members': members.count(),
            'employees': members.filter(relation='PRINCIPAL').count(),
            'dependents': members.exclude(relation='PRINCIPAL').count(),
            'spouses': members.filter(relation='SPOUSE').count(),
            'children': members.filter(relation='CHILD').count(),
            'parents': members.filter(relation='PARENT').count(),
            'others': members.filter(relation__in=['BROTHER', 'SISTER', 'OTHER']).count(),
            'pending_requests': members.filter(is_active=False).count(),
        }
        
        # آخر الطلبات (الأعضاء غير النشطين)
        recent_requests = members.filter(is_active=False).select_related('policy_class').order_by('-created_at')[:5]
        
        context = {
            'client': client,
            'stats': stats,
            'recent_requests': recent_requests
        }
        return render(request, 'accounts/dashboard_hr.html', context)

    # مسار لوحة تحكم الوسيط (الافتراضي)
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


# --- إدارة موظفي الـ HR (للـ HR Admin) ---

@login_required
def hr_user_list(request):
    if not request.user.is_hr:
        messages.error(request, "ليس لديك صلاحية الوصول لهذه الصفحة")
        return redirect('dashboard')

    client = request.user.related_client
    # عرض الموظفين التابعين لنفس الشركة فقط (باستثناء المستخدم الحالي لتجنب حذفه لنفسه بالخطأ)
    users_list = User.objects.filter(related_client=client).exclude(pk=request.user.pk).order_by('-date_joined')

    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        users_list = users_list.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # الترقيم
    paginator = Paginator(users_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.headers.get('HX-Request'):
        return render(request, 'accounts/partials/hr_user_table.html', {'users': page_obj, 'page_obj': page_obj})

    return render(request, 'accounts/hr_user_list.html', {'users': page_obj, 'page_obj': page_obj})

@login_required
def hr_user_create(request):
    if not request.user.is_hr:
        return redirect('dashboard')
    
    client = request.user.related_client
    if not client:
        messages.error(request, "حسابك غير مرتبط بشركة")
        return redirect('dashboard')

    if request.method == 'POST':
        form = HRStaffForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = User.Roles.HR_STAFF
            user.related_client = client
            user.save()
            messages.success(request, "تم إضافة الموظف بنجاح")
            return redirect('hr_user_list')
    else:
        form = HRStaffForm()

    return render(request, 'accounts/hr_user_form.html', {'form': form, 'title': 'إضافة موظف جديد'})

@login_required
def hr_user_update(request, pk):
    if not request.user.is_hr:
        return redirect('dashboard')

    user_to_edit = get_object_or_404(User, pk=pk)
    
    # حماية: التأكد من أن الموظف يتبع لنفس شركة الـ HR Admin
    if user_to_edit.related_client != request.user.related_client:
         messages.error(request, "ليس لديك صلاحية لتعديل هذا المستخدم")
         return redirect('hr_user_list')
         
    if request.method == 'POST':
        form = HRStaffForm(request.POST, instance=user_to_edit)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث بيانات الموظف بنجاح")
            return redirect('hr_user_list')
    else:
        form = HRStaffForm(instance=user_to_edit)

    return render(request, 'accounts/hr_user_form.html', {'form': form, 'title': f'تعديل الموظف: {user_to_edit.username}'})

@login_required
def hr_user_delete(request, pk):
    if not request.user.is_hr:
        return redirect('dashboard')

    user_to_delete = get_object_or_404(User, pk=pk)
    
    # حماية
    if user_to_delete.related_client != request.user.related_client:
         return redirect('hr_user_list')

    if request.method == 'POST':
        username = user_to_delete.username
        user_to_delete.delete()
        messages.success(request, f"تم حذف الموظف {username} بنجاح")
        return redirect('hr_user_list')
    
    return render(request, 'accounts/hr_user_confirm_delete.html', {'user_to_delete': user_to_delete})


# --- الملف الشخصي ---

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {
        'user': request.user
    })

@login_required
def user_profile_edit(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث الملف الشخصي بنجاح")
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
    
    return render(request, 'accounts/profile_edit.html', {'form': form})