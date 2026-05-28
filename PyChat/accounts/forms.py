from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

INPUT_CLASSES = {
    'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100',
}

CHECKBOX_CLASSES = {
    'class': 'h-4 w-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500',
}

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={**INPUT_CLASSES, 'autocomplete': 'new-password'}),
        label='Password',
        min_length=8,
        help_text='At least 8 characters recommended.',
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={**INPUT_CLASSES, 'autocomplete': 'new-password'}),
        label='Confirm Password',
    )

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={**INPUT_CLASSES, 'autocomplete': 'username'}),
            'email': forms.EmailInput(attrs={**INPUT_CLASSES, 'autocomplete': 'email'}),
        }
        help_texts = {
            'username': 'Letters, digits and @/./+/-/_ only.',
        }

    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise ValidationError('Passwords do not match')
        return password_confirm

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Email already registered')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class UserLoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={**INPUT_CLASSES, 'autocomplete': 'username'}),
        label='Username',
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={**INPUT_CLASSES, 'autocomplete': 'current-password'}),
        label='Password',
    )


class UserSettingsForm(forms.Form):
    profile_picture = forms.ImageField(
        required=False,
        label='Profile picture',
        widget=forms.FileInput(attrs={'class': 'block w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:bg-indigo-100 file:text-indigo-700 hover:file:bg-indigo-200'}),
    )
    email_notifications = forms.BooleanField(
        required=False,
        label='Email notifications',
        widget=forms.CheckboxInput(attrs=CHECKBOX_CLASSES),
        initial=True,
    )
    dark_mode = forms.BooleanField(
        required=False,
        label='Enable dark mode',
        widget=forms.CheckboxInput(attrs=CHECKBOX_CLASSES),
        initial=False,
    )
    show_online_status = forms.BooleanField(
        required=False,
        label='Show my online status to friends',
        widget=forms.CheckboxInput(attrs=CHECKBOX_CLASSES),
        initial=True,
    )
