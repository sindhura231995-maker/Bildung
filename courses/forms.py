from django import forms
from django.utils.text import slugify
from .models import Course, Lecture, Feedback, Enrollment, Module
from django.forms import inlineformset_factory


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'price']
        widgets = {'description': forms.Textarea(attrs={'rows': 4})}

class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['title', 'description']

class LectureForm(forms.ModelForm):
    class Meta:
        model = Lecture
        fields = ['title', 'video', 'file']


ModuleFormSet = inlineformset_factory(Course, Module, form=ModuleForm, extra=1, can_delete=True)
LectureFormSet = inlineformset_factory(Module, Lecture, form=LectureForm, extra=1, can_delete=True)

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write feedback here...'}),
        }

    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)  # passed from view
        super().__init__(*args, **kwargs)
        if course:
            # restrict feedback to enrolled students
            enrolled_students = Enrollment.objects.filter(course=course).values_list("student", flat=True)
            self.fields['student'].queryset = course.students.filter(id__in=enrolled_students)
