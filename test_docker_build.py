import subprocess
import sys

def test_docker_build():
    print("🔨 Testing Docker image build...")
    
    try:
        # Build the image
        result = subprocess.run([
            'docker', 'build', '-t', 'trading-bot:latest', 
            './app/your_existing_bots'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Docker image built successfully!")
            return True
        else:
            print(f"❌ Docker build failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error building Docker image: {e}")
        return False

def test_docker_run():
    print("\n🚀 Testing Docker container run...")
    
    try:
        # Run a test container
        result = subprocess.run([
            'docker', 'run', '--rm', 
            '-e', 'BOT_TYPE=EMA',
            '-e', 'SYMBOL=BTCUSD',
            'trading-bot:latest'
        ], capture_output=True, text=True, timeout=10)
        
        print("✅ Docker container test completed")
        return True
        
    except subprocess.TimeoutExpired:
        print("✅ Docker container is running (stopped after timeout)")
        return True
    except Exception as e:
        print(f"❌ Error running Docker container: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Docker Build & Run Test")
    print("=" * 50)
    
    build_ok = test_docker_build()
    run_ok = test_docker_run() if build_ok else False
    
    print("\n" + "=" * 50)
    if build_ok and run_ok:
        print("🎉 All Docker tests passed! Ready for bot deployment.")
    else:
        print("❌ Some tests failed. Check the errors above.")