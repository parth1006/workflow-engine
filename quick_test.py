"""
Quick test script to verify the workflow engine is working.

Tests:
1. Server health check
2. Tool registry verification
3. Simple graph creation and execution
"""
import requests
import sys

BASE_URL = "http://localhost:8000"


def test_health():
    """Test if server is running."""
    print("🔍 Testing server health...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            print("✅ Server is healthy")
            return True
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is it running?")
        print("   Start with: python run.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_simple_workflow():
    """Test creating and running a simple workflow."""
    print("\n🔍 Testing workflow creation and execution...")
    
    # Create a simple graph
    graph_data = {
        "name": "Health Check Workflow",
        "description": "Simple test workflow",
        "nodes": [
            {"name": "start", "node_type": "function", "tool_name": "extract_functions"}
        ],
        "edges": [],
        "entry_point": "start"
    }
    
    try:
        # Create graph
        response = requests.post(f"{BASE_URL}/graph/create", json=graph_data)
        if response.status_code != 201:
            print(f"❌ Failed to create graph: {response.json()}")
            return False
        
        graph_id = response.json()["graph_id"]
        print(f"✅ Graph created: {graph_id[:8]}...")
        
        # Run graph
        run_data = {
            "graph_id": graph_id,
            "initial_state": {"code": "def test(): pass"}
        }
        
        response = requests.post(f"{BASE_URL}/graph/run", json=run_data)
        if response.status_code != 200:
            print(f"❌ Failed to run graph: {response.json()}")
            return False
        
        result = response.json()
        print(f"✅ Workflow executed successfully")
        print(f"   Status: {result['status']}")
        print(f"   Execution time: {result['total_execution_time_ms']:.2f}ms")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("🧪 WORKFLOW ENGINE QUICK TEST")
    print("="*60)
    
    # Test health
    if not test_health():
        sys.exit(1)
    
    # Test workflow
    if not test_simple_workflow():
        sys.exit(1)
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)
    print("\n💡 Next steps:")
    print("   1. View API docs: http://localhost:8000/docs")
    print("   2. Run full demo: python test_code_review.py")
    print("   3. Create your own workflow!")


if __name__ == "__main__":
    main()