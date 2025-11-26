# File: apps/tcc/usecase/services/controllers/donation_controller.py

import logging
from typing import Dict, Any, Optional, List
from apps.core.schemas.common.response import APIResponse
from apps.tcc.usecase.services.auth.base_controller import BaseController
from apps.core.core_validators.decorators import validate
from apps.tcc.models.base.enums import DonationStatus

# Import Schemas (based on your 'donations.py' file)
from apps.core.schemas.schemas.donations import (
    DonationCreateSchema, DonationUpdateSchema, 
    FundTypeCreateSchema, FundTypeUpdateSchema
)

# Import Use Case types for Constructor Injection (DI)
from apps.tcc.usecase.usecases.donations.donaiton_create import CreateDonationUseCase, CreateFundTypeUseCase
from apps.tcc.usecase.usecases.donations.donaiton_update import UpdateDonationUseCase, UpdateFundTypeUseCase
from apps.tcc.usecase.usecases.donations.donation_read import (
    GetDonationByIdUseCase, GetAllDonationsUseCase, GetUserDonationsUseCase,
    GetDonationsByStatusUseCase, GetDonationsByFundUseCase, GetDonationStatsUseCase,
    GetFundTypeByIdUseCase, GetAllFundTypesUseCase, GetActiveFundTypesUseCase
)
from apps.tcc.usecase.usecases.donations.donation_delete import DeleteDonationUseCase, DeleteFundTypeUseCase

# Import the assumed specific exception handler decorator
# NOTE: This must be implemented and imported correctly
from apps.tcc.usecase.services.exceptions.donation_handler_exceptions import handle_donation_exceptions 

logger = logging.getLogger(__name__)


class DonationController(BaseController):
    """
    Donation Controller: Handles all API operations for Donations and Fund Types.
    Uses Dependency Injection to receive all Use Cases.
    """
    
    # --- 1. CONSTRUCTOR INJECTION (The Dependency Glue) ---
    def __init__(
        self,
        # Donation UCs
        create_donation_uc: CreateDonationUseCase,
        update_donation_uc: UpdateDonationUseCase,
        delete_donation_uc: DeleteDonationUseCase,
        get_donation_by_id_uc: GetDonationByIdUseCase,
        get_all_donations_uc: GetAllDonationsUseCase,
        get_user_donations_uc: GetUserDonationsUseCase,
        get_donations_by_status_uc: GetDonationsByStatusUseCase,
        get_donations_by_fund_uc: GetDonationsByFundUseCase,
        get_donation_stats_uc: GetDonationStatsUseCase,
        # Fund Type UCs
        create_fund_type_uc: CreateFundTypeUseCase,
        update_fund_type_uc: UpdateFundTypeUseCase,
        delete_fund_type_uc: DeleteFundTypeUseCase,
        get_fund_type_by_id_uc: GetFundTypeByIdUseCase,
        get_all_fund_types_uc: GetAllFundTypesUseCase,
        get_active_fund_types_uc: GetActiveFundTypesUseCase,
    ):
        # Assign all injected Use Cases
        self.create_donation_uc = create_donation_uc
        self.update_donation_uc = update_donation_uc
        self.delete_donation_uc = delete_donation_uc
        self.get_donation_by_id_uc = get_donation_by_id_uc
        self.get_all_donations_uc = get_all_donations_uc
        self.get_user_donations_uc = get_user_donations_uc
        self.get_donations_by_status_uc = get_donations_by_status_uc
        self.get_donations_by_fund_uc = get_donations_by_fund_uc
        self.get_donation_stats_uc = get_donation_stats_uc

        self.create_fund_type_uc = create_fund_type_uc
        self.update_fund_type_uc = update_fund_type_uc
        self.delete_fund_type_uc = delete_fund_type_uc
        self.get_fund_type_by_id_uc = get_fund_type_by_id_uc
        self.get_all_fund_types_uc = get_all_fund_types_uc
        self.get_active_fund_types_uc = get_active_fund_types_uc

    # ----------------------------------------------------------------------
    # A. DONATION API ENDPOINTS
    # ----------------------------------------------------------------------

    @handle_donation_exceptions
    @validate.validate_input(DonationCreateSchema)
    async def create_donation(
        self, 
        input_data: Dict[str, Any], 
        current_user: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """Endpoint to create a new donation."""
        # Controller sends validated data to the Use Case
        return await self.create_donation_uc.execute(input_data, current_user, context or {})

    @handle_donation_exceptions
    @validate.validate_input(DonationUpdateSchema)
    async def update_donation(
        self, 
        donation_id: str,
        input_data: Dict[str, Any], 
        current_user: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """Endpoint to update an existing donation."""
        input_data['donation_id'] = donation_id
        return await self.update_donation_uc.execute(input_data, current_user, context or {})

    @handle_donation_exceptions
    async def get_donation_by_id(
        self, 
        donation_id: str,
        current_user: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """Endpoint to retrieve a donation by its ID."""
        input_data = {'donation_id': donation_id}
        return await self.get_donation_by_id_uc.execute(input_data, current_user, context or {})

    @handle_donation_exceptions
    async def get_all_donations(
        self, 
        page: int = 1,
        per_page: int = 20,
        current_user: Any = None,
        context: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """Endpoint to retrieve a paginated list of all donations."""
        input_data = {'page': page, 'per_page': per_page}
        return await self.get_all_donations_uc.execute(input_data, current_user, context or {})

    @handle_donation_exceptions
    async def get_donations_by_fund(
        self, 
        fund_id: str,
        current_user: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """Endpoint to get all donations for a specific fund."""
        input_data = {'fund_id': fund_id}
        return await self.get_donations_by_fund_uc.execute(input_data, current_user, context or {})

    @handle_donation_exceptions
    async def get_donation_statistics(
        self, 
        current_user: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """Endpoint to get aggregated donation statistics."""
        return await self.get_donation_stats_uc.execute({}, current_user, context or {})

    # ----------------------------------------------------------------------
    # B. FUND TYPE API ENDPOINTS
    # ----------------------------------------------------------------------

    @handle_donation_exceptions
    @validate.validate_input(FundTypeCreateSchema)
    async def create_fund_type(
        self, 
        input_data: Dict[str, Any], 
        current_user: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """Endpoint to create a new fund type."""
        return await self.create_fund_type_uc.execute(input_data, current_user, context or {})

    @handle_donation_exceptions
    @validate.validate_input(FundTypeUpdateSchema)
    async def update_fund_type(
        self, 
        fund_id: str,
        input_data: Dict[str, Any], 
        current_user: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """Endpoint to update an existing fund type."""
        input_data['fund_id'] = fund_id
        return await self.update_fund_type_uc.execute(input_data, current_user, context or {})

    @handle_donation_exceptions
    async def get_fund_type_by_id(
        self, 
        fund_id: str,
        current_user: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """Endpoint to retrieve a fund type by its ID."""
        input_data = {'fund_id': fund_id}
        return await self.get_fund_type_by_id_uc.execute(input_data, current_user, context or {})

    @handle_donation_exceptions
    async def get_active_fund_types(
        self, 
        current_user: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """Endpoint to retrieve all currently active fund types."""
        return await self.get_active_fund_types_uc.execute({}, current_user, context or {})

    @handle_donation_exceptions
    async def delete_fund_type(
        self, 
        fund_id: str,
        current_user: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """Endpoint to soft delete a fund type."""
        input_data = {'fund_id': fund_id}
        return await self.delete_fund_type_uc.execute(input_data, current_user, context or {})


# ----------------------------------------------------------------------
# 2. CONTROLLER FACTORY (The final step in the Dependency Layer)
# ----------------------------------------------------------------------

# NOTE: This factory should be placed in your dependency file (e.g., donation_dependencies.py)
# for true isolation, but it's shown here for context.

from apps.tcc.usecase.dependencies.donation_dependencies import (
    get_create_donation_uc, get_update_donation_uc, get_delete_donation_uc,
    get_get_donation_by_id_uc, get_get_all_donations_uc, get_get_user_donations_uc,
    get_get_donations_by_status_uc, get_get_donations_by_fund_uc, get_get_donation_stats_uc,
    get_create_fund_type_uc, get_update_fund_type_uc, get_delete_fund_type_uc,
    get_get_fund_type_by_id_uc, get_get_all_fund_types_uc, get_get_active_fund_types_uc
)

def create_donation_controller_factory() -> DonationController:
    """
    Factory function to create a fully wired DonationController instance 
    by injecting all Use Cases from the dependency layer.
    """
    return DonationController(
        # Donation UCs
        create_donation_uc=get_create_donation_uc(),
        update_donation_uc=get_update_donation_uc(),
        delete_donation_uc=get_delete_donation_uc(),
        get_donation_by_id_uc=get_get_donation_by_id_uc(),
        get_all_donations_uc=get_get_all_donations_uc(),
        get_user_donations_uc=get_get_user_donations_uc(),
        get_donations_by_status_uc=get_get_donations_by_status_uc(),
        get_donations_by_fund_uc=get_get_donations_by_fund_uc(),
        get_donation_stats_uc=get_get_donation_stats_uc(),
        # Fund Type UCs
        create_fund_type_uc=get_create_fund_type_uc(),
        update_fund_type_uc=get_update_fund_type_uc(),
        delete_fund_type_uc=get_delete_fund_type_uc(),
        get_fund_type_by_id_uc=get_get_fund_type_by_id_uc(),
        get_all_fund_types_uc=get_get_all_fund_types_uc(),
        get_active_fund_types_uc=get_get_active_fund_types_uc(),
    )