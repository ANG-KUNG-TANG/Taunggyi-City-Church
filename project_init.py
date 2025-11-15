"""
TCC Project Auto Initialization Script
Fully automatic: creates venv with Python 3.12, installs deps, prepares environment, and runs Django setup.
"""

import os, sys, subprocess, platform, shutil, json
from pathlib import Path

class ProjectInitializer:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.venv_path = self.project_root / "viro"
        self.requirements_file = self.project_root / "requirements.txt"
        self.is_windows = platform.system() == "Windows"
        self.python_executable = None
        self.pip_executable = None
        self.python_12 = None

    # ----------------------------------------------------------
    def print_header(self):
        print("=" * 60)
        print("🚀  TCC Project Auto Initialization (Python 3.12)")
        print("=" * 60)

    # ----------------------------------------------------------
    def find_python_312(self):
        """Find Python 3.12 executable with better Windows support"""
        print("🔍 Looking for Python 3.12...")
        
        # Common Python 3.12 locations on Windows
        possible_paths = [
            # User might have installed Python 3.12 in different locations
            "python3.12", "python312", 
            "py -3.12", "py -3.12-32", "py -3.12-64",
            # Common installation paths
            "C:\\Python312\\python.exe",
            "C:\\Program Files\\Python312\\python.exe", 
            "C:\\Users\\" + os.getenv('USERNAME') + "\\AppData\\Local\\Programs\\Python\\Python312\\python.exe",
            # Environment variables
            os.getenv('PYTHON312_PATH', ''),
            # Check if Python 3.12 is available via python command
            "python"
        ]
        
        for path_cmd in possible_paths:
            if not path_cmd.strip():
                continue
                
            try:
                if path_cmd.startswith("py "):
                    # Handle Windows py launcher
                    cmd = path_cmd.split() + ["--version"]
                else:
                    cmd = [path_cmd, "--version"]
                    
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and "3.12" in result.stdout:
                    print(f"✅ Found Python 3.12: {path_cmd}")
                    return path_cmd
            except (FileNotFoundError, subprocess.SubprocessError, subprocess.TimeoutExpired):
                continue
        
        # Last resort: check current Python version
        current_version = sys.version_info
        if current_version.major == 3 and current_version.minor == 12:
            print("✅ Using current Python 3.12")
            return sys.executable
        
        print("\n❌ Python 3.12 not found automatically.")
        print("\n🔧 Please install Python 3.12 from:")
        print("   https://www.python.org/downloads/release/python-3120/")
        print("\n📋 Or try one of these solutions:")
        print("   1. Install Python 3.12 using the Windows installer")
        print("   2. Use the Python launcher: 'py -3.12' should work after installation")
        print("   3. Add Python 3.12 to your PATH during installation")
        
        # Ask user for manual path
        manual_path = input("\n📁 Or enter the full path to Python 3.12 executable (or press Enter to exit): ").strip()
        if manual_path and os.path.exists(manual_path):
            return manual_path
        else:
            sys.exit(1)

    # ----------------------------------------------------------
    def check_python_version(self):
        print("🔍 Checking Python version...")
        self.python_12 = self.find_python_312()
        
        # Verify it's actually 3.12 with better error handling
        try:
            if self.python_12.startswith("py "):
                cmd = self.python_12.split() + ["--version"]
            else:
                cmd = [self.python_12, "--version"]
                
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True)
            version_output = result.stdout.strip()
            print(f"✅ Using: {version_output}")
            
            if "3.12" not in version_output:
                print(f"❌ Expected Python 3.12 but got: {version_output}")
                sys.exit(1)
                
        except Exception as e:
            print(f"❌ Failed to verify Python 3.12: {e}")
            print(f"   Command tried: {cmd}")
            sys.exit(1)

    # ----------------------------------------------------------
    def recreate_virtual_environment(self):
        """Always recreate a fresh virtual environment with Python 3.12"""
        if self.venv_path.exists():
            print("🧹 Removing existing virtual environment...")
            try:
                shutil.rmtree(self.venv_path)
            except Exception as e:
                print(f"❌ Failed to remove old environment: {e}")
                sys.exit(1)

        print("🐍 Creating new virtual environment with Python 3.12...")
        try:
            # Use the found Python 3.12 to create venv
            if self.python_12.startswith("py "):
                # Handle py launcher on Windows
                cmd = self.python_12.split() + ["-m", "venv", str(self.venv_path)]
            else:
                cmd = [self.python_12, "-m", "venv", str(self.venv_path)]
                
            print(f"   Running: {' '.join(cmd)}")
            subprocess.run(cmd, check=True, timeout=60)
        except Exception as e:
            print(f"❌ Could not create venv with Python 3.12: {e}")
            print("💡 Try installing Python 3.12 manually and ensure it's in PATH")
            sys.exit(1)

        if self.is_windows:
            self.python_executable = self.venv_path / "Scripts" / "python.exe"
            self.pip_executable = self.venv_path / "Scripts" / "pip.exe"
        else:
            self.python_executable = self.venv_path / "bin" / "python"
            self.pip_executable = self.venv_path / "bin" / "pip"
        
        # Verify the venv was created successfully
        if not self.python_executable.exists():
            print(f"❌ Virtual environment creation failed: {self.python_executable} not found")
            sys.exit(1)
            
        print(f"✅ Virtual environment ready: {self.python_executable}")

    # ----------------------------------------------------------
    def install_dependencies(self):
        print("📦 Installing dependencies...")
        if not self.requirements_file.exists():
            self.requirements_file.parent.mkdir(exist_ok=True)
            self.create_compatible_requirements()

        try:
            # Upgrade pip first
            subprocess.run([str(self.python_executable), "-m", "pip", "install", "--upgrade", "pip"], 
                         check=True, timeout=120)
            
            # Install requirements
            subprocess.run([str(self.python_executable), "-m", "pip", "install", "-r", str(self.requirements_file)], 
                         check=True, timeout=300)
            print("✅ Dependencies installed successfully.")
        except subprocess.TimeoutExpired:
            print("❌ Dependency installation timed out. Try running again.")
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            sys.exit(1)

    # ----------------------------------------------------------
    def create_compatible_requirements(self):
        """Create requirements compatible with Python 3.12"""
        compatible_reqs = """Django>=4.2,<5.0
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

# JWT packages compatible with Python 3.12
djangorestframework-simplejwt>=5.2.0
PyJWT>=2.8.0

# Database
psycopg2-binary>=2.9.6

# Development tools
black>=23.0
flake8>=6.0
"""
        with open(self.requirements_file, "w") as f:
            f.write(compatible_reqs)
        print("📄 Created Python 3.12 compatible requirements.txt")

    # ----------------------------------------------------------
    def fix_jwt_compatibility(self):
        """Apply workaround for JWT package compatibility issues"""
        print("🔧 Checking for JWT compatibility fixes...")
        
        # This is now less critical since we're using Python 3.12
        jwt_init_file = self.venv_path / "Lib" / "site-packages" / "rest_framework_simplejwt" / "__init__.py"
        
        if jwt_init_file.exists():
            try:
                # Only fix if there's an importlib issue
                with open(jwt_init_file, 'r') as f:
                    content = f.read()
                    
                if "importlib" in content and "version" in content:
                    # Backup original file
                    backup_file = jwt_init_file.with_suffix('.py.backup')
                    if not backup_file.exists():
                        shutil.copy2(jwt_init_file, backup_file)
                    
                    # Replace with fixed version
                    fixed_content = '''__version__ = "5.3.0"  # Manual version

default_app_config = 'rest_framework_simplejwt.apps.SimpleJwtConfig'
'''
                    with open(jwt_init_file, 'w') as f:
                        f.write(fixed_content)
                    print("✅ Applied JWT compatibility fix")
                else:
                    print("✅ JWT package already compatible")
            except Exception as e:
                print(f"⚠️  Could not check JWT package (non-critical): {e}")
        else:
            print("ℹ️  JWT package not installed yet")

    # ----------------------------------------------------------
    def setup_env_files(self):
        print("⚙️  Setting up .env files...")
        env_example = self.project_root / ".env.example"
        env_file = self.project_root / ".env"

        if not env_example.exists():
            with open(env_example, "w") as f:
                f.write("""DEBUG=True
SECRET_KEY=your-secret-key-here-make-it-very-long-and-secure
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
DATABASE_URL=sqlite:///db.sqlite3
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
""")
            print("📄 Created .env.example")

        if not env_file.exists():
            shutil.copy(env_example, env_file)
            print("✅ Created .env from template")
        else:
            print("📁 .env already exists")

    # ----------------------------------------------------------
    def run_django_setup(self):
        print("🛠️  Running Django setup...")
        manage_py = self.project_root / "manage.py"
        if not manage_py.exists():
            print("❌ manage.py not found — please ensure you're in a Django project root.")
            sys.exit(1)

        commands = [
            ["makemigrations"],
            ["migrate"],
            ["collectstatic", "--noinput"],
        ]
        
        for cmd in commands:
            try:
                print(f"   Running: python manage.py {cmd[0]}")
                subprocess.run([str(self.python_executable), str(manage_py)] + cmd, check=True, timeout=60)
                print(f"✅ Django {cmd[0]} completed")
            except subprocess.CalledProcessError as e:
                print(f"⚠️  Django {cmd[0]} failed: {e}")
                if "auth" in str(e).lower() or "user" in str(e).lower():
                    print("💡 Tip: You may need to check your custom user model configuration")
            except subprocess.TimeoutExpired:
                print(f"⚠️  Django {cmd[0]} timed out")
        
        print("✅ Django setup completed.")

    # ----------------------------------------------------------
    def setup_vscode(self):
        print("🧩 Setting up VS Code configuration...")
        vscode_dir = self.project_root / ".vscode"
        vscode_dir.mkdir(exist_ok=True)
        
        settings = {
            "python.defaultInterpreterPath": str(self.python_executable),
            "editor.formatOnSave": True,
            "python.formatting.provider": "black",
            "python.terminal.activateEnvironment": False
        }
        
        with open(vscode_dir / "settings.json", "w") as f:
            json.dump(settings, f, indent=2)
        
        # Create launch.json for debugging
        launch_config = {
            "version": "0.2.0",
            "configurations": [
                {
                    "name": "Django Debug",
                    "type": "python",
                    "request": "launch",
                    "program": "${workspaceFolder}/manage.py",
                    "args": ["runserver"],
                    "django": True,
                    "justMyCode": True
                }
            ]
        }
        
        with open(vscode_dir / "launch.json", "w") as f:
            json.dump(launch_config, f, indent=2)
            
        print("✅ VS Code configured for Python 3.12")

    # ----------------------------------------------------------
    def verify_installation(self):
        """Verify that everything is working correctly"""
        print("🔍 Verifying installation...")
        
        try:
            # Test Python version in venv
            result = subprocess.run(
                [str(self.python_executable), "--version"], 
                capture_output=True, text=True, check=True, timeout=10
            )
            print(f"✅ {result.stdout.strip()}")
            
            # Test Django
            result = subprocess.run(
                [str(self.python_executable), "manage.py", "check"], 
                capture_output=True, text=True, check=True, timeout=30
            )
            print("✅ Django check passed")
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Verification issue: {e}")
            return False
        except subprocess.TimeoutExpired:
            print("⚠️  Verification timed out")
            return False
            
        return True

    # ----------------------------------------------------------
    def run(self):
        self.print_header()
        self.check_python_version()
        self.recreate_virtual_environment()
        self.install_dependencies()
        self.fix_jwt_compatibility()
        self.setup_env_files()
        self.run_django_setup()
        self.setup_vscode()
        self.verify_installation()
        
        print("\n🎉 All set! Project initialized with Python 3.12")
        print("\n🚀 To start your project:")
        if self.is_windows:
            print("   viro\\Scripts\\activate")
            print("   python manage.py runserver")
        else:
            print("   source viro/bin/activate")
            print("   python manage.py runserver")
        
        print("\n📝 Next steps:")
        print("   1. Configure your database in .env file")
        print("   2. Create a superuser: python manage.py createsuperuser")
        print("   3. Start developing!")
        print("\n✅ Initialization complete.")

# --------------------------------------------------------------
def main():
    try:
        ProjectInitializer().run()
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()