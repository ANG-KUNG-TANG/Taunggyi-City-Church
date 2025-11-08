
from users.user_repo import UserRepository
from event.events import EventRepository, EventRegistrationRepository
from sermons.sermons import SermonRepository, SermonMediaRepository
from prayers.prayer import PrayerRequestRepository, PrayerResponseRepository
from donations.donations import DonationRepository, FundTypeRepository

class RepositoryFactory:
    """
    Factory class to provide repository instances
    """
    
    @staticmethod
    def get_user_repository() -> UserRepository:
        return UserRepository()
    
    @staticmethod
    def get_event_repository() -> EventRepository:
        return EventRepository()
    
    @staticmethod
    def get_event_registration_repository() -> EventRegistrationRepository:
        return EventRegistrationRepository()
    
    @staticmethod
    def get_sermon_repository() -> SermonRepository:
        return SermonRepository()
    
    @staticmethod
    def get_sermon_media_repository() -> SermonMediaRepository:
        return SermonMediaRepository()
    
    @staticmethod
    def get_prayer_request_repository() -> PrayerRequestRepository:
        return PrayerRequestRepository()
    
    @staticmethod
    def get_prayer_response_repository() -> PrayerResponseRepository:
        return PrayerResponseRepository()
    
    @staticmethod
    def get_donation_repository() -> DonationRepository:
        return DonationRepository()
    
    @staticmethod
    def get_fund_type_repository() -> FundTypeRepository:
        return FundTypeRepository()

# Convenience imports
__all__ = [
    'RepositoryFactory',
    'UserRepository',
    'EventRepository',
    'EventRegistrationRepository',
    'SermonRepository', 
    'SermonMediaRepository',
    'PrayerRequestRepository',
    'PrayerResponseRepository',
    'DonationRepository',
    'FundTypeRepository',
]