import requests
import sys
import json
from datetime import datetime
import os

class CRMAPITester:
    def __init__(self, base_url="https://inboxhub-3.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'} if not files else {}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files)
                else:
                    response = requests.post(url, json=data, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                except:
                    print(f"   Response: {response.text[:100]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")

            self.results.append({
                "test": name,
                "endpoint": endpoint,
                "method": method,
                "expected_status": expected_status,
                "actual_status": response.status_code,
                "success": success,
                "response_preview": response.text[:100] if not success else "OK"
            })

            return success, response.json() if success and response.text else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.results.append({
                "test": name,
                "endpoint": endpoint,
                "method": method,
                "expected_status": expected_status,
                "actual_status": "ERROR",
                "success": False,
                "response_preview": str(e)
            })
            return False, {}

    def test_excel_import(self):
        """Test Excel import functionality"""
        try:
            # Use the sample file
            with open('/tmp/sample_contacts.xlsx', 'rb') as f:
                files = {'file': ('sample_contacts.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                success, response = self.run_test(
                    "Excel Import",
                    "POST",
                    "excel/import",
                    200,
                    files=files
                )
            return success, response
        except Exception as e:
            print(f"❌ Excel import failed: {str(e)}")
            return False, {}

    def test_get_categories(self):
        """Test getting categories"""
        success, response = self.run_test(
            "Get Categories",
            "GET",
            "categories",
            200
        )
        return success, response

    def test_send_messages(self):
        """Test sending messages (will fail without credentials - expected)"""
        success, response = self.run_test(
            "Send Messages",
            "POST",
            "messages/send",
            200,
            data={
                "contact_ids": ["test-id"],
                "platform": "email",
                "subject": "Test Subject",
                "message": "Test message"
            }
        )
        return success, response

    def test_analyze_message(self):
        """Test message analysis"""
        success, response = self.run_test(
            "Analyze Message",
            "POST",
            "messages/analyze",
            200,
            data={
                "contact_id": "test-contact-id",
                "message": "This is a great product! I'm very interested."
            }
        )
        return success, response

    def test_get_conversations(self):
        """Test getting conversations"""
        success, response = self.run_test(
            "Get Conversations",
            "GET",
            "conversations",
            200
        )
        return success, response

    def test_get_analytics(self):
        """Test analytics endpoint"""
        success, response = self.run_test(
            "Get Analytics",
            "GET",
            "analytics",
            200
        )
        return success, response

def main():
    print("🚀 Starting CRM Backend API Tests")
    print("=" * 50)
    
    tester = CRMAPITester()
    
    # Test sequence
    print("\n📊 Testing Core Functionality...")
    
    # 1. Test Excel import first
    excel_success, excel_data = tester.test_excel_import()
    
    # 2. Test categories (should have data after import)
    categories_success, categories_data = tester.test_get_categories()
    
    # 3. Test analytics
    analytics_success, analytics_data = tester.test_get_analytics()
    
    # 4. Test conversations
    conversations_success, conversations_data = tester.test_get_conversations()
    
    # 5. Test message analysis (will likely fail without valid contact_id)
    analyze_success, analyze_data = tester.test_analyze_message()
    
    # 6. Test send messages (expected to fail without credentials)
    send_success, send_data = tester.test_send_messages()
    
    # Print summary
    print(f"\n📊 Test Results Summary")
    print("=" * 50)
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    # Print detailed results
    print(f"\n📋 Detailed Results:")
    for result in tester.results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['test']}: {result['actual_status']} (expected {result['expected_status']})")
        if not result["success"]:
            print(f"   Error: {result['response_preview']}")
    
    # Critical issues check
    critical_failures = []
    if not excel_success:
        critical_failures.append("Excel import functionality broken")
    if not categories_success:
        critical_failures.append("Categories endpoint not working")
    if not analytics_success:
        critical_failures.append("Analytics endpoint not working")
    
    if len(critical_failures) > 0:
        print(f"\n🚨 Critical Issues Found:")
        for issue in critical_failures:
            print(f"   - {issue}")
        return 1
    
    print(f"\n✅ Core backend functionality is working!")
    print(f"Note: Send/Analyze failures are expected without proper credentials/data")
    
    return 0 if tester.tests_passed >= 3 else 1  # At least 3 core tests should pass

if __name__ == "__main__":
    sys.exit(main())