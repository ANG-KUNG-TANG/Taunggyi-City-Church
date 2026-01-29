"""Model registry to manage imports and avoid circular dependencies"""
import sys


class ModelRegistry:
    """Registry for lazy model loading"""
    
    _models = {}
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """Initialize all models - call this once at startup"""
        if cls._initialized:
            return
        
        # Import models in a safe order
        from apps.tcc.models.base.base_model import BaseModel
        
        # Delay user model import
        cls._initialized = True
    
    @classmethod
    def get_model(cls, model_name):
        """Get a model by name"""
        if model_name not in cls._models:
            cls._load_model(model_name)
        return cls._models.get(model_name)
    
    @classmethod
    def _load_model(cls, model_name):
        """Load a specific model"""
        if model_name == 'User':
            from apps.tcc.models.users.users import User
            cls._models['User'] = User
        elif model_name == 'Event':
            from apps.tcc.models.events.events import Event
            cls._models['Event'] = Event
        elif model_name == 'Donation':
            from apps.tcc.models.donations.donation import Donation
            cls._models['Donation'] = Donation
        elif model_name == 'Prayer':
            from apps.tcc.models.prayers.prayer import Prayer
            cls._models['Prayer'] = Prayer
        elif model_name == 'PrayerResponse':
            from apps.tcc.models.prayers.prayer import PrayerResponse
            cls._models['PrayerResponse'] = PrayerResponse
        elif model_name == 'Sermon':
            from apps.tcc.models.sermons.sermons import Sermon
            cls._models['Sermon'] = Sermon
        # Add other models as needed
    
    @classmethod
    def get_all_models(cls):
        """Get all registered models"""
        return list(cls._models.values())


# Convenience functions
def get_user_model():
    """Get the User model without circular import issues"""
    return ModelRegistry.get_model('User')


def get_event_model():
    """Get the Event model"""
    return ModelRegistry.get_model('Event')


# Initialize the registry when module is imported
ModelRegistry.initialize()