from functools import lru_cache
from apps.tcc.usecase.repo.domain_repo.sermons import SermonRepository
from apps.tcc.usecase.usecases.sermons.sermon_create import CreateSermonUseCase
from apps.tcc.usecase.usecases.sermons.sermon_read import (
    GetSermonByIdUseCase,
    GetAllSermonsUseCase,
    GetSermonsByPreacherUseCase,
    GetRecentSermonsUseCase,
    SearchSermonsUseCase,
    GetSermonsByYearUseCase,
    GetPublicSermonUseCase,
    GetSermonPreviewsUseCase
)
from apps.tcc.usecase.usecases.sermons.sermon_update import UpdateSermonUseCase, PublishSermonUseCase
from apps.tcc.usecase.usecases.sermons.sermon_delete import DeleteSermonUseCase

@lru_cache()
def get_sermon_repository() -> SermonRepository:
    return SermonRepository()

# Create use case instances
def get_create_sermon_uc() -> CreateSermonUseCase:
    return CreateSermonUseCase(get_sermon_repository())

def get_sermon_by_id_uc() -> GetSermonByIdUseCase:
    return GetSermonByIdUseCase(get_sermon_repository())

def get_all_sermons_uc() -> GetAllSermonsUseCase:
    return GetAllSermonsUseCase(get_sermon_repository())

def get_sermons_by_preacher_uc() -> GetSermonsByPreacherUseCase:
    return GetSermonsByPreacherUseCase(get_sermon_repository())

def get_recent_sermons_uc() -> GetRecentSermonsUseCase:
    return GetRecentSermonsUseCase(get_sermon_repository())

def search_sermons_uc() -> SearchSermonsUseCase:
    return SearchSermonsUseCase(get_sermon_repository())

def get_sermons_by_year_uc() -> GetSermonsByYearUseCase:
    return GetSermonsByYearUseCase(get_sermon_repository())

def get_public_sermon_uc() -> GetPublicSermonUseCase:
    return GetPublicSermonUseCase(get_sermon_repository())

def get_sermon_previews_uc() -> GetSermonPreviewsUseCase:
    return GetSermonPreviewsUseCase(get_sermon_repository())

def get_update_sermon_uc() -> UpdateSermonUseCase:
    return UpdateSermonUseCase(get_sermon_repository())

def get_publish_sermon_uc() -> PublishSermonUseCase:
    return PublishSermonUseCase(get_sermon_repository())

def get_delete_sermon_uc() -> DeleteSermonUseCase:
    return DeleteSermonUseCase(get_sermon_repository())