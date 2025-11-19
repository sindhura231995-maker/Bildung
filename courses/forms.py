from django import forms
from django.utils.text import slugify
from .models import Course, Lecture, Feedback, Enrollment, Module, LiveClass, CourseEvent
from django.forms import inlineformset_factory


# --------------------------
# Course Form (with category)
# --------------------------
class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'price', 'category']  # Added 'category'
        widgets = {'description': forms.Textarea(attrs={'rows': 4})}


# --------------------------
# Module Form
# --------------------------
class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['title', 'description']


# --------------------------
# Lecture Form
# --------------------------
class LectureForm(forms.ModelForm):
    class Meta:
        model = Lecture
        fields = ['title', 'video', 'file']


# --------------------------
# Inline Formsets
# --------------------------

ModuleFormSet = inlineformset_factory(
    parent_model=Course,
    model=Module,
    form=ModuleForm,
    fk_name='course',
    extra=1,
    can_delete=True
)

LectureFormSet = inlineformset_factory(
    parent_model=Module,
    model=Lecture,
    form=LectureForm,
    extra=1,
    can_delete=True
)


# --------------------------
# Feedback Form
# --------------------------
class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write feedback here...'}),
        }

    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)  
        super().__init__(*args, **kwargs)
        if course:
            enrolled_students = Enrollment.objects.filter(course=course).values_list("student", flat=True)
            self.fields['student'].queryset = course.students.filter(id__in=enrolled_students)


class CourseEventForm(forms.ModelForm):
    event_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    start_time_input = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    end_time_input = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))

    class Meta:
        model = CourseEvent
        fields = ['title', 'description']

class LiveClassForm(forms.ModelForm):
    class Meta:
        model = LiveClass
        fields = ['course', 'topic', 'date', 'time']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'topic': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Topic Name'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
        }
    def clean(self):
 
        cleaned_data = super().clean()
        course = cleaned_data.get('course')
        date = cleaned_data.get('date')
        time = cleaned_data.get('time')

        if not (course and date and time):
            return cleaned_data

        enrolled_students = Enrollment.objects.filter(course=course).values_list('student_id', flat=True)

        if not enrolled_students.exists():
            return cleaned_data  


        conflicting_classes = (
            LiveClass.objects
            .filter(date=date, time=time)
            .exclude(course=course)  
            .filter(course__enrollments__student_id__in=enrolled_students)
            .distinct()
        )

        if conflicting_classes.exists():
            conflict = conflicting_classes.first()
            instructor_name = conflict.instructor.get_full_name() or conflict.instructor.username
            raise forms.ValidationError(
                f"⚠️ Scheduling conflict! already "
                f"'{conflict.course.title}' course by {instructor_name} was scheduled at this time."
            )

        return cleaned_data
