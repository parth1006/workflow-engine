"""
Test the Code Review workflow with sample code.
"""
import requests
import json
from app.workflows.code_review import create_code_review_graph

# Sample Python code to review (intentionally has issues)
SAMPLE_CODE = '''
def process_data(data, config, flags, mode):
    results = []
    for item in data:
        if item:
            if item['type'] == 'A':
                if item['value'] > 100:
                    if flags['process']:
                        if mode == 'strict':
                            results.append(item['value'] * 2)
                        else:
                            results.append(item['value'])
            elif item['type'] == 'B':
                if item['value'] < 50:
                    results.append(item['value'] / 2)
    return results

def calculate(x, y, z, a, b, c, d, e, f, g):
    total = 0
    if x > 0:
        total += x
    if y > 0:
        total += y
    if z > 0:
        total += z
    for val in [a, b, c, d, e, f, g]:
        if val:
            if val > 10:
                total += val * 2
            else:
                total += val
    return total
'''


def test_code_review_workflow():
    print("\n" + "="*70)
    print("TESTING CODE REVIEW WORKFLOW")
    print("="*70)
    
    # Step 1: Create the graph
    print("\n📊 Step 1: Creating Code Review Graph...")
    graph = create_code_review_graph()
    
    create_response = requests.post(
        "http://localhost:8000/graph/create",
        json={
            "name": graph.name,
            "description": graph.description,
            "nodes": [node.model_dump() for node in graph.nodes],
            "edges": [edge.model_dump() for edge in graph.edges],
            "entry_point": graph.entry_point
        }
    )
    
    if create_response.status_code != 201:
        print(f"❌ Failed to create graph: {create_response.json()}")
        return
    
    graph_id = create_response.json()["graph_id"]
    print(f"✅ Graph created: {graph_id}\n")
    
    # Step 2: Run the workflow
    print("🔄 Step 2: Running Code Review Workflow...")
    print(f"Analyzing code ({len(SAMPLE_CODE)} characters)...")
    
    run_response = requests.post(
        "http://localhost:8000/graph/run",
        json={
            "graph_id": graph_id,
            "initial_state": {
                "code": SAMPLE_CODE
            }
        }
    )
    
    if run_response.status_code != 200:
        print(f"❌ Failed to run graph: {run_response.json()}")
        return
    
    result = run_response.json()
    
    # Step 3: Display Results
    print("\n" + "="*70)
    print("📋 ANALYSIS RESULTS")
    print("="*70)
    
    final_state = result['final_state']
    
    print(f"\n📈 Functions Found: {final_state.get('num_functions', 0)}")
    for func in final_state.get('functions', []):
        print(f"  - {func['name']}: {func['num_lines']} lines, complexity {func.get('complexity', 0)}")
    
    print(f"\n⚠️  Issues Detected: {final_state.get('issue_count', 0)}")
    for issue in final_state.get('issues', [])[:5]:  # Show first 5
        print(f"  [{issue['severity'].upper()}] {issue['message']}")
    
    print(f"\n💡 Suggestions Generated: {final_state.get('suggestion_count', 0)}")
    for suggestion in final_state.get('suggestions', []):
        print(f"  [{suggestion['priority'].upper()}] {suggestion['suggestion']}")
    
    print(f"\n🎯 Quality Score: {final_state.get('quality_score', 0)}/10")
    print(f"✅ Quality Passed: {final_state.get('quality_passed', False)}")
    
    print(f"\n🔁 Improvement Iterations: {final_state.get('improvement_iteration', 0)}")
    print(f"⚡ Total Execution Time: {result['total_execution_time_ms']:.2f}ms")
    print(f"📊 Nodes Executed: {len(result['execution_logs'])}")
    print(f"🔄 Loop Iterations: {result['iterations_completed']}")
    
    print("\n" + "="*70)
    print("✅ CODE REVIEW WORKFLOW COMPLETED!")
    print("="*70)


if __name__ == "__main__":
    print("🧪 Make sure the server is running: python run.py")
    input("Press Enter to continue...")
    
    try:
        test_code_review_workflow()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to server.")
        print("   Make sure to run: python run.py")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()