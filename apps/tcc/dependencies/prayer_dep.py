from functools import lru_cache
from apps.tcc.usecase.repo.domain_repo.prayer import PrayerRepository, PrayerResponseRepository

# Import prayer use cases
from apps.tcc.usecase.usecases.prayers.prayer_create_uc import CreatePrayerRequestUseCase, CreatePrayerResponseUseCase
from apps.tcc.usecase.usecases.prayers.prayer_read import (
    GetPrayerRequestByIdUseCase,
    GetAllPrayerRequestsUseCase,
    GetPublicPrayerRequestsUseCase,
    GetUserPrayerRequestsUseCase,
    GetPrayerRequestsByCategoryUseCase,
    GetPrayerResponseByIdUseCase,
    GetPrayerResponsesForPrayerUseCase
)
from apps.tcc.usecase.usecases.prayers.prayer_update import (
    UpdatePrayerRequestUseCase,
    UpdatePrayerResponseUseCase,
    MarkPrayerRequestAnsweredUseCase
)
from apps.tcc.usecase.usecases.prayers.prayer_delete import DeletePrayerRequestUseCase, DeletePrayerResponseUseCase

# Repository Dependencies
@lru_cache()
def get_prayer_repository() -> PrayerRepository:
    """Singleton prayer repository instance"""
    return PrayerRepository()

@lru_cache()
def get_prayer_response_repository() -> PrayerResponseRepository:
    """Singleton prayer response repository instance"""
    return PrayerResponseRepository()

# Create Use Cases
def get_create_prayer_request_uc() -> CreatePrayerRequestUseCase:
    """Create prayer request use case"""
    return CreatePrayerRequestUseCase(get_prayer_repository())

def get_create_prayer_response_uc() -> CreatePrayerResponseUseCase:
    """Create prayer response use case"""
    return CreatePrayerResponseUseCase(get_prayer_response_repository())

# Read Use Cases
def get_prayer_request_by_id_uc() -> GetPrayerRequestByIdUseCase:
    """Get prayer request by ID use case"""
    return GetPrayerRequestByIdUseCase(get_prayer_repository())

def get_all_prayer_requests_uc() -> GetAllPrayerRequestsUseCase:
    """Get all prayer requests use case"""
    return GetAllPrayerRequestsUseCase(get_prayer_repository())

def get_public_prayer_requests_uc() -> GetPublicPrayerRequestsUseCase:
    """Get public prayer requests use case"""
    return GetPublicPrayerRequestsUseCase(get_prayer_repository())

def get_user_prayer_requests_uc() -> GetUserPrayerRequestsUseCase:
    """Get user prayer requests use case"""
    return GetUserPrayerRequestsUseCase(get_prayer_repository())

def get_prayer_requests_by_category_uc() -> GetPrayerRequestsByCategoryUseCase:
    """Get prayer requests by category use case"""
    return GetPrayerRequestsByCategoryUseCase(get_prayer_repository())

def get_prayer_response_by_id_uc() -> GetPrayerResponseByIdUseCase:
    """Get prayer response by ID use case"""
    return GetPrayerResponseByIdUseCase(get_prayer_response_repository())

def get_prayer_responses_for_prayer_uc() -> GetPrayerResponsesForPrayerUseCase:
    """Get prayer responses for prayer use case"""
    return GetPrayerResponsesForPrayerUseCase(get_prayer_response_repository())

# Update Use Cases
def get_update_prayer_request_uc() -> UpdatePrayerRequestUseCase:
    """Update prayer request use case"""
    return UpdatePrayerRequestUseCase(get_prayer_repository())

def get_update_prayer_response_uc() -> UpdatePrayerResponseUseCase:
    """Update prayer response use case"""
    return UpdatePrayerResponseUseCase(get_prayer_response_repository())

def get_mark_prayer_answered_uc() -> MarkPrayerRequestAnsweredUseCase:
    """Mark prayer as answered use case"""
    return MarkPrayerRequestAnsweredUseCase(get_prayer_repository())

# Delete Use Cases
def get_delete_prayer_request_uc() -> DeletePrayerRequestUseCase:
    """Delete prayer request use case"""
    return DeletePrayerRequestUseCase(get_prayer_repository())

def get_delete_prayer_response_uc() -> DeletePrayerResponseUseCase:
    """Delete prayer response use case"""
    return DeletePrayerResponseUseCase(get_prayer_response_repository())