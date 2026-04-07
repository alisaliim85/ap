from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
from django_fsm import TransitionNotAllowed
from .models import Claim, ClaimComment, ClaimAttachment
from .forms import ClaimCreateForm, ClaimCommentForm
from members.models import Member


@login_required
def claim_list(request):
    user = request.user
    
    # 1. الاستعلام الأساسي مع القضاء على N+1 مبكراً
    # نستخدم select_related لجلب الجداول المرتبطة في استعلام SQL واحد
    claims = Claim.objects.select_related(
        'member', 
        'member__client', 
        'currency'
    )

    # 2. فلترة البيانات وعزلها بناءً على دور المستخدم (Data Isolation)
    
    if user.role == user.Roles.SUPER_ADMIN:
        # الإدارة العليا ترى كل شيء في النظام دون قيود
        pass 

    elif user.has_perm('accounts.view_broker_dashboard'):
        # --- منطق الوسيط (Broker) ---
        # نستبعد الحالات التي تسبق وصول المطالبة للوسيط
        pre_broker_states = [
            Claim.Status.DRAFT,
            Claim.Status.SUBMITTED_TO_HR,
            Claim.Status.RETURNED_BY_HR
        ]
        claims = claims.exclude(status__in=pre_broker_states)

    elif user.has_perm('accounts.view_hr_dashboard'):
        # --- منطق الموارد البشرية (HR) ---
        # يرى الـ HR مطالبات موظفي شركته فقط، ونستبعد المسودات التي لم يرسلها الموظف بعد
        claims = claims.filter(
            member__client=user.related_client
        ).exclude(status=Claim.Status.DRAFT)
        
    elif user.role == user.Roles.MEMBER:
        # --- منطق العضو (الموظف) ---
        # يرى مطالباته الخاصة ومطالبات عائلته
        from django.db.models import Q
        claims = claims.filter(
            Q(member__user=user) | Q(member__sponsor__user=user)
        )
        
    else:
        # حماية إضافية: إذا لم يتطابق مع أي دور، لا تعرض شيئاً
        claims = claims.none()

    # 3. الترتيب (الأحدث أولاً)
    claims = claims.order_by('-created_at')
    
    return render(request, 'claims/claim_list.html', {'claims': claims})



@login_required
def claim_detail(request, pk):
    # استخدام select_related للبيانات الأساسية
    # و prefetch_related للقوائم المرتبطة (المرفقات، التعليقات مع أصحابها، وسجل الحالات مع مستخدميها)
    claim = get_object_or_404(
        Claim.objects.select_related('member', 'member__client', 'currency')
        .prefetch_related(
            'attachments',
            'comments__author',  # حل N+1 لكاتب التعليق
            'status_logs__user'  # حل N+1 لمستخدم سجل الحالة
        ),
        pk=pk
    )

    user = request.user
    comments = list(claim.comments.all())

    # فلترة التعليقات حسب الصلاحيات والدور (Data Isolation)
    if not user.is_superuser:
        if user.role == 'MEMBER':
            # العضو يرى فقط العام
            comments = [c for c in comments if c.visibility == ClaimComment.Visibility.GENERAL]
        elif user.is_hr or user.has_perm('accounts.view_hr_dashboard'):
            # HR يرى العام والداخلي (HR + Broker)
            comments = [c for c in comments if c.visibility in [ClaimComment.Visibility.GENERAL, ClaimComment.Visibility.HR_BROKER]]
        elif user.role == 'INSURANCE':
            # التأمين يرى العام والداخلي (Broker + Insurance)
            comments = [c for c in comments if c.visibility in [ClaimComment.Visibility.GENERAL, ClaimComment.Visibility.BROKER_INSURANCE]]
        # Broker has access to all, as defaults if none of the above are matched

    # تحديث حالة "شوهد" (is_read) للتعليقات
    unread_comments = []
    for c in comments:
        if not c.is_read and c.author != user:
            # We don't mark as read if it's their own comment
            unread_comments.append(c.id)
    
    if unread_comments:
        ClaimComment.objects.filter(id__in=unread_comments).update(is_read=True)
        # Update local objects so template shows them as read (optional, since reload will fetch them state, but good practice)

    # نموذج التعليق
    comment_form = ClaimCommentForm(user=user)

    context = {
        'claim': claim,
        'comments': comments,
        'comment_form': comment_form,
    }
    return render(request, 'claims/claim_detail.html', context)

@login_required
@require_POST
def add_claim_comment(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    
    # Check if user has access to this claim - basic check, can be expanded based on your RBAC
    # We will assume they have access if they can view the form and submit it, but for production
    # we should ideally re-run the object permission check here.
    
    form = ClaimCommentForm(request.POST, user=request.user)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.claim = claim
        comment.author = request.user
        
        # Enforce visibility: If MEMBER, strictly enforce GENERAL
        if getattr(request.user, 'role', '') == 'MEMBER':
            comment.visibility = ClaimComment.Visibility.GENERAL
            
        comment.save()
        messages.success(request, "تم إضافة التعليق بنجاح.")
    else:
        messages.error(request, "حدث خطأ أثناء إضافة التعليق. تأكد من إدخال البيانات بشكل صحيح.")
        
    return redirect('claims:claim_detail', pk=pk)

@login_required
@require_POST
def submit_claim_to_hr(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    
    if request.method == 'POST':
        try:
            # نضع العملية داخل Transaction لضمان عدم حدوث أخطاء نصف مكتملة
            with transaction.atomic():
                # FSM Transition Check
                claim.submit_to_hr(user=request.user)
                claim.save()
            
            messages.success(request, "تم إرسال المطالبة إلى قسم الموارد البشرية بنجاح.")
            
        except TransitionNotAllowed:
            messages.error(request, "لا يمكن إرسال هذه المطالبة في حالتها الحالية.")
            
    return redirect('claims:claim_detail', pk=pk)

@login_required
@require_POST
def hr_return_claim(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, "يجب كتابة سبب للإعادة.")
            return redirect('claims:claim_detail', pk=pk)

        try:
            with transaction.atomic():
                # استدعاء دالة الـ FSM مع تمرير السبب
                claim.hr_return(user=request.user, reason=reason)
                claim.save()
            
            messages.success(request, "تم إعادة المطالبة للعضو لوجود نواقص.")
            
        except TransitionNotAllowed:
            messages.error(request, "لا تملك صلاحية أو حالة المطالبة لا تسمح بإعادتها.")
            
    return redirect('claims:claim_detail', pk=pk)


@login_required
@require_POST
def hr_approve_claim(request, pk):
    # نستخدم select_related لمنع N+1 أثناء فحص الصلاحيات داخل شروط FSM
    claim = get_object_or_404(Claim.objects.select_related('member__client'), pk=pk)
    
    try:
        with transaction.atomic():
            claim.hr_approve(user=request.user)
            claim.save()
        messages.success(request, "تمت الموافقة على المطالبة وإرسالها للوسيط.")
    except TransitionNotAllowed:
        messages.error(request, "لا يمكنك تنفيذ هذا الإجراء في حالة المطالبة الحالية.")
        
    return redirect('claims:claim_detail', pk=pk)

@login_required
@require_POST
def broker_start_processing(request, pk):
    claim = get_object_or_404(Claim.objects.select_related('member__client'), pk=pk)
    try:
        with transaction.atomic():
            claim.broker_start_process(user=request.user)
            claim.save()
        messages.success(request, "تم تغيير الحالة إلى: قيد المعالجة من قبل الوسيط.")
    except TransitionNotAllowed:
        messages.error(request, "إجراء غير مسموح.")
    return redirect('claims:claim_detail', pk=pk)

@login_required
@require_POST
def broker_return_claim(request, pk):
    claim = get_object_or_404(Claim.objects.select_related('member__client'), pk=pk)
    reason = request.POST.get('reason', '').strip()
    
    if not reason:
        messages.error(request, "يجب كتابة سبب لإعادة المطالبة.")
        return redirect('claims:claim_detail', pk=pk)

    try:
        with transaction.atomic():
            claim.broker_return(user=request.user, reason=reason)
            claim.save()
        messages.success(request, "تمت إعادة المطالبة للعضو لاستكمال النواقص.")
    except TransitionNotAllowed:
        messages.error(request, "إجراء غير مسموح.")
    return redirect('claims:claim_detail', pk=pk)

@login_required
@require_POST
def send_to_insurance(request, pk):
    claim = get_object_or_404(Claim.objects.select_related('member__client'), pk=pk)
    try:
        with transaction.atomic():
            claim.sent_to_insurance(user=request.user)
            claim.save()
        messages.success(request, "تم إرسال المطالبة لشركة التأمين بنجاح.")
    except TransitionNotAllowed:
        messages.error(request, "إجراء غير مسموح.")
    return redirect('claims:claim_detail', pk=pk)

@login_required
@require_POST
def insurance_query_claim(request, pk):
    claim = get_object_or_404(Claim.objects.select_related('member__client'), pk=pk)
    try:
        with transaction.atomic():
            claim.insurance_query(user=request.user)
            claim.save()
        messages.warning(request, "تم تعليق المطالبة لوجود استفسار من شركة التأمين.")
    except TransitionNotAllowed:
        messages.error(request, "إجراء غير مسموح.")
    return redirect('claims:claim_detail', pk=pk)

@login_required
@require_POST
def answer_insurance_query(request, pk):
    claim = get_object_or_404(Claim.objects.select_related('member__client'), pk=pk)
    try:
        with transaction.atomic():
            claim.answer_insurance_query(user=request.user)
            claim.save()
        messages.success(request, "تم الرد على استفسار التأمين وإعادتها لهم.")
    except TransitionNotAllowed:
        messages.error(request, "إجراء غير مسموح.")
    return redirect('claims:claim_detail', pk=pk)

@login_required
@require_POST
def insurance_approve_claim(request, pk):
    claim = get_object_or_404(Claim.objects.select_related('member__client'), pk=pk)
    try:
        with transaction.atomic():
            claim.insurance_approve(user=request.user)
            claim.save()
        messages.success(request, "تم تسجيل موافقة شركة التأمين على المطالبة.")
    except TransitionNotAllowed:
        messages.error(request, "إجراء غير مسموح.")
    return redirect('claims:claim_detail', pk=pk)

@login_required
@require_POST
def insurance_reject_claim(request, pk):
    claim = get_object_or_404(Claim.objects.select_related('member__client'), pk=pk)
    reason = request.POST.get('reason', '').strip()
    
    if not reason:
        messages.error(request, "يجب تحديد سبب رفض شركة التأمين.")
        return redirect('claims:claim_detail', pk=pk)

    try:
        with transaction.atomic():
            claim.insurance_reject(user=request.user, reason=reason)
            claim.save()
        messages.error(request, "تم رفض المطالبة من قبل شركة التأمين.")
    except TransitionNotAllowed:
        messages.error(request, "إجراء غير مسموح.")
    return redirect('claims:claim_detail', pk=pk)


@login_required
@require_POST
def mark_claim_as_paid(request, pk):
    claim = get_object_or_404(Claim.objects.select_related('member__client'), pk=pk)
    amount = request.POST.get('approved_amount_sar')

    if not amount:
        messages.error(request, "يجب إدخال المبلغ المعتمد للسداد.")
        return redirect('claims:claim_detail', pk=pk)

    try:
        # تحويل النص إلى رقم عشري (Decimal) للتأكد من صحة البيانات
        from decimal import Decimal, InvalidOperation
        amount_decimal = Decimal(amount)
        
        with transaction.atomic():
            claim.mark_as_paid(user=request.user, amount=amount_decimal)
            claim.save()
        messages.success(request, f"تم سداد المطالبة بمبلغ {amount_decimal} ريال بنجاح.")
        
    except InvalidOperation:
        messages.error(request, "صيغة المبلغ غير صحيحة.")
    except TransitionNotAllowed:
        messages.error(request, "لا يمكن تحويل هذه المطالبة للسداد في حالتها الحالية.")
        
    return redirect('claims:claim_detail', pk=pk)

@login_required
def claim_create(request):
    if not request.user.has_perm('claims.can_submit_claim'):
        messages.error(request, "لا تملك الصلاحية لإضافة مطالبة.")
        return redirect('claims:claim_list')

    if request.method == 'POST':
        form = ClaimCreateForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            action = request.POST.get('action', 'draft')
            
            try:
                with transaction.atomic():
                    claim = form.save()
                    
                    # Save attachments
                    attachments = request.FILES.getlist('attachments')
                    for f in attachments:
                        ClaimAttachment.objects.create(claim=claim, file=f)
                    
                    if action == 'submit':
                        if claim.needs_hr_review():
                            claim.submit_to_hr(user=request.user)
                        else:
                            claim.submit_direct_to_broker(user=request.user)
                        claim.save()
                        messages.success(request, "تم حفظ المطالبة وإرسالها بنجاح.")
                    else:
                        messages.success(request, "تم حفظ المطالبة كمسودة.")
                        
                return redirect('claims:claim_detail', pk=claim.pk)
            except TransitionNotAllowed:
                messages.error(request, "حدث خطأ أثناء محاولة إرسال المطالبة، الرجاء المحاولة لاحقاً.")
            except Exception as e:
                messages.error(request, f"حدث خطأ غير متوقع: {str(e)}")
    else:
        form = ClaimCreateForm(user=request.user)

    return render(request, 'claims/claim_create.html', {'form': form})

@login_required
def search_member_by_nid(request):
    q = request.GET.get('q', '').strip()
    client = getattr(request.user, 'related_client', None)
    
    if len(q) < 5 or not client:
        return render(request, 'claims/partials/member_search_result.html', {'member': None})
        
    try:
        member = Member.objects.get(national_id=q, client=client)
    except Member.DoesNotExist:
        member = None
        
    return render(request, 'claims/partials/member_search_result.html', {'member': member, 'q': q})
