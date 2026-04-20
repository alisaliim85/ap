from django import forms
from django.utils.translation import gettext_lazy as _
from .models import MedicationRequest, MedicationRefill
from partners.models import Partner


class MedicationTransferForm(forms.Form):
    """نموذج نقل طلب الخدمة إلى وحدة الأدوية."""

    prescription_date = forms.DateField(
        label=_("Prescription Date"),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    prescription_validity_months = forms.IntegerField(
        label=_("Prescription Validity (Months)"),
        initial=6,
        min_value=1,
        max_value=24,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    interval_months = forms.IntegerField(
        label=_("Dispense Interval (Months)"),
        min_value=1,
        max_value=12,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text=_("e.g., 1 for Monthly, 3 for Quarterly"),
    )
    total_duration_months = forms.IntegerField(
        label=_("Total Duration (Months)"),
        min_value=1,
        max_value=120,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    delivery_address = forms.CharField(
        label=_("Delivery Address"),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        help_text=_("Recipient's address for medication delivery."),
    )
    broker_note = forms.CharField(
        label=_("Broker Note"),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )

    def clean(self):
        cleaned_data = super().clean()
        interval = cleaned_data.get('interval_months')
        total = cleaned_data.get('total_duration_months')
        if interval and total and interval > total:
            raise forms.ValidationError(
                _("Dispense interval cannot be greater than total duration.")
            )
        return cleaned_data


class ScheduleRefillForm(forms.ModelForm):
    """نموذج جدولة دورة صرف."""

    partner = forms.ModelChoiceField(
        label=_("Dispensing Pharmacy"),
        queryset=Partner.objects.filter(partner_type='PHARMACY_CHAIN', is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label=_("-- Select Pharmacy --"),
    )

    class Meta:
        model = MedicationRefill
        fields = ['scheduled_date', 'partner', 'notes']
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'scheduled_date': _("Scheduled Date"),
            'notes': _("Notes"),
        }


class RefillReviewForm(forms.Form):
    """نموذج مراجعة وقبول/رفض دورة الصرف."""

    ACTION_APPROVE = 'approve'
    ACTION_CANCEL = 'cancel'
    ACTION_CHOICES = [
        (ACTION_APPROVE, _('Approve')),
        (ACTION_CANCEL, _('Cancel')),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.HiddenInput(),
    )
    notes = forms.CharField(
        label=_("Notes / Reason"),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )
