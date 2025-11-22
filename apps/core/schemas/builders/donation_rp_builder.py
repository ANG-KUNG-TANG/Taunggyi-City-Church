from typing import Any, Dict, List
from decimal import Decimal
from apps.core.schemas.schemas.donations import DonationResponseSchema, DonationListResponseSchema, FundTypeResponseSchema, FundTypeListResponseSchema
from apps.tcc.usecase.entities.donations import DonationEntity, FundTypeEntity  # Assuming you have these entities

class DonationResponseBuilder:
    """
    Centralized builder for creating donation response schemas.
    Works like a serializer but stays framework-independent.
    Automatically maps entity attributes to response schema fields.
    """

    @staticmethod
    def to_response(entity: Any) -> DonationResponseSchema:
        """
        Convert a donation entity → DonationResponseSchema automatically.
        """
        schema_fields = DonationResponseSchema.model_fields.keys()
        
        data: Dict[str, Any] = {}
        for field in schema_fields:
            data[field] = getattr(entity, field, None)
        
        return DonationResponseSchema(**data)

    @staticmethod
    def to_list_response(entities: List[Any], total: int = None, 
                        page: int = 1, per_page: int = 20) -> DonationListResponseSchema:
        """
        Convert a list of donation entities to a paginated list response.
        """
        donation_responses = [DonationResponseBuilder.to_response(entity) for entity in entities]
        
        if total is None:
            total = len(entities)
            
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 1
        
        return DonationListResponseSchema(
            donations=donation_responses,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    @staticmethod
    def to_summary_response(entity: Any) -> Dict[str, Any]:
        """
        Convert donation entity to summary format (for lists, reports).
        """
        summary_fields = ['id', 'amount', 'donation_date', 'payment_method', 'status', 'user_name']
        
        data = {}
        for field in summary_fields:
            data[field] = getattr(entity, field, None)
        
        return data


class FundTypeResponseBuilder:
    """
    Builder for fund type response schemas.
    """

    @staticmethod
    def to_response(entity: Any) -> FundTypeResponseSchema:
        """
        Convert a fund type entity → FundTypeResponseSchema automatically.
        """
        schema_fields = FundTypeResponseSchema.model_fields.keys()
        
        data: Dict[str, Any] = {}
        for field in schema_fields:
            data[field] = getattr(entity, field, None)
        
        # Calculate progress percentage if target_amount is set
        if hasattr(entity, 'target_amount') and entity.target_amount and entity.target_amount > Decimal('0'):
            if hasattr(entity, 'current_balance'):
                progress_percentage = (entity.current_balance / entity.target_amount) * 100
                data['progress_percentage'] = round(float(progress_percentage), 2)
        
        return FundTypeResponseSchema(**data)

    @staticmethod
    def to_list_response(entities: List[Any], total: int = None, 
                        page: int = 1, per_page: int = 20) -> FundTypeListResponseSchema:
        """
        Convert a list of fund type entities to a paginated list response.
        """
        fund_type_responses = [FundTypeResponseBuilder.to_response(entity) for entity in entities]
        
        if total is None:
            total = len(entities)
            
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 1
        
        return FundTypeListResponseSchema(
            fund_types=fund_type_responses,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )