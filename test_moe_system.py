#!/usr/bin/env python3
"""
Test the complete MoE Recommendation System
Tests fix for sahi recommendations working properly
"""

import sys
sys.path.insert(0, '.')

from app.ai.moe_engine import TransformerMoE, AttentionRouter
from app.utils.db import execute_query
import json

def test_moe_initialization():
    """Test if MoE engine initializes without errors"""
    print("\n" + "="*60)
    print("TEST 1: MoE Engine Initialization")
    print("="*60)
    
    try:
        # Test with a test user
        moe = TransformerMoE(1)
        print("✅ MoE Engine initialized successfully")
        print(f"   User ID: 1")
        print(f"   Weak topics: {moe.context['weak_count']}")
        print(f"   Quiz attempts: {moe.context['quiz_count']}")
        print(f"   Videos watched: {moe.context['watch_count']}")
        print(f"   Average score: {moe.context['avg_score']:.1f}%")
        
        return True
    except Exception as e:
        print(f"❌ Failed to initialize MoE: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_attention_weights():
    """Test if attention weights are computed correctly"""
    print("\n" + "="*60)
    print("TEST 2: Attention Weights Computation")
    print("="*60)
    
    try:
        moe = TransformerMoE(1)
        weights = moe.weights
        
        print("✅ Attention weights computed")
        print(f"   Weak Topic Expert:    {weights['weak_topic']:.4f}")
        print(f"   Performance Expert:   {weights['performance']:.4f}")
        print(f"   History Expert:       {weights['history']:.4f}")
        
        # Verify weights sum to ~1.0 (softmax)
        total = sum(weights.values())
        print(f"   Total weight sum:     {total:.4f}")
        
        if 0.99 <= total <= 1.01:
            print("✅ Weights correctly normalized (softmax)")
            return True
        else:
            print("❌ Weights not properly normalized")
            return False
            
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_expert_recommendations():
    """Test if all experts produce recommendations"""
    print("\n" + "="*60)
    print("TEST 3: Expert Recommendations")
    print("="*60)
    
    try:
        moe = TransformerMoE(1)
        
        e1 = moe.expert_weak_topics()
        e2 = moe.expert_performance()
        e3 = moe.expert_history()
        
        print("✅ All experts executed")
        print(f"   Expert 1 (Weak Topics):   {len(e1)} queries")
        print(f"   Expert 2 (Performance):   {len(e2)} queries") 
        print(f"   Expert 3 (History):       {len(e3)} queries")
        print(f"   Total:                    {len(e1) + len(e2) + len(e3)} queries")
        
        # Verify each query has required fields
        all_queries = e1 + e2 + e3
        required_fields = ['query', 'topic', 'expert', 'expert_score', 'final_score', 'reason', 'weight_used']
        
        for q in all_queries:
            for field in required_fields:
                if field not in q:
                    print(f"❌ Missing field '{field}' in query")
                    return False
        
        print("✅ All queries have required fields")
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_final_recommendations():
    """Test if final recommendations are properly sorted"""
    print("\n" + "="*60)
    print("TEST 4: Final Recommendations Sorting")
    print("="*60)
    
    try:
        moe = TransformerMoE(1)
        recommendations = moe.get_recommendations()
        
        print(f"✅ Got {len(recommendations)} recommendations")
        
        # Verify sorted by final_score descending
        if len(recommendations) > 1:
            is_sorted = all(
                recommendations[i]['final_score'] >= recommendations[i+1]['final_score']
                for i in range(len(recommendations)-1)
            )
            
            if is_sorted:
                print("✅ Recommendations properly sorted by final_score")
            else:
                print("❌ Recommendations NOT sorted correctly")
                return False
        
        # Display top 3
        print("\nTop 3 Recommendations:")
        for i, r in enumerate(recommendations[:3], 1):
            print(f"  {i}. [{r['expert']:12}] score={r['final_score']:.4f} — {r['reason'][:50]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_context_building():
    """Test if student context is built correctly"""
    print("\n" + "="*60)
    print("TEST 5: Student Context Building")
    print("="*60)
    
    try:
        moe = TransformerMoE(1)
        ctx = moe.context
        
        print("✅ Context built successfully")
        print(f"   weak_count:  {ctx['weak_count']}")
        print(f"   quiz_count:  {ctx['quiz_count']}")
        print(f"   watch_count: {ctx['watch_count']}")
        print(f"   avg_score:   {ctx['avg_score']:.1f}%")
        
        # Verify data loading
        print("\nData Loaded from Database:")
        print(f"   User preferences: field='{moe.data['field']}', " 
              f"skill_level='{moe.data['skill_level']}'")
        print(f"   Weak topics found: {len(moe.data['weak'])}")
        print(f"   Performance records: {len(moe.data['performance'])}")
        print(f"   Videos watched: {len(moe.data['watched'])}")
        print(f"   Learning curves: {len(moe.data['curves'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "="*60)
    print("🤖 COMPLETE MoE RECOMMENDATION SYSTEM TEST")
    print("="*60)
    
    results = {
        'Initialization': test_moe_initialization(),
        'Attention Weights': test_attention_weights(),
        'Expert Recommendations': test_expert_recommendations(),
        'Context Building': test_context_building(),
        'Final Recommendations': test_final_recommendations(),
    }
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "="*60)
    if failed == 0:
        print(f"✅ ALL {passed} TESTS PASSED!")
        print("🎉 Recommendation system is working correctly")
    else:
        print(f"❌ {failed} test(s) failed, {passed} passed")
    print("="*60 + "\n")
    
    return failed == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
