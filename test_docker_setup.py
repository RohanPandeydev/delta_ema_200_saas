import sys
import subprocess

def check_docker_installation():
    print("🔍 Checking Docker installation...")
    
    try:
        # Check if docker command is available
        result = subprocess.run(['docker', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Docker is installed: {result.stdout.strip()}")
            return True
        else:
            print("❌ Docker is not installed or not in PATH")
            return False
    except FileNotFoundError:
        print("❌ Docker command not found. Please install Docker Desktop.")
        return False

def check_docker_service():
    print("\n🔍 Checking Docker service status...")
    
    try:
        result = subprocess.run(['docker', 'info'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Docker service is running")
            return True
        else:
            print("❌ Docker service is not running")
            print("💡 Please start Docker Desktop")
            return False
    except FileNotFoundError:
        print("❌ Docker command not found")
        return False

def check_python_docker():
    print("\n🔍 Checking Python docker package...")
    
    try:
        import docker
        print("✅ Python docker package is installed")
        return True
    except ImportError:
        print("❌ Python docker package not installed")
        print("💡 Run: pip install docker")
        return False

def main():
    print("🚀 Docker Setup Check")
    print("=" * 50)
    
    docker_installed = check_docker_installation()
    docker_running = check_docker_service()
    python_docker_installed = check_python_docker()
    
    print("\n" + "=" * 50)
    
    if docker_installed and docker_running and python_docker_installed:
        print("🎉 All checks passed! Docker is ready to use.")
        
        # Test Docker Python client
        try:
            import docker
            client = docker.from_env()
            print(f"✅ Docker Python client connected successfully")
            print(f"✅ Server version: {client.version()['Version']}")
        except Exception as e:
            print(f"❌ Docker Python client error: {e}")
            
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        
        if not docker_installed:
            print("\n📥 To install Docker Desktop:")
            print("1. Go to: https://www.docker.com/products/docker-desktop/")
            print("2. Download Docker Desktop for Windows")
            print("3. Run the installer and follow the setup instructions")
            print("4. Restart your computer after installation")
            
        if not python_docker_installed:
            print("\n📥 To install Python docker package:")
            print("Run: pip install docker")

if __name__ == "__main__":
    main()