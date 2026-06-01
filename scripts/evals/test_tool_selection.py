"""
Evaluation script to measure LLM tool selection accuracy.

Tests whether the model chooses the correct tool for a variety of queries.
Tracks accuracy by category to identify weak areas.

Usage:
    python scripts/evals/test_tool_selection.py [--base-url http://localhost:8000]
"""

import argparse
import json
import sys
from dataclasses import dataclass

import httpx


@dataclass
class TestCase:
    """Single test case for tool selection."""
    query: str
    expected_tool: str
    category: str
    explanation: str | None = None


# Comprehensive test suite covering all tools
TEST_CASES = [
    # Employee & HR (should use query_files)
    TestCase(
        query="Give me a list of employees",
        expected_tool="query_files",
        category="employees",
        explanation="Employee roster is in file share, not SQL"
    ),
    TestCase(
        query="Show me the employee roster",
        expected_tool="query_files",
        category="employees",
    ),
    TestCase(
        query="Who works in the engineering department?",
        expected_tool="query_files",
        category="employees",
    ),
    TestCase(
        query="What are employee salaries?",
        expected_tool="query_files",
        category="employees",
    ),

    # Financial reports (should use query_files)
    TestCase(
        query="Show me the Q1 financial report",
        expected_tool="query_files",
        category="financial",
    ),
    TestCase(
        query="What's our revenue for Q2?",
        expected_tool="query_files",
        category="financial",
        explanation="Financial reports are documents in file share"
    ),
    TestCase(
        query="Give me the financial statements",
        expected_tool="query_files",
        category="financial",
    ),

    # Product & Strategy (should use query_files)
    TestCase(
        query="What is the product roadmap?",
        expected_tool="query_files",
        category="product",
        explanation="Product roadmap is a document in file share"
    ),
    TestCase(
        query="Show me the product roadmap for 2026",
        expected_tool="query_files",
        category="product",
    ),
    TestCase(
        query="What's our strategic plan?",
        expected_tool="query_files",
        category="product",
    ),

    # Meeting notes (should use query_files)
    TestCase(
        query="Show me executive meeting notes",
        expected_tool="query_files",
        category="meetings",
    ),
    TestCase(
        query="What were the decisions from the May meeting?",
        expected_tool="query_files",
        category="meetings",
        explanation="Meeting notes are documents in file share"
    ),

    # Technical specs (should use query_files)
    TestCase(
        query="Show me the technical specification",
        expected_tool="query_files",
        category="technical",
    ),
    TestCase(
        query="What is the service restart spec?",
        expected_tool="query_files",
        category="technical",
    ),

    # Policies & Handbook (should use query_knowledge_base)
    TestCase(
        query="What is our remote work policy?",
        expected_tool="query_knowledge_base",
        category="policies",
        explanation="Policies are in knowledge base, not file share"
    ),
    TestCase(
        query="How much vacation do employees get?",
        expected_tool="query_knowledge_base",
        category="policies",
    ),
    TestCase(
        query="What is the expense reimbursement procedure?",
        expected_tool="query_knowledge_base",
        category="policies",
    ),
    TestCase(
        query="Show me the employee handbook",
        expected_tool="query_knowledge_base",
        category="policies",
    ),

    # Emails (should use query_mail)
    TestCase(
        query="Show me emails from john",
        expected_tool="query_mail",
        category="email",
    ),
    TestCase(
        query="What did the team email about Q2?",
        expected_tool="query_mail",
        category="email",
    ),
    TestCase(
        query="Find emails with subject 'project update'",
        expected_tool="query_mail",
        category="email",
    ),

    # OneDrive (should use query_onedrive)
    TestCase(
        query="Show me files in my OneDrive",
        expected_tool="query_onedrive",
        category="onedrive",
    ),
    TestCase(
        query="Find the team folder in OneDrive",
        expected_tool="query_onedrive",
        category="onedrive",
    ),

    # Real estate / Brokerage (should use query_sql)
    TestCase(
        query="What multifamily properties do we have in Memphis?",
        expected_tool="query_sql",
        category="real_estate",
        explanation="Real estate data is in SQL database, not file share"
    ),
    TestCase(
        query="Show me deals in the closing stage",
        expected_tool="query_sql",
        category="real_estate",
    ),
    TestCase(
        query="Who are the top 10 agents by commission?",
        expected_tool="query_sql",
        category="real_estate",
    ),
    TestCase(
        query="What is the average cap rate in our portfolio?",
        expected_tool="query_analytics",
        category="analytics",
    ),

    # Document generation (should use query_document_generation)
    TestCase(
        query="Generate an executive summary",
        expected_tool="query_document_generation",
        category="document_generation",
    ),
    TestCase(
        query="Create a board briefing",
        expected_tool="query_document_generation",
        category="document_generation",
    ),
    TestCase(
        query="Write a sales report",
        expected_tool="query_document_generation",
        category="document_generation",
    ),
]


def extract_tool_from_response(response_text: str) -> str | None:
    """
    Extract the tool name from the response.
    Looks for tool_use blocks or function call patterns.
    """
    # Look for function calling format
    if '"name"' in response_text and (
        "query_files" in response_text or
        "query_sql" in response_text or
        "query_mail" in response_text or
        "query_analytics" in response_text or
        "query_knowledge_base" in response_text or
        "query_document_generation" in response_text or
        "query_onedrive" in response_text
    ):
        # Extract the first tool mentioned
        for tool in [
            "query_files", "query_sql", "query_mail", "query_analytics",
            "query_knowledge_base", "query_document_generation", "query_onedrive",
            "query_postgresql", "query_memory", "query_dashboard"
        ]:
            if f'"{tool}"' in response_text or f"'{tool}'" in response_text:
                return tool

    # Fallback: look for any tool name in the response
    for tool in [
        "query_files", "query_sql", "query_mail", "query_analytics",
        "query_knowledge_base", "query_document_generation", "query_onedrive",
        "query_postgresql", "query_memory", "query_dashboard"
    ]:
        if tool in response_text.lower():
            return tool

    return None


async def test_tool_selection(base_url: str = "http://localhost:8000") -> None:
    """Run tool selection tests and report results."""

    client = httpx.AsyncClient(timeout=30.0)
    results_by_category = {}
    all_results = []

    print("\n🧪 Testing Tool Selection Accuracy")
    print(f"📍 Base URL: {base_url}")
    print(f"📊 Total test cases: {len(TEST_CASES)}\n")
    print("=" * 80)

    for i, test_case in enumerate(TEST_CASES, 1):
        try:
            # Make streaming chat request
            payload = {
                "message": test_case.query,
                "history": []
            }

            response = await client.post(
                f"{base_url}/chat",
                json=payload,
                headers={"Accept": "text/event-stream"}
            )

            if response.status_code != 200:
                result = {
                    "query": test_case.query,
                    "expected": test_case.expected_tool,
                    "actual": "ERROR",
                    "correct": False,
                    "status_code": response.status_code
                }
                print(f"\n❌ Test {i}: {test_case.query[:60]}")
                print(f"   Status: {response.status_code}")
            else:
                # Stream the response and look for tool calls
                full_response = ""
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "tool_call":
                                full_response += json.dumps(data)
                        except json.JSONDecodeError:
                            pass

                actual_tool = extract_tool_from_response(full_response)
                is_correct = actual_tool == test_case.expected_tool

                result = {
                    "query": test_case.query,
                    "expected": test_case.expected_tool,
                    "actual": actual_tool or "NO_TOOL_CALLED",
                    "correct": is_correct,
                    "category": test_case.category
                }

                status = "✅" if is_correct else "❌"
                print(f"\n{status} Test {i}: {test_case.query[:60]}")
                if test_case.explanation:
                    print(f"   Reason: {test_case.explanation}")
                print(f"   Expected: {test_case.expected_tool}")
                if not is_correct:
                    print(f"   Got:      {result['actual']}")

            all_results.append(result)

            # Track by category
            category = test_case.category
            if category not in results_by_category:
                results_by_category[category] = {"correct": 0, "total": 0}
            results_by_category[category]["total"] += 1
            if result["correct"]:
                results_by_category[category]["correct"] += 1

        except Exception as e:
            print(f"\n⚠️  Test {i} error: {e}")
            all_results.append({
                "query": test_case.query,
                "expected": test_case.expected_tool,
                "actual": "EXCEPTION",
                "correct": False,
                "error": str(e)
            })

    # Summary report
    print("\n" + "=" * 80)
    print("\n📊 SUMMARY BY CATEGORY\n")

    total_correct = 0
    total_tests = 0

    for category in sorted(results_by_category.keys()):
        stats = results_by_category[category]
        percentage = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
        total_correct += stats["correct"]
        total_tests += stats["total"]

        status = "✅" if percentage == 100 else "⚠️ " if percentage >= 70 else "❌"
        print(f"{status} {category:20s}: {stats['correct']:2d}/{stats['total']:2d} ({percentage:5.1f}%)")

    overall_percentage = (total_correct / total_tests * 100) if total_tests > 0 else 0
    print(f"\n📈 OVERALL: {total_correct}/{total_tests} ({overall_percentage:.1f}%)")

    # Detailed failures
    failures = [r for r in all_results if not r["correct"]]
    if failures:
        print("\n" + "=" * 80)
        print("\n❌ FAILURES (tool selection errors)\n")
        for failure in failures:
            print(f"Query: {failure['query']}")
            print(f"Expected: {failure['expected']}")
            print(f"Got:      {failure['actual']}")
            print()

    # Recommendation
    print("=" * 80)
    if overall_percentage >= 90:
        print("\n✅ Tool selection is highly accurate! Keep monitoring.")
    elif overall_percentage >= 70:
        print("\n⚠️  Tool selection accuracy is acceptable but could be improved.")
        print("   Consider reviewing failed queries and refining tool descriptions.")
    else:
        print("\n❌ Tool selection accuracy is low. Review system prompt and tool descriptions.")
        print("   Focus on the categories with lowest accuracy first.")

    await client.aclose()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Test LLM tool selection accuracy"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of EvieAI orchestrator (default: http://localhost:8000)"
    )

    args = parser.parse_args()

    try:
        import asyncio
        asyncio.run(test_tool_selection(args.base_url))
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
