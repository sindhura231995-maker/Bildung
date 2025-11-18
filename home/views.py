from django.shortcuts import redirect, render
from courses.models import Course
from django.db.models import Count

def smart_home(request):

    # Step 1: Get top 4 popular courses based on title repetition
    popular_titles_qs = (
        Course.objects
        .values('title', 'category')
        .annotate(count=Count('title'))
        .order_by('-count', '-id')[:4]
    )

    popular_titles = list(popular_titles_qs)
    print("Popular courses queryset:", popular_titles)

    courses = Course.objects.all()[:6]
    if request.user.is_authenticated:
        if request.user.role == "student":
            return redirect('student_dashboard')
        elif request.user.role == "instructor":
            return redirect('instructor:instructor_dashboard')
        elif request.user.role == "admin":
            return redirect('admin_dashboard')

    context = {
        'courses': courses,
        'popular_courses': popular_titles,
    }

    return render(request, 'home/guest_home.html', context)