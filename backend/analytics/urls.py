from django.urls import path

from .views import CourseListAPIView, StudentListAPIView, EnrollmentListAPIView, AssessmentListAPIView, CourseEngagementAPIView, CourseSuccessRateAPIView

urlpatterns = [
    path("courses/", CourseListAPIView.as_view(), name="course-list"),
    path("students/", StudentListAPIView.as_view(), name="student-list"),
    path("enrollments/", EnrollmentListAPIView.as_view(), name="enrollment-list"),
    path("assessments/", AssessmentListAPIView.as_view(), name="assessment-list"),
    path("analytics/engagement-by-course/", CourseEngagementAPIView.as_view(), name="course-engagement"),
    path("analytics/success-rate-by-course/", CourseSuccessRateAPIView.as_view(), name="course-success-rate"),
]