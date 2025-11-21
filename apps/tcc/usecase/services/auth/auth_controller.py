from apps.core.schemas.common.response import APIResponse
from apps.tcc.usecase.usecases.auth.login_uc import LoginUseCase


async def login(self, request):
    # Add request meta to context for audit logging
    ctx = {
        'request_meta': {
            'HTTP_X_FORWARDED_FOR': request.META.get('HTTP_X_FORWARDED_FOR'),
            'REMOTE_ADDR': request.META.get('REMOTE_ADDR'),
            'HTTP_USER_AGENT': request.META.get('HTTP_USER_AGENT'),
            'HTTP_REFERER': request.META.get('HTTP_REFERER'),
            'SERVER_NAME': request.META.get('SERVER_NAME'),
        }
    }
    
    result = await LoginUseCase().execute(request.data, ctx=ctx)
    return APIResponse.success_response(message="Login successful", data=result)