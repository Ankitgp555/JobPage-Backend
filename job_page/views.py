
import json

from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BasicInformation
from .serializers import BasicInformationSerializer


class JobApplicationListCreateView(APIView):
    """List applications and submit new applications."""

    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def parse_candidate_data(self, request):
        """Parse JSON or multipart application data and uploaded files."""
        content_type = (request.content_type or "").lower()

        if content_type.startswith("application/json"):
            data = request.data.copy()
        else:
            candidate_data = request.data.get("candidate_data")

            if not candidate_data:
                return None, Response(
                    {"message": "The candidate_data JSON field is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                data = json.loads(candidate_data)
            except (json.JSONDecodeError, TypeError, ValueError):
                return None, Response(
                    {"message": "candidate_data must contain valid JSON."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if not isinstance(data, dict):
            return None, Response(
                {"message": "Application data must be a JSON object."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not content_type.startswith("application/json"):
            cover_letter = request.FILES.get("cover_letter_file")
            if cover_letter:
                data["cover_letter_file"] = cover_letter

            resume_file = request.FILES.get("resume_file")
            if resume_file:
                resume_data = data.get("resume")

                if resume_data is None:
                    data["resume"] = {"file": resume_file}
                elif isinstance(resume_data, dict):
                    resume_data["file"] = resume_file
                else:
                    return None, Response(
                        {"message": "The resume field must be a JSON object."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            educations = data.get("educations", [])

            if not isinstance(educations, list):
                return None, Response(
                    {"message": "educations must be a list."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            for index, education in enumerate(educations):
                if not isinstance(education, dict):
                    return None, Response(
                        {
                            "message": (
                                "Each education record must be a JSON object."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                document = request.FILES.get(f"education_document_{index}")
                if document:
                    education["education_document"] = document

        return data, None

    def get(self, request):
        """Return all applications, newest first."""
        candidates = BasicInformation.objects.all().order_by("-created_at")

        serializer = BasicInformationSerializer(candidates, many=True)

        return Response(
            {
                "count": candidates.count(),
                "applications": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def post(self, request):
        """Create a new application."""
        data, error_response = self.parse_candidate_data(request)

        if error_response:
            return error_response

        serializer = BasicInformationSerializer(data=data)

        if not serializer.is_valid():
            return Response(
                {
                    "message": "Application submission failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        candidate = serializer.save()

        return Response(
            {
                "message": "Application submitted successfully.",
                "candidate": BasicInformationSerializer(candidate).data,
            },
            status=status.HTTP_201_CREATED,
        )


class JobApplicationDetailView(APIView):
    """Retrieve, update, or delete one application."""

    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self, pk):
        return get_object_or_404(BasicInformation, pk=pk)

    def get(self, request, pk):
        """Return one application."""
        candidate = self.get_object(pk)
        serializer = BasicInformationSerializer(candidate)

        return Response(
            {"application": serializer.data},
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def patch(self, request, pk):
        """Partially update an existing application."""
        candidate = self.get_object(pk)

        # Reuse the same parsing and file-upload behavior as submission.
        data, error_response = JobApplicationListCreateView().parse_candidate_data(
            request
        )

        if error_response:
            return error_response

        serializer = BasicInformationSerializer(
            candidate,
            data=data,
            partial=True,
        )

        if not serializer.is_valid():
            return Response(
                {
                    "message": "Application update failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        candidate = serializer.save()

        return Response(
            {
                "message": "Application updated successfully.",
                "application": BasicInformationSerializer(candidate).data,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        """Delete an existing application."""
        candidate = self.get_object(pk)
        candidate.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
