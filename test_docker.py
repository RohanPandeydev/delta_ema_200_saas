import docker

def test_docker():
    try:
        client = docker.from_env()
        print("✅ Docker connection successful!")
        print(f"✅ Docker version: {client.version()}")
        
        # Test listing containers
        containers = client.containers.list(all=True)
        print(f"✅ Found {len(containers)} containers")
        
        return True
    except Exception as e:
        print(f"❌ Docker connection failed: {e}")
        print("Make sure Docker Desktop is running on your system")
        return False

if __name__ == "__main__":
    test_docker()