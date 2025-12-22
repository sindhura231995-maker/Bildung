from django.urls import path
from courses import views

app_name = 'instructor'  

urlpatterns = [
    # Instructor Dashboard
    path('dashboard/', views.instructor_dashboard, name='instructor_dashboard'),

    # Instructor-only course management
    path('courses/add/', views.add_course, name='add_course'),

    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('courses/<int:course_id>/add-lecture/', views.add_lecture, name='add_lecture'),
    path('courses/<int:course_id>/feedback/', views.give_feedback, name='give_feedback'),
    path('my-students/', views.my_students, name='my_students'),
    path('students-list/', views.students_list, name='students_list'),
    path('student/<int:student_id>/', views.view_student_profile, name='view_student_profile'),

    # Course progress report for instructor
    path('courses/<int:course_id>/progress/', views.course_progress_report, name='course_progress_report'),
    # Instructor course edit
    #path('courses/<int:course_id>/edit/', views.course_edit, name='course_edit'),
    # Add Event for a course
    path("add-event/", views.add_event, name="add_event"),
    path("schedule_live_class/", views.schedule_live_class, name="schedule_live_class"),
    path("edit-class/<int:class_id>/", views.edit_live_class, name="edit_live_class"),
    path("delete-class/<int:class_id>/", views.delete_live_class, name="delete_live_class"),
    path("edit-event/<int:event_id>/", views.edit_event, name="edit_event"),
    path("delete-event/<int:event_id>/", views.delete_event, name="delete_event"),

   # path('my_activity/', views.my_activity, name='my_activity'),
    path("calendar/", views.calendar_view, name="calendar_view"),

  #  path("course/<int:course_id>/qna/instructor/", views.instructor_qna, name="instructor_qna"),
    path("question/<int:question_id>/reply/", views.add_reply, name="add_reply"),
    path("reply/<int:reply_id>/edit/", views.edit_reply, name="edit_reply"),
    path("reply/<int:reply_id>/delete/", views.delete_reply, name="delete_reply"),
    path("course/<int:course_id>/overview/", views.course_overview, name="course_overview"),


    path(
        "course/<int:course_id>/student/<int:student_id>/history/",views.student_history, name="student_history"),
    path("recent-notifications/", views.instructor_recent_notifications, name="recent_notifications"),
    path("notifications/", views.instructor_notifications_page, name="instructor_notifications"),
    path("mark-read/<int:notif_id>/", views.instructor_mark_read, name="mark_notification_read"),
    path("mark-all-read/", views.instructor_mark_all_read, name="mark_notifications_read"),

    path("account-settings/", views.instructor_account_settings, name="account_settings"),

    path("dashboard/", views.instructor_dashboard, name="instructor_dashboard"),

    # Create Course 
    #path("add_course/", views.add_course, name="add_course"),

    # Edit Course
    path("courses/<int:course_id>/edit/", views.edit_course, name="edit_course"),

    # Save Course Structure
    path("save/", views.save_course, name="save_course"),

    # Publish Course
    path("publish/<int:course_id>/", views.publish_course, name="publish_course"),

    # Module Editor
    path("courses/<int:course_id>/module/<int:module_id>/edit/",
         views.edit_module, name="edit_module"),

    path("courses/<int:course_id>/module/<int:module_id>/module_add/",
         views.add_module, name="add_module"),

    # Create Module (Before Editing)
    path("module/create/", views.create_module, name="create_module"),

    # Save Module (including lectures)
    path("module/<int:module_id>/save/", views.save_module, name="save_module"),

    # Delete Lecture
    path("lecture/<int:lecture_id>/delete/", views.delete_lecture, name="delete_lecture"),
    path("module/<int:module_id>/delete/", views.delete_module, name="delete_module"),

]
    

   
