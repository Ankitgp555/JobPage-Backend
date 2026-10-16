
import json

from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BasicInformation
from .serializers import BasicInformationSerializer


class JobApplicationCreateView(APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def parse_candidate_data(self, request):
        """
        Read application data from JSON or multipart/form-data.
        Return (data, error_response).
        """
        content_type = (request.content_type or "").lower()

        if content_type.startswith("application/json"):
            data = request.data.copy()

        else:
            candidate_data = request.data.get("candidate_data")

            if not candidate_data:
                return None, Response(
                    {
                        "message": (
                            "The candidate_data JSON field is required."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                data = json.loads(candidate_data)
            except (json.JSONDecodeError, TypeError, ValueError):
                return None, Response(
                    {
                        "message": (
                            "candidate_data must contain valid JSON."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if not isinstance(data, dict):
            return None, Response(
                {
                    "message": (
                        "Application data must be a JSON object."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # File attachment is only relevant to multipart requests.
        if not content_type.startswith("application/json"):
            # Attach an optional cover letter.
            cover_letter = request.FILES.get("cover_letter_file")

            if cover_letter:
                data["cover_letter_file"] = cover_letter

            # Attach the resume if a resume object was provided.
            resume_file = request.FILES.get("resume_file")

            if resume_file:
                resume_data = data.get("resume")

                if resume_data is None:
                    data["resume"] = {"file": resume_file}
                elif isinstance(resume_data, dict):
                    resume_data["file"] = resume_file
                else:
                    return None, Response(
                        {
                            "message": (
                                "The resume field must be a JSON object."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Attach education documents using their list indexes.
            educations = data.get("educations", [])

            if not isinstance(educations, list):
                return None, Response(
                    {
                        "message": "educations must be a list."
                    },
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

                document = request.FILES.get(
                    f"education_document_{index}"
                )

                if document:
                    education["education_document"] = document

        return data, None

    @transaction.atomic
    def post(self, request):
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

    def get(self, request, pk=None):
        if pk is not None:
            candidate = get_object_or_404(
                BasicInformation,
                pk=pk,
            )

            serializer = BasicInformationSerializer(candidate)

            return Response(
                {"application": serializer.data},
                status=status.HTTP_200_OK,
            )

        candidates = BasicInformation.objects.all().order_by(
            "-created_at"
        )

        serializer = BasicInformationSerializer(
            candidates,
            many=True,
        )

        return Response(
            {
                "count": candidates.count(),
                "applications": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk=None):
        if pk is None:
            return Response(
                {"message": "Application ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        candidate = get_object_or_404(
            BasicInformation,
            pk=pk,
        )
        candidate.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )

    @transaction.atomic
    def patch(self, request, pk=None):
        if pk is None:
            return Response(
                {"message": "Application ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        candidate = get_object_or_404(
            BasicInformation,
            pk=pk,
        )

        data, error_response = self.parse_candidate_data(request)

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
                "application": BasicInformationSerializer(
                    candidate
                ).data,
            },
            status=status.HTTP_200_OK,
        )
