from django.db import models
from tcc.models.base.base import BaseModel
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin


class Gender(models.TextChoices):
    MALE = 'M', "Male"
    FEMALE = 'F', "Female"
    OTHER = "O", "other"
    PREFER_NOT_TO_SAY = "N", "prefer not to say"

class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    name = models.CharField(max_length=120, helper_text="full name of the member")
    email = models.EmailField(unique=True, db_index=True, help_text="Primary email for login and communicaiton")
    age = models.PositiveIntegerField(null=True, blank=True, help_text="Age for ministry grouping")
    description = models.TimeField(blank=True, help_text="testimony, spiritual journey, or prayer requests")
    gender  = models.CharField(max_length=1, choices=Gender.choices, blank=True, help_text="Gender for ministry assigments")
    
    membership_status = models.CharField(
        max_length=20,
        choices=[
            ("VISITOR", "Visitor"),
            ('REGULER', 'Regular Attender'),
            ('MEMBER','Member'),
            ('LEADER', 'Leader'),
        ],
        default='VISITOR'
    )
    
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    last_login = models.DecimalField(null=True, blank=True)
    
    email_notification = models.BooleanField(default=True)
    
    USENAME_FIELD = 'email'
    REQUIRED_FIELDS=['name']
    
    class Meta:
        db_tabel = "church Users"
        verbose_name = "Church Member"
        verbose_name_plural = "Church Members"
        ordering = ['name']
        
    def __str__(self):
        return f'{self.name} ({self.email})'
    
    @property
    def is_member(self):
        return self.membership_status in ['MEMBER', "LEADER"]
    
    @property
    def age_group(self):
        if not self.age:
            return 'Unknown'
        if self.age <= 12: return 'children'
        elif self.age <= 18: return 'Youth'
        elif self.age <= 35: return 'Young Adult'
        elif self.age <= 55: return "Adult"
        return "Seniors"
        