# debug_user_create.py
import asyncio
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

async def debug_create_user():
    """Debug user creation directly"""
    from apps.tcc.usecase.services.users.user_controller import create_user_controller
    from apps.core.schemas.input_schemas.users import UserCreateInputSchema
    
    print("Starting user creation debug...")
    
    try:
        # Create controller
        controller = await create_user_controller()
        print("✓ Controller created")
        
        # Test data
        test_data = {
            'name': 'Debug User',
            'email': 'debug@example.com',
            'password': 'Debug123!@#',
            'password_confirm': 'Debug123!@#',
            'gender': 'male',
            'date_of_birth': '1990-01-01',
            'role': 'member',
            'status': 'pending',
            'is_active': True,
            'email_notifications': True
        }
        
        # Create input schema
        user_schema = UserCreateInputSchema(**test_data)
        print("✓ Input schema created")
        
        # Try to create user
        print("Attempting to create user...")
        user_entity = await controller.create_user(
            user_data=user_schema,
            current_user=None,
            context={}
        )
        
        print(f"✓ User created successfully!")
        print(f"  ID: {user_entity.id}")
        print(f"  Email: {user_entity.email}")
        print(f"  Name: {user_entity.name}")
        
    except Exception as e:
        print(f"✗ Error creating user: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_create_user())