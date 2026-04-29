from django.contrib.auth.models import BaseUserManager
from apps.tcc.models.base.enums import UserRole, UserStatus

class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError('The email must be set')
        if not name:
            raise ValueError('The name must be set')
        
        email = self.normalize_email(email)
        
        # Set default values for required fields
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', UserRole.VISITOR)
        extra_fields.setdefault('status', UserStatus.PENDING)
        
        user = self.model(email=email, name=name, **extra_fields)
        
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
            
        try:
            user.save(using=self.db)
            return user
        except Exception as e:
            # This will help us see the actual database error
            print(f"Error saving user: {str(e)}")
            raise
    
    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', UserRole.SUPER_ADMIN)
        extra_fields.setdefault('status', UserStatus.ACTIVE)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True")
        
        return self.create_user(email, name, password, **extra_fields)