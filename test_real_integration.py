#!/usr/bin/env python3
"""
REAL Integration Test - No Bullshit
Tests the actual system end-to-end with real database, real API calls, real AI
"""

import sqlite3
import json
import requests
import time
import sys

def test_real_integration():
    """Test the actual system end-to-end"""
    
    print("🔥 REAL INTEGRATION TEST - NO BULLSHIT")
    print("=" * 60)
    
    # Test 1: Database Schema Validation
    print("\n1. 🗄️ Testing Database Schema...")
    if not test_database_schema():
        print("❌ Database schema test FAILED")
        return False
    
    # Test 2: API Endpoint Validation  
    print("\n2. 🌐 Testing API Endpoints...")
    if not test_api_endpoints():
        print("❌ API endpoint test FAILED")
        return False
    
    # Test 3: Real Transcription Processing
    print("\n3. 📝 Testing Real Transcription Processing...")
    if not test_transcription_processing():
        print("❌ Transcription processing test FAILED")
        return False
    
    # Test 4: Completed Work Generation
    print("\n4. ⚡ Testing Completed Work Generation...")
    if not test_completed_work_generation():
        print("❌ Completed work generation test FAILED")
        return False
    
    print("\n🎉 ALL TESTS PASSED - SYSTEM IS ACTUALLY WORKING!")
    return True

def test_database_schema():
    """Test that database has all required fields"""
    
    try:
        conn = sqlite3.connect("gum.db")
        cursor = conn.cursor()
        
        # Check suggestions table schema
        cursor.execute("PRAGMA table_info(suggestions)")
        columns = [row[1] for row in cursor.fetchall()]
        
        required_fields = [
            'has_completed_work',
            'completed_work_content', 
            'completed_work_type',
            'completed_work_preview',
            'action_label',
            'executor_type',
            'work_metadata'
        ]
        
        missing_fields = [field for field in required_fields if field not in columns]
        
        if missing_fields:
            print(f"   ❌ Missing database fields: {missing_fields}")
            return False
        
        print(f"   ✅ All required fields present: {required_fields}")
        return True
        
    except Exception as e:
        print(f"   ❌ Database test failed: {e}")
        return False
    finally:
        if conn:
            conn.close()

def test_api_endpoints():
    """Test that API endpoints are accessible"""
    
    base_url = "http://localhost:8000"
    
    endpoints_to_test = [
        "/health",
        "/suggestions/history"
    ]
    
    for endpoint in endpoints_to_test:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"   ✅ {endpoint}: Working")
            else:
                print(f"   ❌ {endpoint}: HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"   ❌ {endpoint}: Connection failed - {e}")
            print("   💡 Make sure the controller is running: python controller.py")
            return False
    
    return True

def test_transcription_processing():
    """Test actual transcription processing through the API"""
    
    base_url = "http://localhost:8000"
    
    # Real test transcription
    test_transcription = {
        "content": """Application: Microsoft Excel
Window Title: Q3_Financial_Report.xlsx
Visible Text Content and UI Elements:
Revenue: $2,450,000
Expenses: $1,890,000
Profit Margin: 22.9%
YoY Growth: 15.3%
Current Quarter: Q3 2024
Previous Quarter: $2,120,000
Budget vs Actual: 103.2%
Key Metrics Dashboard showing:
- Customer Acquisition Cost: $125
- Lifetime Value: $1,850
- Churn Rate: 3.2%
- Monthly Recurring Revenue: $815,000
User is analyzing quarterly financial performance and comparing against budget targets."""
    }
    
    try:
        # Submit transcription
        print("   📤 Submitting real transcription...")
        response = requests.post(
            f"{base_url}/observations/text",
            json=test_transcription,
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"   ❌ Transcription submission failed: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
        print("   ✅ Transcription submitted successfully")
        
        # Wait for processing
        print("   ⏳ Waiting for proactive suggestions...")
        time.sleep(5)
        
        # Check for suggestions
        suggestions_response = requests.get(f"{base_url}/suggestions/history?limit=5")
        if suggestions_response.status_code != 200:
            print(f"   ❌ Failed to fetch suggestions: HTTP {suggestions_response.status_code}")
            return False
        
        suggestions = suggestions_response.json()
        print(f"   📊 Found {len(suggestions)} suggestions")
        
        # Check if any have completed work
        completed_work_count = sum(1 for s in suggestions if s.get('has_completed_work'))
        print(f"   ⚡ Completed work items: {completed_work_count}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Transcription processing test failed: {e}")
        return False

def test_completed_work_generation():
    """Test that completed work is actually generated and stored"""
    
    try:
        conn = sqlite3.connect("gum.db")
        cursor = conn.cursor()
        
        # Check for recent completed work in database
        cursor.execute("""
            SELECT id, title, has_completed_work, completed_work_content, 
                   completed_work_type, action_label, executor_type
            FROM suggestions 
            WHERE has_completed_work = 1 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        
        completed_work_records = cursor.fetchall()
        
        if not completed_work_records:
            print("   ❌ No completed work found in database")
            return False
        
        print(f"   ✅ Found {len(completed_work_records)} completed work records")
        
        # Validate the data quality
        for record in completed_work_records:
            record_id, title, has_work, content, content_type, action_label, executor_type = record
            
            print(f"   📋 Record {record_id}:")
            print(f"      Title: {title}")
            print(f"      Has Work: {has_work}")
            print(f"      Content Length: {len(content) if content else 0} chars")
            print(f"      Content Type: {content_type}")
            print(f"      Action Label: {action_label}")
            print(f"      Executor: {executor_type}")
            
            # Validate required fields
            if not title or not content or not action_label:
                print(f"   ❌ Record {record_id} missing required data")
                return False
        
        print("   ✅ All completed work records have valid data")
        return True
        
    except Exception as e:
        print(f"   ❌ Completed work test failed: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚨 WARNING: This test requires:")
    print("   1. Database with migrated schema (gum.db)")
    print("   2. Controller running (python controller.py)")
    print("   3. AI client configured with valid API keys")
    print()
    
    input("Press Enter to continue with REAL integration test...")
    
    success = test_real_integration()
    
    if success:
        print("\n🎉 REAL INTEGRATION TEST: PASSED")
        print("The maximally helpful AI system is actually working!")
    else:
        print("\n💥 REAL INTEGRATION TEST: FAILED")
        print("The system has real problems that need fixing.")
        sys.exit(1)