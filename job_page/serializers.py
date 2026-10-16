
from urllib.parse import urlparse

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import (
    BasicInformation,
    PersonalDetails,
    Resume,
    Education,
    Experience,
    Consent,
)


class PersonalDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonalDetails
        exclude = ("candidate",)


class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        exclude = ("candidate",)
        read_only_fields = ("original_filename", "file_size")

    def validate_file(self, value):
        if not value:
            raise serializers.ValidationError(
                "Please upload your resume."
            )

        if not value.name.lower().endswith((".pdf", ".doc", ".docx")):
            raise serializers.ValidationError(
                "Only PDF, DOC, and DOCX files are allowed."
            )

        return value


class EducationSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Education
        exclude = ("candidate",)

    def validate_graduation_year(self, value):
        if value is None:
            return value

        year = str(value)

        if len(year) != 4 or not 1900 <= value <= 2200:
            raise serializers.ValidationError(
                "Enter a valid four-digit graduation year."
            )

        return value

    def validate_backlogs(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "Backlogs must be a non-negative whole number."
            )

        return value


class ExperienceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Experience
        exclude = ("candidate",)

    def validate(self, attrs):
        start_date = attrs.get(
            "start_date",
            getattr(self.instance, "start_date", None),
        )
        end_date = attrs.get(
            "end_date",
            getattr(self.instance, "end_date", None),
        )
        currently_working = attrs.get(
            "currently_working",
            getattr(self.instance, "currently_working", False),
        )

        errors = {}

        if not currently_working and not end_date:
            errors["end_date"] = (
                "End date is required when you are not currently working."
            )

        if start_date and end_date and end_date < start_date:
            errors["end_date"] = (
                "End date cannot be before the start date."
            )

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


class ConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consent
        exclude = ("candidate",)


class BasicInformationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        validators=[
            UniqueValidator(
                queryset=BasicInformation.objects.all(),
                message=(
                    "An application with this email address "
                    "already exists."
                ),
            )
        ]
    )

    personal_details = PersonalDetailsSerializer(required=False)
    resume = ResumeSerializer(required=False)
    educations = EducationSerializer(many=True, required=False)
    experiences = ExperienceSerializer(many=True, required=False)
    consent = ConsentSerializer(required=False)

    class Meta:
        model = BasicInformation
        fields = "__all__"
        read_only_fields = ("id", "created_at")

    def validate_date_of_birth(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError(
                "Date of birth cannot be in the future."
            )

        return value

    def validate(self, attrs):
        errors = {}

        # Validate professional URLs when supplied.
        url_fields = [
            "linkedin_url",
            "github_url",
            "portfolio_url",
            "other_professional_link",
        ]

        for field in url_fields:
            value = attrs.get(field)

            if value:
                parsed_url = urlparse(value)

                if (
                    parsed_url.scheme not in ("http", "https")
                    or not parsed_url.netloc
                ):
                    errors[field] = (
                        "Enter a valid URL starting with "
                        "http:// or https://."
                    )

        # Creation-only validation.
        # Partial updates can omit these sections.
        if self.instance is None:
            if "personal_details" not in attrs:
                errors["personal_details"] = (
                    "Personal details are required."
                )

            if not attrs.get("educations"):
                errors["educations"] = (
                    "At least one education record is required."
                )

            resume_data = attrs.get("resume", {})

            if not resume_data or not resume_data.get("file"):
                errors["resume"] = "Please upload your resume."

            consent_data = attrs.get("consent", {})

            if consent_data.get("consent_given") is not True:
                errors["consent"] = (
                    "You must provide consent to submit your application."
                )

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        personal_data = validated_data.pop("personal_details")
        resume_data = validated_data.pop("resume")
        educations_data = validated_data.pop("educations")
        experiences_data = validated_data.pop("experiences", [])
        consent_data = validated_data.pop("consent")

        candidate = BasicInformation.objects.create(**validated_data)

        PersonalDetails.objects.create(
            candidate=candidate,
            **personal_data,
        )

        file_obj = resume_data["file"]

        Resume.objects.create(
            candidate=candidate,
            file=file_obj,
            original_filename=file_obj.name,
            file_size=file_obj.size,
        )

        for item in educations_data:
            Education.objects.create(
                candidate=candidate,
                **item,
            )

        for item in experiences_data:
            Experience.objects.create(
                candidate=candidate,
                **item,
            )

        Consent.objects.create(
            candidate=candidate,
            **consent_data,
        )

        return candidate

    @transaction.atomic
    def update(self, instance, validated_data):
        personal_data = validated_data.pop(
            "personal_details", None
        )
        resume_data = validated_data.pop("resume", None)
        educations_data = validated_data.pop("educations", None)
        experiences_data = validated_data.pop("experiences", None)
        consent_data = validated_data.pop("consent", None)

        # Update main candidate fields.
        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.save()

        # Update personal details.
        if personal_data is not None:
            details, _ = PersonalDetails.objects.get_or_create(
                candidate=instance
            )

            for field, value in personal_data.items():
                setattr(details, field, value)

            details.save()

        # Update resume only if a new file is supplied.
        if resume_data is not None:
            new_file = resume_data.get("file")

            if new_file:
                resume = getattr(instance, "resume", None)

                if resume is None:
                    Resume.objects.create(
                        candidate=instance,
                        file=new_file,
                        original_filename=new_file.name,
                        file_size=new_file.size,
                    )
                else:
                    resume.file = new_file
                    resume.original_filename = new_file.name
                    resume.file_size = new_file.size
                    resume.save()

        # Update education records by ID, create new records,
        # and delete existing records omitted from the list.
        if educations_data is not None:
            existing = {
                item.id: item
                for item in instance.educations.all()
            }
            retained_ids = set()

            for item_data in educations_data:
                item_id = item_data.pop("id", None)

                if item_id is not None:
                    item = existing.get(item_id)

                    if item is None:
                        raise serializers.ValidationError({
                            "educations": (
                                f"Invalid education ID: {item_id}"
                            )
                        })

                    for field, value in item_data.items():
                        setattr(item, field, value)

                    item.save()
                else:
                    item = Education.objects.create(
                        candidate=instance,
                        **item_data,
                    )

                retained_ids.add(item.id)

            instance.educations.exclude(
                id__in=retained_ids
            ).delete()

        # Update experience records by ID, create new records,
        # and delete existing records omitted from the list.
        if experiences_data is not None:
            existing = {
                item.id: item
                for item in instance.experiences.all()
            }
            retained_ids = set()

            for item_data in experiences_data:
                item_id = item_data.pop("id", None)

                if item_id is not None:
                    item = existing.get(item_id)

                    if item is None:
                        raise serializers.ValidationError({
                            "experiences": (
                                f"Invalid experience ID: {item_id}"
                            )
                        })

                    for field, value in item_data.items():
                        setattr(item, field, value)

                    item.save()
                else:
                    item = Experience.objects.create(
                        candidate=instance,
                        **item_data,
                    )

                retained_ids.add(item.id)

            instance.experiences.exclude(
                id__in=retained_ids
            ).delete()

        # Update consent.
        if consent_data is not None:
            consent, _ = Consent.objects.get_or_create(
                candidate=instance
            )

            for field, value in consent_data.items():
                setattr(consent, field, value)

            consent.save()

        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)

        data["personal_details"] = (
            PersonalDetailsSerializer(
                instance.personal_details
            ).data
            if hasattr(instance, "personal_details")
            else None
        )

        data["resume"] = (
            ResumeSerializer(instance.resume).data
            if hasattr(instance, "resume")
            else None
        )

        data["educations"] = EducationSerializer(
            instance.educations.all(),
            many=True,
        ).data

        data["experiences"] = ExperienceSerializer(
            instance.experiences.all(),
            many=True,
        ).data

        data["consent"] = (
            ConsentSerializer(instance.consent).data
            if hasattr(instance, "consent")
            else None
        )

        return data

    
    
    def validate_cover_letter_file(self, value):
        if value and not value.name.lower().endswith(
            (".pdf", ".doc", ".docx")
        ):
            raise serializers.ValidationError(
                "Only PDF, DOC, and DOCX files are allowed."
            )

        return value

