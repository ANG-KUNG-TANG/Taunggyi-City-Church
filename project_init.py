"""
TCC Project Initialization Script
Reuses or creates a virtual environment, verifies dependencies, prepares
environment files and VS Code settings, checks Django configuration,
and optionally collects static files. Database migrations are currently
performed automatically during Django setup.
"""

import os, sys, subprocess, platform, shutil, json
from pathlib import Path

class ProjectInitializer:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.venv_path = self.project_root / "backend" / ".venv"
        self.requirements_file = self.project_root / "backend" / "requirements.txt"
        self.is_windows = platform.system() == "Windows"
        self.python_executable = None
        self.pip_executable = None
        self.python_12 = None

    # ----------------------------------------------------------
    def print_header(self):
        print("=" * 60)
        print("🚀  TCC Project Auto Initialization")
        print("=" * 60)


    # ----------------------------------------------------------
    def find_python_312(self):
        """Use the Python interpreter running this initializer."""
        return sys.executable

    # ----------------------------------------------------------
    def check_python_version(self):
        """Check the current Python interpreter without requiring 3.12."""
        print("🔍 Checking Python version...")

        self.python_12 = self.find_python_312()

        try:
            result = subprocess.run(
                [
                    self.python_12,
                    "-c",
                    "import sys; print(sys.version)",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )

            version_output = result.stdout.strip()
            print(f"✅ Using Python: {version_output}")

        except (subprocess.SubprocessError, OSError) as e:
            print(f"❌ Failed to verify Python: {e}")
            sys.exit(1)



    # ----------------------------------------------------------
    def recreate_virtual_environment(self):
        """Reuse the existing venv or create one without deleting anything."""

        if self.is_windows:
            python_path = self.venv_path / "Scripts" / "python.exe"
            pip_path = self.venv_path / "Scripts" / "pip.exe"
        else:
            python_path = self.venv_path / "bin" / "python"
            pip_path = self.venv_path / "bin" / "pip"

        # Reuse the existing environment if its Python executable exists.
        if python_path.exists():
            self.python_executable = python_path
            self.pip_executable = pip_path

            print(f"♻️ Reusing existing virtual environment: {python_path}")
            return

        # Never delete an existing directory automatically.
        if self.venv_path.exists():
            print(
                "❌ The virtual environment directory exists, "
                "but its Python executable was not found."
            )
            print(f"   Directory: {self.venv_path}")
            print("   Please inspect it before making any changes.")
            sys.exit(1)

        print("🐍 Creating a new virtual environment...")

        try:
            subprocess.run(
                [
                    self.python_12,
                    "-m",
                    "venv",
                    str(self.venv_path),
                ],
                check=True,
                timeout=120,
            )

        except (subprocess.SubprocessError, OSError) as e:
            print(f"❌ Could not create virtual environment: {e}")
            sys.exit(1)

        if not python_path.exists():
            print(
                f"❌ Virtual environment creation failed: "
                f"{python_path} not found"
            )
            sys.exit(1)

        self.python_executable = python_path
        self.pip_executable = pip_path

        print(f"✅ Virtual environment ready: {python_path}")



    def verify_dependencies(self):
        """Verify pinned dependencies without modifying the environment."""
        print("📦 Verifying dependencies...")

        if not self.requirements_file.exists():
            print(f"❌ Requirements file not found: {self.requirements_file}")
            return False

        try:
            from importlib.metadata import PackageNotFoundError, version
            from packaging.requirements import Requirement

            missing = []
            mismatched = []

            with self.requirements_file.open(
                "r", encoding="utf-8"
            ) as requirements:
                for line_number, line in enumerate(requirements, start=1):
                    line = line.strip()

                    if not line or line.startswith("#"):
                        continue

                    try:
                        requirement = Requirement(line)
                    except Exception as error:
                        print(
                            f"❌ Invalid requirement at line "
                            f"{line_number}: {line}"
                        )
                        print(f"   {error}")
                        return False

                    try:
                        installed_version = version(requirement.name)
                    except PackageNotFoundError:
                        missing.append(requirement.name)
                        continue

                    if not requirement.specifier.contains(
                        installed_version,
                        prereleases=True,
                    ):
                        mismatched.append(
                            f"{requirement.name}: "
                            f"required {requirement.specifier}, "
                            f"installed {installed_version}"
                        )

            if missing:
                print("❌ Missing packages:")
                for package in missing:
                    print(f"   - {package}")

            if mismatched:
                print("❌ Version mismatches:")
                for package in mismatched:
                    print(f"   - {package}")

            if missing or mismatched:
                print("❌ Requirements verification failed.")
                print("ℹ️  No packages were installed or upgraded.")
                return False

            subprocess.run(
                [
                    str(self.python_executable),
                    "-m",
                    "pip",
                    "check",
                ],
                check=True,
                timeout=60,
            )

            print("✅ All requirements are installed at compatible versions.")
            print("✅ Installed packages have no dependency conflicts.")
            print("ℹ️  No packages were installed or upgraded.")

            return True

        except subprocess.CalledProcessError as error:
            print(f"❌ Dependency conflict check failed: {error}")
            return False

        except subprocess.TimeoutExpired:
            print("❌ Dependency verification timed out.")
            return False

        except Exception as error:
            print(f"❌ Dependency verification failed: {error}")
            return False

    # ----------------------------------------------------------
    def setup_env_files(self):
        """Prepare backend environment files without overwriting secrets."""
        print("⚙️  Setting up backend .env files...")

        backend_dir = self.project_root / "backend"
        env_example = backend_dir / ".env.example"
        env_file = backend_dir / ".env"

        if not backend_dir.exists():


            print(f"❌ Backend directory not found: {backend_dir}")
            sys.exit(1)

        # Create a template only if it does not already exist.
        if not env_example.exists():
            env_example.write_text(
                """DEBUG=True
SECRET_KEY=replace-with-a-secure-secret-key
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=5432
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
""",
                encoding="utf-8",
            )
            print("📄 Created backend/.env.example")
        else:
            print("📄 backend/.env.example already exists")

        # Never overwrite an existing environment file.
        if not env_file.exists():
            shutil.copy2(env_example, env_file)
            print("✅ Created backend/.env from template")
            print("⚠️  Update backend/.env with your actual configuration.")
        else:
            print("🔒 backend/.env already exists. Keeping it unchanged.")

    def run_django_setup(self):
        """Run Django migrations and optionally collect static files."""
        print("🛠️  Running Django setup...")

        backend_dir = self.project_root / "backend"
        manage_py = backend_dir / "manage.py"

        if not manage_py.exists():
            print(f"❌ Django manage.py not found: {manage_py}")
            sys.exit(1)

        # Validate Django configuration before making changes.
        try:
            subprocess.run(
                [
                    str(self.python_executable),
                    str(manage_py),
                    "check",
                ],
                cwd=str(backend_dir),
                check=True,
                timeout=30,
            )
        except subprocess.CalledProcessError as e:
            print(f"❌ Django configuration check failed: {e}")
            sys.exit(1)
        except subprocess.TimeoutExpired:
            print("❌ Django configuration check timed out.")
            sys.exit(1)


        # Database migrations are performed automatically.
        commands = [
            ["migrate", "--noinput"],
        ]

        for cmd in commands:
            try:
                print(f"   Running: python manage.py {' '.join(cmd)}")

                subprocess.run(
                    [
                        str(self.python_executable),
                        str(manage_py),
                        *cmd,
                    ],
                    cwd=str(backend_dir),
                    check=True,
                    timeout=120,
                )

                print(f"✅ Django {cmd[0]} completed")

            except subprocess.CalledProcessError as e:
                print(f"❌ Django {cmd[0]} failed: {e}")
                sys.exit(1)

            except subprocess.TimeoutExpired:
                print(f"❌ Django {cmd[0]} timed out.")
                sys.exit(1)

        # Static collection requires explicit confirmation.
        if sys.stdin.isatty():
            answer = input(
                "\nDo you want to collect static files now? [y/N]: "
            ).strip().lower()

            if answer in ("y", "yes"):
                try:
                    subprocess.run(
                        [
                            str(self.python_executable),
                            str(manage_py),
                            "collectstatic",
                            "--noinput",
                        ],
                        cwd=str(backend_dir),
                        check=True,
                        timeout=120,
                    )

                    print("✅ Django collectstatic completed")

                except subprocess.CalledProcessError as e:
                    print(f"❌ Django collectstatic failed: {e}")
                    sys.exit(1)

                except subprocess.TimeoutExpired:
                    print("❌ Django collectstatic timed out.")
                    sys.exit(1)

            else:
                print("ℹ️  Static collection skipped.")

        else:
            print("ℹ️  Non-interactive environment detected.")
            print("   Static collection skipped.")

        print("✅ Django setup completed.")



    def setup_vscode(self):
        """Create VS Code configuration only when files are missing."""
        print("🧩 Setting up VS Code configuration...")

        vscode_dir = self.project_root / ".vscode"
        vscode_dir.mkdir(exist_ok=True)

        settings_file = vscode_dir / "settings.json"
        launch_file = vscode_dir / "launch.json"

        settings = {
            "python.defaultInterpreterPath": str(self.python_executable),
            "editor.formatOnSave": True,
            "python.formatting.provider": "black",
            "python.terminal.activateEnvironment": False,
        }

        launch_config = {
            "version": "0.2.0",
            "configurations": [
                {
                    "name": "Django Debug",
                    "type": "debugpy",
                    "request": "launch",
                    "program": "${workspaceFolder}/backend/manage.py",
                    "args": ["runserver"],
                    "cwd": "${workspaceFolder}/backend",
                    "django": True,
                    "justMyCode": True,
                }
            ],
        }

        if settings_file.exists():
            print("ℹ️  Existing settings.json preserved.")
        else:
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
            print("✅ Created settings.json")

        if launch_file.exists():
            print("ℹ️  Existing launch.json preserved.")
        else:
            with open(launch_file, "w", encoding="utf-8") as f:
                json.dump(launch_config, f, indent=2)
            print("✅ Created launch.json")

        print("✅ VS Code configuration checked.")


    def verify_installation(self):
        """Verify that the backend Django installation is working."""
        print("🔍 Verifying installation...")

        backend_dir = self.project_root / "backend"
        manage_py = backend_dir / "manage.py"

        try:
            result = subprocess.run(
                [str(self.python_executable), "--version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )

            print(f"✅ {result.stdout.strip()}")

            result = subprocess.run(
                [
                    str(self.python_executable),
                    str(manage_py),
                    "check",
                ],
                cwd=str(backend_dir),
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )

            print(result.stdout)
            print("✅ Django check passed")

        except subprocess.CalledProcessError as e:
            print(f"⚠️  Verification failed: {e}")

            if e.stdout:
                print(e.stdout)

            if e.stderr:
                print(e.stderr)

            return False

        except subprocess.TimeoutExpired:
            print("⚠️  Verification timed out")
            return False

        return True


    def run(self):
        self.print_header()
        self.check_python_version()
        self.recreate_virtual_environment()

        if not self.verify_dependencies():
            print("❌ Initialization stopped: dependency verification failed.")
            sys.exit(1)

        self.setup_env_files()
        self.run_django_setup()
        self.setup_vscode()

        if not self.verify_installation():
            print("❌ Initialization failed: Django verification did not pass.")
            sys.exit(1)


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