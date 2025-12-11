"""
Code Review Workflow - Option A from the assignment.

A workflow that analyzes Python code and iteratively improves it
until a quality threshold is met.

Workflow Steps:
1. extract_functions: Parse code and extract function definitions
2. check_complexity: Calculate cyclomatic complexity
3. detect_issues: Find code smells (long functions, deep nesting)
4. suggest_improvements: Generate improvement suggestions
5. calculate_quality: Compute quality score (0-10)
6. Loop back to suggest_improvements if quality_score < 8 (max 5 iterations)
"""
import re
import ast
from typing import Dict, Any, List
from app.core.tool_registry import tool, ToolRegistry
from app.core.models import GraphDefinition, NodeDefinition, EdgeDefinition, NodeType


# ============================================================================
# CODE ANALYSIS TOOLS
# ============================================================================

@tool(name="extract_functions")
def extract_functions(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract function definitions from Python code.
    
    Args:
        state: Must contain 'code' key with Python source code
        
    Returns:
        Updated state with 'functions' list
    """
    code = state.get('code', '')
    functions = []
    
    try:
        # Parse the code into an AST
        tree = ast.parse(code)
        
        # Extract all function definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Get function source code
                func_lines = code.split('\n')[node.lineno - 1:node.end_lineno]
                func_code = '\n'.join(func_lines)
                
                functions.append({
                    'name': node.name,
                    'lineno': node.lineno,
                    'num_lines': node.end_lineno - node.lineno + 1,
                    'code': func_code,
                    'args': [arg.arg for arg in node.args.args]
                })
        
        state['functions'] = functions
        state['num_functions'] = len(functions)
        
    except SyntaxError as e:
        state['functions'] = []
        state['num_functions'] = 0
        state['parse_error'] = str(e)
    
    return state


@tool(name="check_complexity")
def check_complexity(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate cyclomatic complexity for each function.
    
    Simplified complexity = number of decision points + 1
    Decision points: if, for, while, and, or, except
    
    Args:
        state: Must contain 'functions' from extract_functions
        
    Returns:
        Updated state with complexity scores
    """
    functions = state.get('functions', [])
    
    for func in functions:
        code = func.get('code', '')
        
        # Count decision points (simplified metric)
        complexity = 1  # Base complexity
        
        # Count control flow keywords
        complexity += code.count('if ')
        complexity += code.count('elif ')
        complexity += code.count('for ')
        complexity += code.count('while ')
        complexity += code.count(' and ')
        complexity += code.count(' or ')
        complexity += code.count('except')
        
        func['complexity'] = complexity
    
    # Calculate average complexity
    if functions:
        avg_complexity = sum(f['complexity'] for f in functions) / len(functions)
        state['avg_complexity'] = round(avg_complexity, 2)
    else:
        state['avg_complexity'] = 0
    
    return state


@tool(name="detect_issues")
def detect_issues(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect code smells and potential issues.
    
    Checks for:
    - Functions that are too long (>50 lines)
    - High complexity (>10)
    - Deep nesting (>4 levels)
    - Missing docstrings
    
    Args:
        state: Must contain 'functions' with complexity scores
        
    Returns:
        Updated state with 'issues' list
    """
    functions = state.get('functions', [])
    issues = []
    
    for func in functions:
        func_name = func['name']
        num_lines = func['num_lines']
        complexity = func.get('complexity', 0)
        code = func.get('code', '')
        
        # Check function length
        if num_lines > 50:
            issues.append({
                'type': 'long_function',
                'function': func_name,
                'severity': 'medium',
                'message': f"Function '{func_name}' is too long ({num_lines} lines). Consider breaking it up."
            })
        
        # Check complexity
        if complexity > 10:
            issues.append({
                'type': 'high_complexity',
                'function': func_name,
                'severity': 'high',
                'message': f"Function '{func_name}' has high complexity ({complexity}). Simplify logic."
            })
        elif complexity > 7:
            issues.append({
                'type': 'moderate_complexity',
                'function': func_name,
                'severity': 'medium',
                'message': f"Function '{func_name}' has moderate complexity ({complexity}). Could be simplified."
            })
        
        # Check for deep nesting
        max_indent = 0
        for line in code.split('\n'):
            if line.strip():
                indent = len(line) - len(line.lstrip())
                max_indent = max(max_indent, indent // 4)
        
        if max_indent > 4:
            issues.append({
                'type': 'deep_nesting',
                'function': func_name,
                'severity': 'medium',
                'message': f"Function '{func_name}' has deep nesting ({max_indent} levels). Flatten structure."
            })
        
        # Check for docstring
        if not code.strip().startswith('"""') and not code.strip().startswith("'''"):
            issues.append({
                'type': 'missing_docstring',
                'function': func_name,
                'severity': 'low',
                'message': f"Function '{func_name}' is missing a docstring."
            })
    
    state['issues'] = issues
    state['issue_count'] = len(issues)
    
    return state


@tool(name="suggest_improvements")
def suggest_improvements(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate improvement suggestions based on detected issues.
    
    Args:
        state: Must contain 'issues' from detect_issues
        
    Returns:
        Updated state with 'suggestions' list
    """
    issues = state.get('issues', [])
    suggestions = []
    
    # Group issues by type
    issue_types = {}
    for issue in issues:
        issue_type = issue['type']
        if issue_type not in issue_types:
            issue_types[issue_type] = []
        issue_types[issue_type].append(issue)
    
    # Generate suggestions
    if 'long_function' in issue_types:
        suggestions.append({
            'category': 'refactoring',
            'priority': 'high',
            'suggestion': 'Break down long functions into smaller, single-responsibility functions'
        })
    
    if 'high_complexity' in issue_types or 'moderate_complexity' in issue_types:
        suggestions.append({
            'category': 'simplification',
            'priority': 'high',
            'suggestion': 'Reduce complexity by extracting nested logic into helper functions'
        })
    
    if 'deep_nesting' in issue_types:
        suggestions.append({
            'category': 'structure',
            'priority': 'medium',
            'suggestion': 'Flatten nested structures using early returns or guard clauses'
        })
    
    if 'missing_docstring' in issue_types:
        suggestions.append({
            'category': 'documentation',
            'priority': 'low',
            'suggestion': 'Add docstrings to all functions describing purpose, args, and return values'
        })
    
    state['suggestions'] = suggestions
    state['suggestion_count'] = len(suggestions)
    
    # Increment improvement iteration counter
    state['improvement_iteration'] = state.get('improvement_iteration', 0) + 1
    
    return state


@tool(name="calculate_quality")
def calculate_quality(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate overall code quality score (0-10).
    
    Scoring factors:
    - Issue count (fewer is better)
    - Average complexity (lower is better)
    - Function length (shorter is better)
    - Documentation (more is better)
    
    Args:
        state: Must contain analysis results
        
    Returns:
        Updated state with 'quality_score' and 'quality_passed'
    """
    functions = state.get('functions', [])
    issues = state.get('issues', [])
    avg_complexity = state.get('avg_complexity', 0)
    
    # Start with perfect score
    score = 10.0
    
    # Penalize for issues (by severity)
    for issue in issues:
        severity = issue.get('severity', 'low')
        if severity == 'high':
            score -= 1.5
        elif severity == 'medium':
            score -= 0.75
        else:
            score -= 0.25
    
    # Penalize for high average complexity
    if avg_complexity > 10:
        score -= 2.0
    elif avg_complexity > 7:
        score -= 1.0
    elif avg_complexity > 5:
        score -= 0.5
    
    # Penalize for very long functions
    for func in functions:
        if func.get('num_lines', 0) > 100:
            score -= 1.0
        elif func.get('num_lines', 0) > 50:
            score -= 0.5
    
    # Ensure score is in range [0, 10]
    score = max(0.0, min(10.0, score))
    
    state['quality_score'] = round(score, 2)
    state['quality_passed'] = score >= 8.0
    
    return state


# ============================================================================
# WORKFLOW GRAPH DEFINITION
# ============================================================================

def create_code_review_graph() -> GraphDefinition:
    """
    Create the Code Review workflow graph.
    
    Returns:
        GraphDefinition for the code review workflow
    """
    return GraphDefinition(
        name="Code Review Agent",
        description="Analyzes Python code and suggests improvements until quality threshold is met",
        nodes=[
            NodeDefinition(
                name="extract",
                node_type=NodeType.FUNCTION,
                tool_name="extract_functions"
            ),
            NodeDefinition(
                name="complexity",
                node_type=NodeType.FUNCTION,
                tool_name="check_complexity"
            ),
            NodeDefinition(
                name="issues",
                node_type=NodeType.FUNCTION,
                tool_name="detect_issues"
            ),
            NodeDefinition(
                name="suggestions",
                node_type=NodeType.FUNCTION,
                tool_name="suggest_improvements"
            ),
            NodeDefinition(
                name="quality",
                node_type=NodeType.FUNCTION,
                tool_name="calculate_quality"
            ),
        ],
        edges=[
            # Main flow
            EdgeDefinition(from_node="extract", to_node="complexity"),
            EdgeDefinition(from_node="complexity", to_node="issues"),
            EdgeDefinition(from_node="issues", to_node="suggestions"),
            EdgeDefinition(from_node="suggestions", to_node="quality"),
            
            # Loop: if quality not met, suggest more improvements
            EdgeDefinition(
                from_node="quality",
                to_node="suggestions",
                condition="not state.get('quality_passed', False) and state.get('improvement_iteration', 0) < 5",
                label="Continue improving (quality < 8, iteration < 5)"
            ),
        ],
        entry_point="extract"
    )


# ============================================================================
# REGISTRATION FUNCTION
# ============================================================================

def register_code_review_tools():
    """
    Register all code review tools with the global registry.
    
    This function is called on application startup.
    """
    # Tools are automatically registered via @tool decorator
    # This function is here for explicit initialization if needed
    registry = ToolRegistry()
    
    # Verify all tools are registered
    required_tools = [
        "extract_functions",
        "check_complexity",
        "detect_issues",
        "suggest_improvements",
        "calculate_quality"
    ]
    
    registered = registry.list_tools()
    for tool_name in required_tools:
        if tool_name not in registered:
            raise RuntimeError(f"Required tool '{tool_name}' not registered!")
    
    print(f"✅ Code review tools registered: {required_tools}")