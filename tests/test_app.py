"""
Tests for Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original participants
    original_state = {}
    for activity_name, details in activities.items():
        original_state[activity_name] = details["participants"].copy()
    
    yield
    
    # Restore original participants after test
    for activity_name, details in activities.items():
        details["participants"] = original_state[activity_name]


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data

    def test_activity_has_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, details in data.items():
            assert "description" in details
            assert "schedule" in details
            assert "max_participants" in details
            assert "participants" in details
            assert isinstance(details["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_for_activity_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]

    def test_signup_adds_participant(self, client, reset_activities):
        """Test that signup actually adds participant to activity"""
        email = "newstudent@mergington.edu"
        response = client.post(
            f"/activities/Chess%20Club/signup?email={email}"
        )
        assert response.status_code == 200
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Chess Club"]["participants"]

    def test_signup_duplicate_student_fails(self, client, reset_activities):
        """Test that a student cannot sign up twice for the same activity"""
        email = "duplicate@mergington.edu"
        
        # First signup succeeds
        response1 = client.post(
            f"/activities/Chess%20Club/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Second signup fails
        response2 = client.post(
            f"/activities/Chess%20Club/signup?email={email}"
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"].lower() or \
               "student is already" in response2.json()["detail"].lower()

    def test_signup_nonexistent_activity_fails(self, client):
        """Test that signup for nonexistent activity fails"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_signup_full_activity_fails(self, client, reset_activities):
        """Test that signup fails when activity is full"""
        # Get an activity with limited spots
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        # Find an activity close to capacity
        full_activity = None
        for name, details in activities_data.items():
            spots_left = details["max_participants"] - len(details["participants"])
            if spots_left == 1:
                full_activity = name
                break
        
        if full_activity:
            # Fill the last spot
            response = client.post(
                f"/activities/{full_activity.replace(' ', '%20')}/signup?"
                f"email=filltolast@mergington.edu"
            )
            assert response.status_code == 200
            
            # Try to signup when full
            response2 = client.post(
                f"/activities/{full_activity.replace(' ', '%20')}/signup?"
                f"email=trytooverflow@mergington.edu"
            )
            assert response2.status_code == 400
            assert "full" in response2.json()["detail"].lower()


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistration from activity"""
        # First signup
        email = "unregister@mergington.edu"
        client.post(f"/activities/Chess%20Club/signup?email={email}")
        
        # Then unregister
        response = client.delete(
            f"/activities/Chess%20Club/unregister?email={email}"
        )
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]

    def test_unregister_removes_participant(self, client, reset_activities):
        """Test that unregister actually removes participant"""
        email = "removetest@mergington.edu"
        
        # Signup
        client.post(f"/activities/Programming%20Class/signup?email={email}")
        
        # Unregister
        response = client.delete(
            f"/activities/Programming%20Class/unregister?email={email}"
        )
        assert response.status_code == 200
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Programming Class"]["participants"]

    def test_unregister_not_signed_up_fails(self, client):
        """Test that unregister fails if student not signed up"""
        response = client.delete(
            "/activities/Tennis%20Team/unregister?email=notsignedup@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"].lower()

    def test_unregister_nonexistent_activity_fails(self, client):
        """Test that unregister from nonexistent activity fails"""
        response = client.delete(
            "/activities/Fake%20Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestRedirect:
    """Tests for root endpoint redirect"""

    def test_root_redirects_to_index(self, client):
        """Test that root path redirects to index.html"""
        response = client.get("/", follow_redirects=True)
        assert response.status_code == 200
