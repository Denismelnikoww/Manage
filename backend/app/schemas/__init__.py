from app.schemas.auth import RoleResponse, TokenResponse, UserLogin, UserRegister, UserResponse
from app.schemas.lab_work import (
    LabWorkBase,
    LabWorkCreate,
    LabWorkUpdate,
    LabWorkResponse,
    LabWorkListResponse,
)
from app.schemas.report import (
    CommentCreateRequest,
    CommentResponse,
    ErrorResponse,
    PresignedDownloadResponse,
    ReportListResponse,
    ReportResponse,
    SubmissionUploadInfo,
    SubmissionUploadResponse,
)

__all__ = [
    "LabWorkBase",
    "LabWorkCreate",
    "LabWorkUpdate",
    "LabWorkResponse",
    "LabWorkListResponse",
    "RoleResponse",
    "TokenResponse",
    "UserLogin",
    "UserRegister",
    "UserResponse",
    "CommentCreateRequest",
    "CommentResponse",
    "ErrorResponse",
    "PresignedDownloadResponse",
    "ReportListResponse",
    "ReportResponse",
    "SubmissionUploadInfo",
    "SubmissionUploadResponse",
]