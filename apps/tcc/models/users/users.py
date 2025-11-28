from datetime import date
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from apps.tcc.models.base.base_model import BaseModel
from apps.tcc.models.users.user_manager import UserManager  
from apps.tcc.models.base.enums import UserRole, UserStatus, Gender, MaritalStatus

class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    # Personal Information
    name = models.CharField(max_length=120, help_text="Full name of the member")
    email = models.EmailField(unique=True, db_index=True, help_text="Primary email for login and communication")
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    gender = models.CharField(max_length=20, choices=Gender.choices, blank=True)
    marital_status = models.CharField(max_length=20, choices=MaritalStatus.choices, blank=True)
    date_of_birth = models.DateField(null=True, blank=True, help_text="The user's date of birth")
    
    # Spiritual Information
    testimony = models.TextField(blank=True, help_text="Personal testimony or spiritual journey")
    baptism_date = models.DateField(null=True, blank=True)
    membership_date = models.DateField(null=True, blank=True)
    
    # Role & Status
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.VISITOR)
    status = models.CharField(max_length=20, choices=UserStatus.choices, default=UserStatus.PENDING)
    
    # System Fields
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    
    objects = UserManager()
    # Authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']
    
    class Meta:
        db_table = 'users'
        verbose_name = ('User')
        verbose_name_plural = ('Users')
        ordering = ['name']
    
    def __str__(self):
        return f'{self.name} ({self.email})'
    
    # Role-based permission properties
    @property
    def is_super_admin(self):
        return self.role == UserRole.SUPER_ADMIN
    
    @property
    def is_staff_member(self):
        return self.role == UserRole.STAFF
    
    @property
    def is_ministry_leader(self):
        return self.role == UserRole.MINISTRY_LEADER
    
    @property
    def is_member(self):
        return self.role == UserRole.MEMBER
    
    @property
    def is_visitor(self):
        return self.role == UserRole.VISITOR
    
    @property
    def can_manage_users(self):
        """Who can manage users"""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF]
    
    @property
    def can_manage_events(self):
        """Who can create and manage events"""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF, UserRole.MINISTRY_LEADER]
    
    @property
    def can_manage_sermons(self):
        """Who can manage sermons"""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF, UserRole.MINISTRY_LEADER]
    
    @property
    def can_manage_donations(self):
        """Who can manage donations"""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF]
    
    @property
    def can_view_all_prayers(self):
        """Who can view all prayer requests"""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF, UserRole.MINISTRY_LEADER]
    
    @property
    def can_join_events(self):
        """Who can join events"""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF, UserRole.MINISTRY_LEADER, UserRole.MEMBER, UserRole.VISITOR]
    
    @property
    def can_create_prayers(self):
        """Who can create prayer requests"""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF, UserRole.MINISTRY_LEADER, UserRole.MEMBER, UserRole.VISITOR]
    
    def get_permissions(self):
        """Get all permissions for this user role"""
        return {
            'manage_users': self.can_manage_users,
            'manage_events': self.can_manage_events,
            'manage_sermons': self.can_manage_sermons,
            'manage_donations': self.can_manage_donations,
            'view_all_prayers': self.can_view_all_prayers,
            'join_events': self.can_join_events,
            'create_prayers': self.can_create_prayers,
        }
    @property
    def age_in_years(self):
        """Calculates the age in years based on the date_of_birth."""
        if self.date_of_birth:
            today = date.today()
            # Calculate the difference in years
            age = today.year - self.date_of_birth.year
            # Subtract 1 if the birthday hasn't occurred yet this year
            if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
                age -= 1
            return age
        return None # Return None if date_of_birth is not set