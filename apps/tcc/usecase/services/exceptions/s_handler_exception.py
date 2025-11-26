# from functools import wraps
# from typing import Dict, Any, Optional
# import logging
# from apps.tcc.usecase.domain_exception.s_exceptions import (
#     SermonAccessDeniedException, SermonAlreadyExistsException, InvalidInputException,
#     InvalidMediaTypeException, InvalidSermonInputException, SermonNotFoundException,
#     SermonPublishException, S
# )
# logger = logging.getLogger(__name__)

# class SermonExceptionHandler:
    
#     STATUS_CODES = {
#         SermonAlreadyExistsException:409,  # Conflict
#         SermonNotFoundException : 404,       # Not Found
#         InvalidInputException: 422,   # Unprocessable Entity
#         SermonAccessDeniedException: 401, # Unauthorized
#         Ser: 423,      # Locked
#         InsufficientPermissionsException: 403,  # Forbidden
#         EmailVerificationException: 400,  # Bad Request
#         PasswordValidationException: 422, # Unprocessable Entity
#         UserException: 400      
#     }