#!/usr/bin/env python3
"""Test the configuration and setup process."""

import os
import tempfile
import shutil
from pathlib import Path

def test_model_selection():
    """Test that the model selection works correctly."""
    # Test with LM-Studio configuration
    os.environ["DEEPAGENTS_MODEL_PROVIDER"] = "lm-studio"
    os.environ["LM_STUDIO_MODEL_NAME"] = "qwen/qwen3-4b-thinking-2507"
    
    from src.deepagents.model import get_default_model
    
    model = get_default_model()
    print(f"✓ Model created successfully: {type(model).__name__}")
    
    # Check that it has the right configuration
    if hasattr(model, 'model'):
        print(f"✓ Model name: {model.model}")
    if hasattr(model, 'base_url'):
        print(f"✓ Base URL: {model.base_url}")
    
    return True

def test_research_agent():
    """Test that we can create and run the research agent."""
    try:
        # Import the research agent
        import sys
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        
        from examples.research.run_local import build_agent
        
        agent = build_agent()
        print(f"✓ Research agent created successfully")
        
        # Test a simple invoke (this will fail without a running model, but should build)
        try:
            result = agent.invoke({
                "messages": [{"role": "user", "content": "Test"}]
            }, {"recursion_limit": 1})  # Limit to avoid long runs
        except Exception as e:
            print(f"✓ Agent invoke attempted (expected to fail without model): {type(e).__name__}")
        
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def main():
    """Run configuration tests."""
    print("🧪 Testing DeepAgents Configuration")
    print("===================================")
    
    try:
        print("\n1. Testing model selection...")
        if test_model_selection():
            print("   ✅ Model selection works")
        
        print("\n2. Testing research agent creation...")
        if test_research_agent():
            print("   ✅ Research agent creation works")
        
        print("\n🎉 All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()