from django.urls import path
from . import views
from users import views as user_views

app_name = 'courses'

urlpatterns = [
    # Public
    path('', views.course_list, name='course_list'),

    # Student URLs
    path('student/dashboard/', user_views.student_dashboard, name='student_dashboard'),
    path('student/courses/', views.browse_courses, name='browse_courses'),
    path('student/enroll/<int:course_id>/', views.enroll_course, name='enroll_course'),
    path('student/course/<int:course_id>/', views.student_course_detail, name='student_course_detail'),
    path('lecture/<int:lecture_id>/complete/', views.mark_lecture_complete, name='mark_lecture_complete'),
    
    #instructor
    path('dashboard/', views.instructor_dashboard, name='instructor_dashboard'),
]
