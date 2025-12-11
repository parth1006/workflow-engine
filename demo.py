"""
Demo script showcasing the workflow engine capabilities.

This script demonstrates:
1. Graph creation
2. Workflow execution
3. State inspection
4. Loop behavior
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def demo():
    """Run the complete demo."""
    print_section("🚀 WORKFLOW ENGINE DEMO")
    
    # Sample code with issues
    bad_code = '''
def complex_function(a, b, c, d, e):
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        return a + b + c + d + e
    return 0
'''
    
    print("📝 Sample Code to Analyze:")
    print(bad_code)
    
    # Create workflow
    print_section("1️⃣ Creating Code Review Workflow")
    
    from app.workflows.code_review import create_code_review_graph
    graph = create_code_review_graph()
    
    response = requests.post(
        f"{BASE_URL}/graph/create",
        json={
            "name": graph.name,
            "description": graph.description,
            "nodes": [n.model_dump() for n in graph.nodes],
            "edges": [e.model_dump() for e in graph.edges],
            "entry_point": graph.entry_point
        }
    )
    
    graph_id = response.json()["graph_id"]
    print(f"✅ Graph ID: {graph_id}")
    print(f"   Nodes: {len(graph.nodes)}")
    print(f"   Edges: {len(graph.edges)}")
    
    # Execute workflow
    print_section("2️⃣ Executing Workflow")
    
    print("⏳ Analyzing code...")
    response = requests.post(
        f"{BASE_URL}/graph/run",
        json={
            "graph_id": graph_id,
            "initial_state": {"code": bad_code}
        }
    )
    
    result = response.json()
    run_id = result["run_id"]
    
    print(f"✅ Execution Complete!")
    print(f"   Run ID: {run_id}")
    print(f"   Status: {result['status']}")
    print(f"   Time: {result['total_execution_time_ms']:.2f}ms")
    
    # Show results
    print_section("3️⃣ Analysis Results")
    
    state = result["final_state"]
    
    print(f"📊 Functions Analyzed: {state.get('num_functions', 0)}")
    for func in state.get('functions', []):
        print(f"   • {func['name']}: {func['num_lines']} lines, complexity {func.get('complexity', 0)}")
    
    print(f"\n⚠️  Issues Found: {state.get('issue_count', 0)}")
    for issue in state.get('issues', [])[:3]:
        print(f"   [{issue['severity'].upper()}] {issue['message']}")
    
    print(f"\n🎯 Quality Score: {state.get('quality_score', 0)}/10")
    print(f"   Target: 8.0 (Passed: {state.get('quality_passed', False)})")
    
    # Show loop behavior
    print_section("4️⃣ Loop Behavior")
    
    iterations = state.get('improvement_iteration', 0)
    print(f"🔁 Improvement Iterations: {iterations}")
    print(f"📊 Total Nodes Executed: {len(result['execution_logs'])}")
    print(f"⚡ Loop Iterations: {result['iterations_completed']}")
    
    if iterations >= 5:
        print("\n⚠️  Stopped at max iterations (safety limit)")
    else:
        print("\n✅ Quality threshold met!")
    
    # Show execution logs
    print_section("5️⃣ Execution Flow")
    
    print("Execution Path:")
    for i, log in enumerate(result['execution_logs'][:10], 1):
        status = "✅" if log['success'] else "❌"
        print(f"   {i}. {status} {log['node_name']} ({log['execution_time_ms']:.2f}ms)")
    
    if len(result['execution_logs']) > 10:
        print(f"   ... and {len(result['execution_logs']) - 10} more steps")
    
    # Summary
    print_section("✅ DEMO COMPLETE")
    
    print("What we demonstrated:")
    print("  ✅ Graph creation with multiple nodes")
    print("  ✅ Sequential execution flow")
    print("  ✅ Conditional branching (quality checks)")
    print("  ✅ Loop behavior (iterative improvement)")
    print("  ✅ Max iteration safety")
    print("  ✅ State management across nodes")
    print("  ✅ Detailed execution logging")
    
    print("\n💡 Next Steps:")
    print("  • View full API docs: http://localhost:8000/docs")
    print("  • Check run state: GET /graph/state/{run_id}")
    print("  • List all graphs: GET /graph/list")
    print("  • Create your own workflow!")


if __name__ == "__main__":
    print("🎬 Starting Demo...")
    print("⚠️  Make sure server is running: python run.py\n")
    
    input("Press Enter to begin...")
    
    try:
        demo()
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to server")
        print("   Run: python run.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()