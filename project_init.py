#!/usr/bin/env python3
"""
TCC Project Initialization Script
One-click setup for development environment, dependencies, and project configuration
"""

import os
import sys
import subprocess
import platform
import venv
import shutil
from pathlib import Path
import importlib.util
import json

class ProjectInitializer:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.venv_path = self.project_root / "viro"
        self.requirements_file = self.project_root / "requirements/requirements.txt"
        self.is_windows = platform.system() == "Windows"
        self.python_executable = None
        
    def print_header(self):
        """Print initialization header"""
        print("=" * 60)
        print("🚀 TCC Project Initialization")
        print("=" * 60)
        
    def check_python_version(self):
        """Check if Python version is compatible"""
        print("🔍 Checking Python version...")
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print(f"❌ Python 3.8+ required. Current: {version.major}.{version.minor}.{version.micro}")
            return False
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
        return True
    
    def create_virtual_environment(self):
        """Create Python virtual environment"""
        print("\n🐍 Creating virtual environment...")
        
        if self.venv_path.exists():
            print("📁 Virtual environment already exists")
        else:
            try:
                venv.create(self.venv_path, with_pip=True)
                print("✅ Virtual environment created")
            except Exception as e:
                print(f"❌ Failed to create virtual environment: {e}")
                return False
        
        # Set Python executable path
        if self.is_windows:
            self.python_executable = self.venv_path / "Scripts" / "python.exe"
            self.pip_executable = self.venv_path / "Scripts" / "pip.exe"
        else:
            self.python_executable = self.venv_path / "bin" / "python"
            self.pip_executable = self.venv_path / "bin" / "pip"
            
        return True
    
    def install_dependencies(self):
        """Install project dependencies"""
        print("\n📦 Installing dependencies...")
        
        if not self.requirements_file.exists():
            print("❌ requirements.txt not found. Creating default...")
            self.create_default_requirements()
        
        try:
            # Upgrade pip first
            subprocess.run([
                str(self.python_executable), "-m", "pip", "install", "--upgrade", "pip"
            ], check=True, capture_output=True)
            
            # Install dependencies
            result = subprocess.run([
                str(self.python_executable), "-m", "pip", "install", "-r", str(self.requirements_file)
            ], check=True, capture_output=True, text=True)
            
            print("✅ Dependencies installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            if e.stderr:
                print(f"Error details: {e.stderr}")
            return False
    
    def create_default_requirements(self):
        """Create default requirements.txt if missing"""
        default_requirements = """Django>=4.2,<5.0
djangorestframework>=3.14
django-cors-headers>=4.0
psycopg2-binary>=2.9
Pillow>=10.0
python-decouple>=3.8
celery>=5.3
redis>=4.5
drf-yasg>=1.21
django-filter>=23.0
django-debug-toolbar>=4.0
django-extensions>=3.2
whitenoise>=6.4
gunicorn>=21.0
django-cleanup>=8.0
python-memcached>=1.59
django-redis>=5.2
"""
        with open(self.requirements_file, 'w') as f:
            f.write(default_requirements)
        print("📄 Created default requirements.txt")
    
    def setup_environment_variables(self):
        """Create environment configuration files"""
        print("\n⚙️  Setting up environment variables...")
        
        env_example = self.project_root / ".env.example"
        env_file = self.project_root / ".env"
        
        if not env_example.exists():
            self.create_env_example()
        
        if not env_file.exists():
            shutil.copy(env_example, env_file)
            print("✅ Created .env file from .env.example")
            print("⚠️  Please edit .env file with your actual configuration")
        else:
            print("📁 .env file already exists")
        
        return True
    
    def create_env_example(self):
        """Create .env.example file"""
        env_example_content = """# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,.localhost

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=tcc_db
DB_USER=tcc_user
DB_PASSWORD=tcc_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# Snowflake ID Generator
SNOWFLAKE_DATACENTER_ID=1
SNOWFLAKE_MACHINE_ID=1
SNOWFLAKE_EPOCH=1672531200000

# Security
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Email (Optional)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# File Storage
DEFAULT_FILE_STORAGE=django.core.files.storage.FileSystemStorage
MEDIA_ROOT=media
MEDIA_URL=/media/

# Logging
LOG_LEVEL=INFO
"""
        with open(self.project_root / ".env.example", 'w') as f:
            f.write(env_example_content)
        print("📄 Created .env.example file")
    
    def run_django_commands(self):
        """Run essential Django management commands"""
        print("\n🛠️  Running Django setup commands...")
        
        manage_py = self.project_root / "manage.py"
        if not manage_py.exists():
            print("❌ manage.py not found. Is this a Django project?")
            return False
        
        commands = [
            ["makemigrations"],
            ["migrate"],
            ["collectstatic", "--noinput"],
        ]
        
        for command in commands:
            try:
                print(f"🔧 Running: python manage.py {' '.join(command)}")
                result = subprocess.run([
                    str(self.python_executable), str(manage_py)
                ] + command, check=True, capture_output=True, text=True, cwd=self.project_root)
                print(f"✅ Command completed: {' '.join(command)}")
            except subprocess.CalledProcessError as e:
                print(f"⚠️  Command failed: {' '.join(command)} - {e}")
                if e.stderr:
                    print(f"Error: {e.stderr}")
        
        # Ask about creating superuser
        self.create_superuser()
        
        return True
    
    def create_superuser(self):
        """Create Django superuser interactively"""
        try:
            create = input("\n👤 Create Django superuser? (y/n): ").lower().strip()
            if create in ['y', 'yes']:
                print("Creating superuser...")
                subprocess.run([
                    str(self.python_executable), str(self.project_root / "manage.py"),
                    "createsuperuser"
                ], check=True, cwd=self.project_root)
        except (KeyboardInterrupt, subprocess.CalledProcessError):
            print("Superuser creation skipped or failed")
    
    def setup_pre_commit(self):
        """Set up pre-commit hooks if desired"""
        try:
            setup = input("\n🔧 Set up pre-commit hooks? (y/n): ").lower().strip()
            if setup in ['y', 'yes']:
                # Install pre-commit
                subprocess.run([
                    str(self.python_executable), "-m", "pip", "install", "pre-commit"
                ], check=True)
                
                # Set up hooks
                pre_commit_config = self.project_root / ".pre-commit-config.yaml"
                if not pre_commit_config.exists():
                    self.create_pre_commit_config()
                
                subprocess.run([
                    str(self.python_executable), "-m", "pre-commit", "install"
                ], check=True, cwd=self.project_root)
                print("✅ Pre-commit hooks installed")
        except (KeyboardInterrupt, subprocess.CalledProcessError):
            print("Pre-commit setup skipped")
    
    def create_pre_commit_config(self):
        """Create pre-commit configuration file"""
        pre_commit_content = """repos:
-   repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
    -   id: trailing-whitespace
    -   id: end-of-file-fixer
    -   id: check-yaml
    -   id: check-added-large-files
    -   id: check-merge-conflict

-   repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
    -   id: black
        args: [--line-length=88]

-   repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
    -   id: isort
        args: ["--profile", "black"]

-   repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
    -   id: flake8
        args: [--max-line-length=88, --extend-ignore=E203,W503]
"""
        with open(self.project_root / ".pre-commit-config.yaml", 'w') as f:
            f.write(pre_commit_content)
        print("📄 Created .pre-commit-config.yaml")
    
    def setup_ide_configuration(self):
        """Create IDE configuration files"""
        print("\n🔧 Setting up IDE configuration...")
        
        # VS Code settings
        vscode_dir = self.project_root / ".vscode"
        vscode_dir.mkdir(exist_ok=True)
        
        vscode_settings = {
            "python.defaultInterpreterPath": str(self.python_executable),
            "python.terminal.activateEnvironment": False,
            "editor.formatOnSave": True,
            "editor.codeActionsOnSave": {
                "source.organizeImports": True
            },
            "python.formatting.provider": "black",
            "python.linting.enabled": True,
            "python.linting.flake8Enabled": True,
            "[python]": {
                "editor.defaultFormatter": "ms-python.black-formatter"
            }
        }
        
        with open(vscode_dir / "settings.json", 'w') as f:
            json.dump(vscode_settings, f, indent=2)
        
        print("✅ VS Code configuration created")
    
    def print_success_message(self):
        """Print completion message with next steps"""
        print("\n" + "=" * 60)
        print("🎉 Project Initialization Complete!")
        print("=" * 60)
        print("\n📝 Next Steps:")
        print("1. Edit .env file with your actual configuration")
        print("2. Activate virtual environment:")
        if self.is_windows:
            print("   venv\\Scripts\\activate")
        else:
            print("   source venv/bin/activate")
        print("3. Run development server:")
        print("   python manage.py runserver")
        print("4. Access your application at http://localhost:8000")
        print("\n🛠️  Useful Commands:")
        print("   python manage.py makemigrations")
        print("   python manage.py migrate")
        print("   python manage.py createsuperuser")
        print("   python manage.py collectstatic")
        print("\n🐛 Debugging:")
        print("   python manage.py check")
        print("   python manage.py test")
        print("\n" + "=" * 60)
    
    def run(self):
        """Main initialization method"""
        self.print_header()
        
        # Check prerequisites
        if not self.check_python_version():
            sys.exit(1)
        
        # Setup steps
        steps = [
            self.create_virtual_environment,
            self.install_dependencies,
            self.setup_environment_variables,
            self.run_django_commands,
            self.setup_pre_commit,
            self.setup_ide_configuration,
        ]
        
        for step in steps:
            try:
                if not step():
                    print(f"❌ Step {step.__name__} failed")
                    if input("Continue anyway? (y/n): ").lower() != 'y':
                        sys.exit(1)
            except KeyboardInterrupt:
                print("\n❌ Initialization cancelled by user")
                sys.exit(1)
            except Exception as e:
                print(f"❌ Unexpected error in {step.__name__}: {e}")
                if input("Continue anyway? (y/n): ").lower() != 'y':
                    sys.exit(1)
        
        self.print_success_message()

def main():
    """Main entry point"""
    try:
        initializer = ProjectInitializer()
        initializer.run()
    except KeyboardInterrupt:
        print("\n❌ Initialization cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()