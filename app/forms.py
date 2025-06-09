from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .models import Rating


def validate_rating(value):
    # Verificar que el valor esté en el rango correcto
    value = Decimal(value)
    if value < 1 or value > 5:
        raise ValidationError('La calificación debe estar entre 1 y 5.')


class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['title', 'text', 'rating']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Gran experiencia'
            }),
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '3',
                'placeholder': 'Comparte tu experiencia...'
            }),
        }

    # Cambia el orden de las opciones a  (5, 4, 3, 2, 1)
    rating = forms.ChoiceField(
        choices=[(i, f"{i} estrellas") for i in range(5, 0, -1)],
        widget=forms.RadioSelect(attrs={'class': 'star-rating-input'}),
        required=True  # La calificación es obligatoria
    )
    # Hacer que el campo text sea opcional
    text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': '3',
            'placeholder': 'Comparte tu experiencia...'
        })
    )
