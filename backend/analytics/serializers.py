from rest_framework import serializers

from .models import Course, Student, Enrollment, Assessment


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = [
            "id",
            "code_module",
            "code_presentation",
            "module_presentation_length",
        ]

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            "id",
            "id_student",
            "gender",
            "region",
            "highest_education",
            "disability",
        ]

class EnrollmentSerializer(serializers.ModelSerializer):
    student_id = serializers.IntegerField(
        source="student.id_student",
        read_only=True,
    )
    code_module = serializers.CharField(
        source="course.code_module",
        read_only=True,
    )
    code_presentation = serializers.CharField(
        source="course.code_presentation",
        read_only=True,
    )

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "student_id",
            "code_module",
            "code_presentation",
            "age_band",
            "num_of_prev_attempts",
            "studied_credits",
            "final_result",
            "date_registration",
            "date_unregistration",
        ]

class AssessmentSerializer(serializers.ModelSerializer):
    student_id = serializers.IntegerField(
        source="enrollment.student.id_student",
        read_only=True,
    )
    code_module = serializers.CharField(
        source="enrollment.course.code_module",
        read_only=True,
    )
    code_presentation = serializers.CharField(
        source="enrollment.course.code_presentation",
        read_only=True,
    )

    class Meta:
        model = Assessment
        fields = [
            "id",
            "student_id",
            "code_module",
            "code_presentation",
            "id_assessment",
            "assessment_type",
            "assessment_date",
            "weight",
            "date_submitted",
            "is_banked",
            "score",
        ]

class CourseEngagementSerializer(serializers.Serializer):
    code_module = serializers.CharField()
    code_presentation = serializers.CharField()
    total_clicks = serializers.IntegerField()
    active_students = serializers.IntegerField()
    interaction_records = serializers.IntegerField()


class CourseSuccessRateSerializer(serializers.Serializer):
    code_module = serializers.CharField()
    code_presentation = serializers.CharField()

    total_enrollments = serializers.IntegerField()
    passed_enrollments = serializers.IntegerField()
    failed_enrollments = serializers.IntegerField()
    withdrawn_enrollments = serializers.IntegerField()
    completed_enrollments = serializers.IntegerField()

    success_rate = serializers.SerializerMethodField()

    def get_success_rate(self, obj):
        passed = obj["passed_enrollments"]
        completed = obj["completed_enrollments"]

        if completed == 0:
            return None

        return round((passed / completed) * 100, 2)
