"""
Test script for GNAF Flask Web Application
Tests API endpoints and database connectivity
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_endpoint(endpoint, description):
    """Test a single endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"URL: {BASE_URL}{endpoint}")
    print('='*60)
    
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ SUCCESS")
            print(f"Response preview:")
            print(json.dumps(data, indent=2)[:500])
            return True
        else:
            print(f"✗ FAILED")
            print(f"Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"✗ FAILED - Cannot connect to server")
        print(f"Make sure Flask app is running at {BASE_URL}")
        return False
    except Exception as e:
        print(f"✗ FAILED - {str(e)}")
        return False


def main():
    print("\n" + "="*60)
    print("GNAF Web Application Test Suite")
    print("="*60)
    
    tests = [
        ("/", "Home Page"),
        ("/api/stats", "Database Statistics"),
        ("/api/search/suburbs?postcode=2000", "Search Suburbs by Postcode (2000)"),
        ("/api/search/postcodes?suburb=Sydney", "Search Postcodes by Suburb (Sydney)"),
        ("/api/autocomplete/suburbs?q=Syd", "Autocomplete Suburbs (Syd)"),
    ]
    
    results = []
    for endpoint, description in tests:
        result = test_endpoint(endpoint, description)
        results.append((description, result))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for description, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {description}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Web application is working correctly.")
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Check the output above for details.")


if __name__ == "__main__":
    main()
