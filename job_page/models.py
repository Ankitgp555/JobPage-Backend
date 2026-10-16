from django.db import models

class BasicInformation(models.Model):
    # Basic Information
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()

    # Contact Information
    email = models.EmailField(unique=True)
    primary_phone = models.CharField(max_length=20)
    alternate_phone = models.CharField(max_length=20, blank=True)

    # Address
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)

    # Professional Links
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    other_professional_link = models.URLField(blank=True)

    # Cover Letter
    cover_letter_text = models.TextField(blank=True)
    cover_letter_file = models.FileField(
        upload_to="cover_letters/",
        blank=True,
    )

    JOB_CHOICES = [
    ("trainee", "Trainee"),
    ("frontend_developer", "Frontend Developer"),
    ("backend_developer", "Backend Developer"),
    ("full_stack_developer", "Full Stack Developer"),
    ("python_developer", "Python Developer"),
    ("django_developer", "Django Developer"),
    ("react_developer", "React Developer"),
    ("software_developer", "Software Developer"),
    ]

    NOTICE_PERIOD_CHOICES = [
        ("na_fresher", "N/A — Fresher"),
        ("immediate", "Immediate Joiner"),
        ("15_days", "15 Days"),
        ("30_days", "30 Days"),
        ("45_days", "45 Days"),
        ("60_days", "60 Days"),
        ("90_days", "90 Days"),
        ("other", "Other"),
    ]

    # Job Application
    job_title = models.CharField(
        max_length=50,
        choices=JOB_CHOICES,
    )

    # Notice Period
    notice_period = models.CharField(
        max_length=20,
        choices=NOTICE_PERIOD_CHOICES,
        default="na_fresher",
    )

    # Record Creation
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class PersonalDetails(models.Model):
    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
        ("prefer_not_to_say", "Prefer not to say"),
    ]

    candidate = models.OneToOneField(
        BasicInformation,
        on_delete=models.CASCADE,
        related_name="personal_details",
    )

    gender = models.CharField(max_length=20, choices=GENDER_CHOICES)
    blood_group = models.CharField(max_length=5, blank=True)
    nationality = models.CharField(max_length=100)
    marital_status = models.CharField(max_length=20, blank=True)
    father_name = models.CharField(max_length=200)
    mother_name = models.CharField(max_length=200)

    def __str__(self):
        return f"Personal Details - Candidate #{self.candidate_id}"



class Resume(models.Model):
    candidate = models.OneToOneField(
        BasicInformation,
        on_delete=models.CASCADE,
        related_name="resume",
    )

    file = models.FileField(upload_to="resumes/")
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveBigIntegerField()

    def __str__(self):
        return self.original_filename

class Education(models.Model):
    candidate = models.ForeignKey(
        BasicInformation,
        on_delete=models.CASCADE,
        related_name="educations",
    )

    qualification_level = models.CharField(max_length=50)
    degree = models.CharField(max_length=150)
    specialization = models.CharField(max_length=150, blank=True)
    institution = models.CharField(max_length=200)
    university_board = models.CharField(max_length=200, blank=True)
    institution_location = models.CharField(max_length=200, blank=True)

    start_date = models.DateField(null=True, blank=True)
    graduation_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    currently_studying = models.BooleanField(default=False)

    grade = models.CharField(max_length=30, blank=True)
    backlogs = models.PositiveIntegerField(default=0)

    education_document = models.FileField(
        upload_to="education_documents/",
        blank=True,
    )

    def __str__(self):
        return f"{self.degree} - {self.institution}"


class Experience(models.Model):
    candidate = models.ForeignKey(
        BasicInformation,
        on_delete=models.CASCADE,
        related_name="experiences",
    )

    company = models.CharField(max_length=200)
    job_title = models.CharField(max_length=150)
    employment_type = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    currently_working = models.BooleanField(default=False)
    company_location = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.job_title} at {self.company}"

class Consent(models.Model):
    candidate = models.OneToOneField(
        BasicInformation,
        on_delete=models.CASCADE,
        related_name="consent",
    )

    consent_given = models.BooleanField(default=False)

    def __str__(self):
        return f"Consent - Candidate #{self.candidate_id}"