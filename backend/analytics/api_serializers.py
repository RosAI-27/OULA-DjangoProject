from rest_framework import serializers

from .models import Assessment, Course, Enrollment, Student


class CourseSerializer(serializers.ModelSerializer):
    inscrits = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = [
            "id", "code_module", "code_presentation",
            "module_presentation_length", "inscrits",
        ]


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            "id_student", "gender", "region",
            "highest_education", "imd_band", "disability",
        ]


class EnrollmentSerializer(serializers.ModelSerializer):
    id_student = serializers.IntegerField(source="student.id_student", read_only=True)
    code_module = serializers.CharField(source="course.code_module", read_only=True)
    code_presentation = serializers.CharField(source="course.code_presentation", read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            "id", "id_student", "code_module", "code_presentation", "age_band",
            "num_of_prev_attempts", "studied_credits", "final_result",
            "date_registration", "date_unregistration",
        ]


class AssessmentSerializer(serializers.ModelSerializer):
    id_student = serializers.IntegerField(
        source="enrollment.student.id_student", read_only=True
    )
    code_module = serializers.CharField(
        source="enrollment.course.code_module", read_only=True
    )
    code_presentation = serializers.CharField(
        source="enrollment.course.code_presentation", read_only=True
    )

    class Meta:
        model = Assessment
        fields = [
            "id", "id_student", "code_module", "code_presentation",
            "id_assessment", "assessment_type", "assessment_date",
            "weight", "date_submitted", "is_banked", "score",
        ]