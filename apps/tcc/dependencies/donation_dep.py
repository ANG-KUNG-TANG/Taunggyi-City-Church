
# from apps.tcc.usecase.repo.domain_repo.donations import DonationRepository, FundRepository
# from apps.tcc.usecase.usecases.donations.donaiton_create import (
#     CreateDonationUseCase, 
#     CreateFundTypeUseCase
# )
# from apps.tcc.usecase.usecases.donations.donaiton_update import (
#     UpdateDonationUseCase, 
#     UpdateFundTypeUseCase
# )
# from apps.tcc.usecase.usecases.donations.donation_read import (
#     GetDonationByIdUseCase, 
#     GetAllDonationsUseCase, 
#     GetUserDonationsUseCase, 
#     GetDonationsByStatusUseCase, 
#     GetFundTypeByIdUseCase, 
#     GetAllFundTypesUseCase, 
#     GetActiveFundTypesUseCase, 
#     GetDonationsByFundUseCase, 
#     GetDonationStatsUseCase
# )
# from apps.tcc.usecase.usecases.donations.donation_delete import (
#     DeleteDonationUseCase, 
#     DeleteFundTypeUseCase
# )

# # --- Repository Providers ---

# def get_donation_repository() -> DonationRepository:
#     """Provides a DonationRepository instance."""
#     return DonationRepository()

# def get_fund_repository() -> FundRepository:
#     """Provides a FundRepository instance."""
#     return FundRepository()

# # --- Use Case Providers (Dependency Factories) ---

# # --- Create Use Cases ---

# def get_create_donation_uc() -> CreateDonationUseCase:
#     """Factory for CreateDonationUseCase."""
#     return CreateDonationUseCase(
#         donation_repository=get_donation_repository(),
#         fund_repository=get_fund_repository()
#     )

# def get_create_fund_type_uc() -> CreateFundTypeUseCase:
#     """Factory for CreateFundTypeUseCase."""
#     return CreateFundTypeUseCase(
#         fund_repository=get_fund_repository()
#     )

# # --- Read Use Cases ---

# def get_get_donation_by_id_uc() -> GetDonationByIdUseCase:
#     """Factory for GetDonationByIdUseCase."""
#     return GetDonationByIdUseCase(
#         donation_repository=get_donation_repository()
#     )
    
# def get_get_all_donations_uc() -> GetAllDonationsUseCase:
#     """Factory for GetAllDonationsUseCase."""
#     return GetAllDonationsUseCase(
#         donation_repository=get_donation_repository()
#     )

# def get_get_user_donations_uc() -> GetUserDonationsUseCase:
#     """Factory for GetUserDonationsUseCase."""
#     return GetUserDonationsUseCase(
#         donation_repository=get_donation_repository()
#     )
    
# def get_get_donations_by_status_uc() -> GetDonationsByStatusUseCase:
#     """Factory for GetDonationsByStatusUseCase."""
#     return GetDonationsByStatusUseCase(
#         donation_repository=get_donation_repository()
#     )
    
# def get_get_fund_type_by_id_uc() -> GetFundTypeByIdUseCase:
#     """Factory for GetFundTypeByIdUseCase."""
#     return GetFundTypeByIdUseCase(
#         fund_repository=get_fund_repository()
#     )

# def get_get_all_fund_types_uc() -> GetAllFundTypesUseCase:
#     """Factory for GetAllFundTypesUseCase."""
#     return GetAllFundTypesUseCase(
#         fund_repository=get_fund_repository()
#     )
    
# def get_get_active_fund_types_uc() -> GetActiveFundTypesUseCase:
#     """Factory for GetActiveFundTypesUseCase."""
#     return GetActiveFundTypesUseCase(
#         fund_repository=get_fund_repository()
#     )

# def get_get_donations_by_fund_uc() -> GetDonationsByFundUseCase:
#     """Factory for GetDonationsByFundUseCase."""
#     return GetDonationsByFundUseCase(
#         donation_repository=get_donation_repository()
#     )

# def get_get_donation_stats_uc() -> GetDonationStatsUseCase:
#     """Factory for GetDonationStatsUseCase."""
#     return GetDonationStatsUseCase(
#         donation_repository=get_donation_repository()
#     )

# # --- Update Use Cases ---

# def get_update_donation_uc() -> UpdateDonationUseCase:
#     """Factory for UpdateDonationUseCase."""
#     return UpdateDonationUseCase(
#         donation_repository=get_donation_repository(),
#         fund_repository=get_fund_repository()
#     )

# def get_update_fund_type_uc() -> UpdateFundTypeUseCase:
#     """Factory for UpdateFundTypeUseCase."""
#     return UpdateFundTypeUseCase(
#         fund_repository=get_fund_repository()
#     )
    
# # --- Delete Use Cases ---

# def get_delete_donation_uc() -> DeleteDonationUseCase:
#     """Factory for DeleteDonationUseCase."""
#     return DeleteDonationUseCase(
#         donation_repository=get_donation_repository()
#     )

# def get_delete_fund_type_uc() -> DeleteFundTypeUseCase:
#     """Factory for DeleteFundTypeUseCase."""
#     return DeleteFundTypeUseCase(
#         donation_repository=get_donation_repository(),
#         fund_repository=get_fund_repository()
#     )