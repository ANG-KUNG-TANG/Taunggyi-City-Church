from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response  
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from apps.tcc.usecase.services.users.user_controller import create_user_controller_with_di
from .base_view import BaseView


class UserCreateView(BaseView, APIView):
    """Create new user - public endpoint"""
    authentication_classes = []
    permission_classes = []

    async def post(self, request: Request) -> Response: 
        # Use DI-based controller factory
        controller = create_user_controller_with_di()
        result = await controller.create_user(request.data, self.build_context(request))
        return self.create_response(result, "POST")


class UserProfileView(BaseView, APIView):
    """Current user profile operations"""
    permission_classes = [IsAuthenticated]

    async def get(self, request: Request) -> Response:  
        controller = create_user_controller_with_di()
        result = await controller.get_current_user_profile(request.user, self.build_context(request))
        return self.create_response(result, "GET")

    async def put(self, request: Request) -> Response:  
        controller = create_user_controller_with_di()
        result = await controller.update_current_user_profile(request.data, request.user, self.build_context(request))
        return self.create_response(result, "PUT")


class UserDetailView(BaseView, APIView):
    """Specific user operations (by ID)"""
    permission_classes = [IsAuthenticated]

    async def get(self, request: Request, user_id: str) -> Response:  
        controller = create_user_controller_with_di()
        result = await controller.get_user_by_id(user_id, request.user, self.build_context(request))
        return self.create_response(result, "GET")

    async def put(self, request: Request, user_id: str) -> Response: 
        controller = create_user_controller_with_di()
        result = await controller.update_user(user_id, request.data, request.user, self.build_context(request))
        return self.create_response(result, "PUT")

    async def delete(self, request: Request, user_id: str) -> Response: 
        controller = create_user_controller_with_di()
        result = await controller.delete_user(user_id, request.user, self.build_context(request))
        return self.create_response(result, "DELETE")


class UserListView(BaseView, APIView):
    """User listing and search operations"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    async def get(self, request: Request) -> Response: 
        controller = create_user_controller_with_di()
        page, per_page = self.get_pagination_params(request)
        
        if search_term := request.query_params.get('search'):
            result = await controller.search_users(search_term, page, per_page, request.user, self.build_context(request))
        elif role := request.query_params.get('role'):
            result = await controller.get_users_by_role(role, page, per_page, request.user, self.build_context(request))
        else:
            filters = self.extract_filters(request)
            result = await controller.get_all_users(filters, page, per_page, request.user, self.build_context(request))
        
        return self.create_response(result, "GET")


class UserAdminView(BaseView, APIView):
    """Admin-only user management operations"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    async def patch(self, request: Request, user_id: str) -> Response: 
        controller = create_user_controller_with_di()
        result = await controller.change_user_status(user_id, request.data.get('status'), request.user, self.build_context(request))
        return self.create_response(result, "PATCH")


class UserBulkView(BaseView, APIView):
    """Bulk user operations"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    async def patch(self, request: Request) -> Response: 
        controller = create_user_controller_with_di()
        result = await controller.bulk_change_status(
            request.data.get('user_ids', []), 
            request.data.get('status'), 
            request.user, 
            self.build_context(request)
        )
        return self.create_response(result, "PATCH")


class UserByEmailView(BaseView, APIView):
    """User lookup by email"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    async def get(self, request: Request) -> Response: 
        controller = create_user_controller_with_di()
        result = await controller.get_user_by_email(request.query_params.get('email'), request.user, self.build_context(request))
        return self.create_response(result, "GET")