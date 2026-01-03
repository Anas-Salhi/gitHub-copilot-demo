"""
Tests for the Mergington High School API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test"""
    activities.clear()
    activities.update({
        "Soccer Team": {
            "description": "Join the school soccer team and compete in inter-school matches",
            "schedule": "Tuesdays and Thursdays, 4:00 PM - 6:00 PM",
            "max_participants": 25,
            "participants": ["alex@mergington.edu", "sarah@mergington.edu"]
        },
        "Basketball Club": {
            "description": "Practice basketball skills and play in tournaments",
            "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
            "max_participants": 20,
            "participants": ["david@mergington.edu", "emily@mergington.edu"]
        },
        "Drama Club": {
            "description": "Participate in theater productions and improve acting skills",
            "schedule": "Wednesdays, 3:30 PM - 5:30 PM",
            "max_participants": 25,
            "participants": ["james@mergington.edu", "lisa@mergington.edu"]
        },
    })


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_index(self, client):
        """Test that root redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that get_activities returns all available activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        assert "Soccer Team" in data
        assert "Basketball Club" in data
        assert "Drama Club" in data
        
    def test_get_activities_structure(self, client):
        """Test that each activity has the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        soccer_team = data["Soccer Team"]
        assert "description" in soccer_team
        assert "schedule" in soccer_team
        assert "max_participants" in soccer_team
        assert "participants" in soccer_team
        assert isinstance(soccer_team["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_new_participant(self, client):
        """Test signing up a new participant for an activity"""
        response = client.post(
            "/activities/Soccer Team/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Soccer Team" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Soccer Team"]["participants"]
    
    def test_signup_duplicate_participant(self, client):
        """Test that signing up an already registered participant fails"""
        response = client.post(
            "/activities/Soccer Team/signup?email=alex@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_nonexistent_activity(self, client):
        """Test that signing up for a non-existent activity fails"""
        response = client.post(
            "/activities/NonExistent Activity/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_signup_url_encoded_activity_name(self, client):
        """Test signing up with URL-encoded activity name"""
        response = client.post(
            "/activities/Soccer%20Team/signup?email=another@mergington.edu"
        )
        assert response.status_code == 200


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant from an activity"""
        # First verify the participant exists
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "alex@mergington.edu" in activities_data["Soccer Team"]["participants"]
        
        # Unregister the participant
        response = client.delete(
            "/activities/Soccer Team/unregister?email=alex@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "alex@mergington.edu" in data["message"]
        assert "Soccer Team" in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "alex@mergington.edu" not in activities_data["Soccer Team"]["participants"]
    
    def test_unregister_non_registered_participant(self, client):
        """Test that unregistering a non-registered participant fails"""
        response = client.delete(
            "/activities/Soccer Team/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"].lower()
    
    def test_unregister_from_nonexistent_activity(self, client):
        """Test that unregistering from a non-existent activity fails"""
        response = client.delete(
            "/activities/NonExistent Activity/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_unregister_url_encoded_activity_name(self, client):
        """Test unregistering with URL-encoded activity name"""
        response = client.delete(
            "/activities/Soccer%20Team/unregister?email=alex@mergington.edu"
        )
        assert response.status_code == 200


class TestIntegrationScenarios:
    """Integration tests for combined operations"""
    
    def test_signup_and_unregister_flow(self, client):
        """Test the complete flow of signing up and then unregistering"""
        email = "testflow@mergington.edu"
        activity = "Basketball Club"
        
        # Get initial participant count
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        
        # Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify participant was added
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
        assert len(response.json()[activity]["participants"]) == initial_count + 1
        
        # Unregister
        unregister_response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Verify participant was removed
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]
        assert len(response.json()[activity]["participants"]) == initial_count
    
    def test_multiple_activities_signup(self, client):
        """Test signing up for multiple activities"""
        email = "multisport@mergington.edu"
        
        # Sign up for Soccer Team
        response1 = client.post(f"/activities/Soccer Team/signup?email={email}")
        assert response1.status_code == 200
        
        # Sign up for Basketball Club
        response2 = client.post(f"/activities/Basketball Club/signup?email={email}")
        assert response2.status_code == 200
        
        # Sign up for Drama Club
        response3 = client.post(f"/activities/Drama Club/signup?email={email}")
        assert response3.status_code == 200
        
        # Verify participant is in all three activities
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        assert email in activities_data["Soccer Team"]["participants"]
        assert email in activities_data["Basketball Club"]["participants"]
        assert email in activities_data["Drama Club"]["participants"]
