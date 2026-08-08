import os
from app import create_app

app = create_app()
app.testing = True

def run_tests():
    with app.test_client() as client:
        # Test 1: Health endpoint should be allowed without auth
        response = client.get('/health')
        print(f"Health Check: {response.status_code}")
        assert response.status_code == 200

        # Test 2: Protected endpoint should fail without auth
        response = client.get('/get_consultation_history/1')
        print(f"Protected Check (No Auth): {response.status_code}")
        assert response.status_code == 401
        
        # Test 3: Protected endpoint with correct API key
        api_key = os.environ.get("X_API_KEY", "your_secure_api_key_here")
        response = client.get('/get_consultation_history/1', headers={'x-api-key': api_key})
        print(f"Protected Check (API Key): {response.status_code}")
        # Could be 400 or 404 depending on logic, but not 401
        assert response.status_code != 401
        
        print("All tests passed!")

if __name__ == '__main__':
    run_tests()

