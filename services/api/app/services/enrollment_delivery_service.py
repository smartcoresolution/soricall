from dataclasses import dataclass
from typing import Protocol

from app.core.config import get_settings


@dataclass(frozen=True)
class EnrollmentDelivery:
    channel: str
    enrollment_url: str


class EnrollmentDeliveryProvider(Protocol):
    def prepare(self, token: str) -> EnrollmentDelivery: ...


class DevelopmentLinkProvider:
    def prepare(self, token: str) -> EnrollmentDelivery:
        return EnrollmentDelivery(
            channel="DEVELOPMENT_LINK",
            enrollment_url=f"/soricall/enroll?token={token}",
        )


def get_enrollment_delivery_provider() -> EnrollmentDeliveryProvider:
    backend = get_settings().enrollment_delivery_backend
    if backend == "development_link":
        return DevelopmentLinkProvider()
    raise RuntimeError(f"enrollment delivery backend is not configured: {backend}")
