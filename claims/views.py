from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django_fsm import TransitionNotAllowed
from .models import Claim, ClaimComment, ClaimAttachment
from .forms import ClaimCreateForm, ClaimCommentForm
from members.models import Member
from accounts.models import User

# ==========================================
# دالة مساعدة: الحماية الجوهرية (Data Isolation)
# ==========================================
def get_allowed_claims(user):
    """
    هذه الدالة هي حارس البوابة لكل المطالبات. تضمن أن لا أحد يرى مطالبة لا تخصه.
    """
    base_qs = Claim.objects.select_related('member', 'member__client', 'currency')

    # 1. السوبر أدمن يرى كل شيء
    if user.role == User.Roles.SUPER_ADMIN:
        return base_qs
        
    # 2. الوسيط يرى فقط مطالبات الشركات العميلة التابعة له
    elif user.is_broker_role and user.related_broker:
        return base_qs.filter(member__client__broker=user.related_broker)
        
    # 3. الـ HR يرى مطالبات شركته فقط
    elif user.is_hr_role and user.related_client:
        return base_qs.filter(member__client=user.related_client)
        
    # 4. العضو يرى مطالباته ومطالبات التابعين له (عائلته)
    elif user.is_member_role and hasattr(user, 'member_profile'):
        return base_qs.filter(
            Q(member=user.member_profile) | Q(member__sponsor=user.member_profile)
        )
        
    return Claim.objects.none()


@login_required
def claim_list(request):
    user = request.user
    
    # 1. جلب المطالبات المسموحة فقط بناءً على الدور المعماري
    claims = get_allowed_claims(user)

    # 2. فلترة إضافية لحالة المطالبة (Status Filtering)
    if user.is_broker_role:
        # الوسيط لا يرى المسودات أو المطالبات التي لا تزال عند الـ HR
        pre_broker_states = [
            Claim.Status.DRAFT,
            Claim.Status.SUBMITTED_TO_HR,
            Claim.Status.RETURNED_BY_HR
        ]
        claims = claims.exclude(status__in=pre_broker_states)

    elif user.is_hr_role:
        # الـ HR لا يرى مسودات الموظف التي لم تُرسل بعد
        claims = claims.exclude(status=Claim.Status.DRAFT)

    # 3. الترتيب (الأحدث أولاً)
    claims = claims.order_by('-created_at')
    
    return render(request, 'claims/claim_list.html', {'claims': claims})


@login_required
def claim_detail(request, pk):
    # الحماية التلقائية: إذا أدخل ID مطالبة لا تخصه سيظهر له 404
    claim = get_object_or_404(
        get_allowed_claims(request.user).prefetch_related(
            'attachments',
            'comments__author',  
            'status_logs__user'  
        ),
        pk=pk
    )

    user = request.user
    comments = list(claim.comments.all())

    # فلترة التعليقات حسب الصلاحيات والدور (Data Isolation للتعليقات)
    if not user.is_superuser:
        if user.is_member_role:
            comments = [c for c in comments if c.visibility == ClaimComment.Visibility.GENERAL]
        elif user.is_hr_role:
            comments = [c for c in comments if c.visibility in [ClaimComment.Visibility.GENERAL, ClaimComment.Visibility.HR_BROKER]]
        elif user.role == user.Roles.INSURANCE:
            comments = [c for c in comments if c.visibility in [ClaimComment.Visibility.GENERAL, ClaimComment.Visibility.BROKER_INSURANCE]]
        # الوسيط (Broker) يرى جميع التعليقات افتراضياً

    # تحديث حالة "شوهد" (is_read)
    unread_comments = [c.id for c in comments if not c.is_read and c.author != user]
    if unread_comments:
        ClaimComment.objects.filter(id__in=unread_comments).update(is_read=True)

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
    # حماية أمنية: تأكد أن المستخدم يملك صلاحية على هذه المطالبة
    claim = get_object_or_404(get_allowed_claims(request.user), pk=pk)
    
    form = ClaimCommentForm(request.POST, user=request.user)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.claim = claim
        comment.author = request.user
        
        if request.user.is_member_role:
            comment.visibility = ClaimComment.Visibility.GENERAL
            
        comment.save()
        messages.success(request, "تم إضافة التعليق بنجاح.")
    else:
        messages.error(request, "حدث خطأ أثناء إضافة التعليق. تأكد من إدخال البيانات بشكل صحيح.")
        
    return redirect('claims:claim_detail', pk=pk)

# ==========================================
# عمليات دورة الحياة للمطالبة (FSM Transitions)
# جميعها أصبحت محمية تلقائياً بفضل `get_allowed_claims`
# ==========================================

@login_required
@require_POST
def submit_claim_to_hr(request, pk):
    claim = get_object_or_404(get_allowed_claims(request.user), pk=pk)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                claim.submit_to_hr(user=request.user)
                claim.save()
            messages.success(request, "تم إرسال المطالبة إلى قسم الموارد البشرية بنجاح.")
        except TransitionNotAllowed:
            messages.error(request, "لا يمكن إرسال هذه المطالبة في حالتها الحالية.")
    return redirect('claims:claim_detail', pk=pk)

@login_required
@require_POST
def hr_return_claim(request, pk):
    claim = get_object_or_404(get_allowed_claims(request.user), pk=pk)
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, "يجب كتابة سبب للإعادة.")
            return redirect('claims:claim_detail', pk=pk)

        try:
            with transaction.atomic():
                claim.hr_return(user=request.user, reason=reason)
                claim.save()
            messages.success(request, "تم إعادة المطالبة للعضو لوجود نواقص.")
        except TransitionNotAllowed:
            messages.error(request, "لا تملك صلاحية أو حالة المطالبة لا تسمح بإعادتها.")
    return redirect('claims:claim_detail', pk=pk)


@login_required
@require_POST
def hr_approve_claim(request, pk):
    claim = get_object_or_404(get_allowed_claims(request.user), pk=pk)
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
    claim = get_object_or_404(get_allowed_claims(request.user), pk=pk)
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
    claim = get_object_or_404(get_allowed_claims(request.user), pk=pk)
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
    claim = get_object_or_404(get_allowed_claims(request.user), pk=pk)
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
    claim = get_object_or_404(get_allowed_claims(request.user), pk=pk)
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
    claim = get_object_or_404(get_allowed_claims(request.user), pk=pk)
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
    claim = get_object_or_404(get_allowed_claims(request.user), pk=pk)
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
    claim = get_object_or_404(get_allowed_claims(request.user), pk=pk)
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
    claim = get_object_or_404(get_allowed_claims(request.user), pk=pk)
    amount = request.POST.get('approved_amount_sar')

    if not amount:
        messages.error(request, "يجب إدخال المبلغ المعتمد للسداد.")
        return redirect('claims:claim_detail', pk=pk)

    try:
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
    """
    بحث عن مشترك باستخدام رقم الهوية.
    تم حمايته لكي يبحث الوسيط في نطاق شركته، والـ HR في نطاق شركته فقط.
    """
    q = request.GET.get('q', '').strip()
    user = request.user
    
    if len(q) < 5:
        return render(request, 'claims/partials/member_search_result.html', {'member': None})
        
    try:
        # استخدام دالة العزل التي أنشأناها في تطبيق الأعضاء 
        # نكتب الكود هنا مباشرة للاستقلالية أو نستورد الدالة لو رغبت
        base_members = Member.objects.all()
        if user.role == User.Roles.SUPER_ADMIN:
            members_qs = base_members
        elif user.is_broker_role and user.related_broker:
            members_qs = base_members.filter(client__broker=user.related_broker)
        elif user.is_hr_role and user.related_client:
            members_qs = base_members.filter(client=user.related_client)
        else:
            members_qs = base_members.none()

        member = members_qs.get(national_id=q)
    except Member.DoesNotExist:
        member = None
        
    return render(request, 'claims/partials/member_search_result.html', {'member': member, 'q': q})