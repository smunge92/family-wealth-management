"""
Tests for Family Members API - User Creation, Error Handling, and Edge Cases

Tests cover:
1. User info available from token - user created/updated, family member created
2. User info None but user exists in DB - family member created
3. User info None and user NOT in DB - returns USER_NOT_FOUND error
4. Foreign key constraint violation - returns FK_VIOLATION error
5. Unique constraint violation (duplicate name) - returns specific error
6. Validation errors (missing required fields)
7. GET family members
8. DELETE family member
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
import azure.functions as func


class TestCreateFamilyMemberWithUserInfo:
    """Test family member creation when user info is available from token"""

    @pytest.fixture
    def mock_request_with_user_info(self):
        """Create a mock request with user_info attached"""
        req = Mock(spec=func.HttpRequest)
        req.method = "POST"
        req.get_json.return_value = {
            "user_id": "test-user-123",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com"
        }
        req.user_info = {
            "user_id": "test-user-123",
            "email": "auth@example.com",
            "first_name": "Auth",
            "last_name": "User"
        }
        return req

    @pytest.mark.asyncio
    @patch('functions.api.family_members.get_db_manager')
    @patch('functions.api.family_members.validate_user_access')
    @patch('functions.api.family_members.get_user_from_request')
    async def test_creates_user_when_user_info_available(self, mock_get_user, mock_validate, mock_get_db, mock_request_with_user_info):
        """When user_info is available, user should be created/updated in database"""
        # Setup mocks
        mock_validate.return_value = (True, None)
        mock_get_user.return_value = mock_request_with_user_info.user_info

        mock_db = MagicMock()
        mock_db.create_or_update_user.return_value = {"user_id": "test-user-123"}
        mock_db.create_family_member.return_value = {
            "family_member_id": 1,
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "is_primary": False,
            "created_at": "2024-01-01"
        }
        mock_get_db.return_value = mock_db

        # Import and call the function
        from functions.api.family_members import _create_family_member

        headers = {"Access-Control-Allow-Origin": "*"}
        response = await _create_family_member(mock_request_with_user_info, headers)

        # Verify user was created
        mock_db.create_or_update_user.assert_called_once_with(
            user_id="test-user-123",
            email="auth@example.com",
            first_name="Auth",
            last_name="User"
        )

        # Verify family member was created
        mock_db.create_family_member.assert_called_once()
        assert response.status_code == 201


class TestCreateFamilyMemberNoUserInfo:
    """Test family member creation when user info is NOT available from token"""

    @pytest.fixture
    def mock_request_no_user_info(self):
        """Create a mock request without user_info"""
        req = Mock(spec=func.HttpRequest)
        req.method = "POST"
        req.get_json.return_value = {
            "user_id": "test-user-123",
            "first_name": "John",
            "last_name": "Doe"
        }
        req.user_info = None
        return req

    @pytest.mark.asyncio
    @patch('functions.api.family_members.get_db_manager')
    @patch('functions.api.family_members.validate_user_access')
    @patch('functions.api.family_members.get_user_from_request')
    async def test_succeeds_when_user_exists_in_db(self, mock_get_user, mock_validate, mock_get_db, mock_request_no_user_info):
        """When user_info is None but user exists in DB, family member creation should succeed"""
        mock_validate.return_value = (True, None)
        mock_get_user.return_value = None  # No user info from request

        mock_db = MagicMock()
        mock_db.get_user.return_value = {"user_id": "test-user-123", "email": "existing@example.com"}
        mock_db.create_family_member.return_value = {
            "family_member_id": 1,
            "first_name": "John",
            "last_name": "Doe",
            "is_primary": False
        }
        mock_get_db.return_value = mock_db

        from functions.api.family_members import _create_family_member

        headers = {"Access-Control-Allow-Origin": "*"}
        response = await _create_family_member(mock_request_no_user_info, headers)

        # Verify user existence was checked
        mock_db.get_user.assert_called_once_with("test-user-123")

        # Verify create_or_update_user was NOT called (user_info was None)
        mock_db.create_or_update_user.assert_not_called()

        # Verify family member was created
        mock_db.create_family_member.assert_called_once()
        assert response.status_code == 201

    @pytest.mark.asyncio
    @patch('functions.api.family_members.get_db_manager')
    @patch('functions.api.family_members.validate_user_access')
    @patch('functions.api.family_members.get_user_from_request')
    async def test_fails_with_user_not_found_when_user_missing(self, mock_get_user, mock_validate, mock_get_db, mock_request_no_user_info):
        """When user_info is None and user doesn't exist in DB, should return USER_NOT_FOUND error"""
        mock_validate.return_value = (True, None)
        mock_get_user.return_value = None  # No user info from request

        mock_db = MagicMock()
        mock_db.get_user.return_value = None  # User doesn't exist in DB
        mock_get_db.return_value = mock_db

        from functions.api.family_members import _create_family_member

        headers = {"Access-Control-Allow-Origin": "*"}
        response = await _create_family_member(mock_request_no_user_info, headers)

        # Verify error response
        assert response.status_code == 400
        response_body = json.loads(response.get_body())
        assert response_body["code"] == "USER_NOT_FOUND"
        assert "sign out and sign back in" in response_body["error"].lower()


class TestForeignKeyConstraintViolation:
    """Test handling of foreign key constraint violations"""

    @pytest.fixture
    def mock_request(self):
        req = Mock(spec=func.HttpRequest)
        req.method = "POST"
        req.get_json.return_value = {
            "user_id": "test-user-123",
            "first_name": "John",
            "last_name": "Doe"
        }
        req.user_info = {"user_id": "test-user-123", "email": "test@example.com"}
        return req

    @pytest.mark.asyncio
    @patch('functions.api.family_members.get_db_manager')
    @patch('functions.api.family_members.validate_user_access')
    @patch('functions.api.family_members.get_user_from_request')
    async def test_handles_fk_constraint_violation(self, mock_get_user, mock_validate, mock_get_db, mock_request):
        """Foreign key constraint violation should return FK_VIOLATION error"""
        mock_validate.return_value = (True, None)
        mock_get_user.return_value = mock_request.user_info

        mock_db = MagicMock()
        mock_db.create_or_update_user.return_value = {"user_id": "test-user-123"}
        # Simulate FK constraint violation
        mock_db.create_family_member.side_effect = Exception(
            "The INSERT statement conflicted with the FOREIGN KEY constraint \"FK_family_members_user\""
        )
        mock_get_db.return_value = mock_db

        from functions.api.family_members import _create_family_member

        headers = {"Access-Control-Allow-Origin": "*"}
        response = await _create_family_member(mock_request, headers)

        assert response.status_code == 400
        response_body = json.loads(response.get_body())
        assert response_body["code"] == "FK_VIOLATION"
        assert "sign out and sign back in" in response_body["error"].lower()


class TestUniqueConstraintViolation:
    """Test handling of unique constraint violations (duplicate family member name)"""

    @pytest.fixture
    def mock_request(self):
        req = Mock(spec=func.HttpRequest)
        req.method = "POST"
        req.get_json.return_value = {
            "user_id": "test-user-123",
            "first_name": "John",
            "last_name": "Doe"
        }
        req.user_info = {"user_id": "test-user-123", "email": "test@example.com"}
        return req

    @pytest.mark.asyncio
    @patch('functions.api.family_members.get_db_manager')
    @patch('functions.api.family_members.validate_user_access')
    @patch('functions.api.family_members.get_user_from_request')
    async def test_handles_duplicate_name_error(self, mock_get_user, mock_validate, mock_get_db, mock_request):
        """Duplicate family member name should return specific error"""
        mock_validate.return_value = (True, None)
        mock_get_user.return_value = mock_request.user_info

        mock_db = MagicMock()
        mock_db.create_or_update_user.return_value = {"user_id": "test-user-123"}
        # Simulate unique constraint violation
        mock_db.create_family_member.side_effect = Exception(
            "Violation of UNIQUE KEY constraint 'UQ_family_member_name'"
        )
        mock_get_db.return_value = mock_db

        from functions.api.family_members import _create_family_member

        headers = {"Access-Control-Allow-Origin": "*"}
        response = await _create_family_member(mock_request, headers)

        assert response.status_code == 409
        response_body = json.loads(response.get_body())
        assert "already exists" in response_body["error"].lower()


class TestValidationErrors:
    """Test input validation for family member creation"""

    @pytest.mark.asyncio
    async def test_missing_user_id(self):
        """Missing user_id should return validation error"""
        req = Mock(spec=func.HttpRequest)
        req.method = "POST"
        req.get_json.return_value = {
            "first_name": "John",
            "last_name": "Doe"
        }

        from functions.api.family_members import _create_family_member

        headers = {"Access-Control-Allow-Origin": "*"}
        response = await _create_family_member(req, headers)

        assert response.status_code == 400
        response_body = json.loads(response.get_body())
        assert "user_id" in response_body["error"].lower()

    @pytest.mark.asyncio
    async def test_missing_first_name(self):
        """Missing first_name should return validation error"""
        req = Mock(spec=func.HttpRequest)
        req.method = "POST"
        req.get_json.return_value = {
            "user_id": "test-user-123",
            "last_name": "Doe"
        }

        from functions.api.family_members import _create_family_member

        headers = {"Access-Control-Allow-Origin": "*"}
        response = await _create_family_member(req, headers)

        assert response.status_code == 400
        response_body = json.loads(response.get_body())
        assert "first_name" in response_body["error"].lower()

    @pytest.mark.asyncio
    async def test_missing_last_name(self):
        """Missing last_name should return validation error"""
        req = Mock(spec=func.HttpRequest)
        req.method = "POST"
        req.get_json.return_value = {
            "user_id": "test-user-123",
            "first_name": "John"
        }

        from functions.api.family_members import _create_family_member

        headers = {"Access-Control-Allow-Origin": "*"}
        response = await _create_family_member(req, headers)

        assert response.status_code == 400
        response_body = json.loads(response.get_body())
        assert "last_name" in response_body["error"].lower()

    @pytest.mark.asyncio
    async def test_invalid_email_format(self):
        """Invalid email format should return validation error"""
        req = Mock(spec=func.HttpRequest)
        req.method = "POST"
        req.get_json.return_value = {
            "user_id": "test-user-123",
            "first_name": "John",
            "last_name": "Doe",
            "email": "not-an-email"
        }

        from functions.api.family_members import _create_family_member

        headers = {"Access-Control-Allow-Origin": "*"}
        response = await _create_family_member(req, headers)

        assert response.status_code == 400
        response_body = json.loads(response.get_body())
        assert "email" in response_body["error"].lower()

    @pytest.mark.asyncio
    async def test_empty_first_name(self):
        """Empty first_name should return validation error"""
        req = Mock(spec=func.HttpRequest)
        req.method = "POST"
        req.get_json.return_value = {
            "user_id": "test-user-123",
            "first_name": "",
            "last_name": "Doe"
        }

        from functions.api.family_members import _create_family_member

        headers = {"Access-Control-Allow-Origin": "*"}
        response = await _create_family_member(req, headers)

        assert response.status_code == 400


class TestGetFamilyMembers:
    """Test GET family members endpoint"""

    @pytest.mark.asyncio
    @patch('functions.api.family_members.get_db_manager')
    @patch('functions.api.family_members.validate_user_access')
    async def test_returns_family_members_list(self, mock_validate, mock_get_db):
        """GET should return list of family members"""
        mock_validate.return_value = (True, None)

        mock_db = MagicMock()
        mock_db.get_family_members_by_user.return_value = [
            {"family_member_id": 1, "first_name": "John", "last_name": "Doe", "is_primary": True},
            {"family_member_id": 2, "first_name": "Jane", "last_name": "Doe", "is_primary": False}
        ]
        mock_get_db.return_value = mock_db

        req = Mock(spec=func.HttpRequest)
        req.method = "GET"
        req.params = {"user_id": "test-user-123"}

        from functions.api.family_members import _get_family_members

        headers = {"Access-Control-Allow-Origin": "*"}
        response = await _get_family_members(req, headers)

        assert response.status_code == 200
        response_body = json.loads(response.get_body())
        assert "family_members" in response_body
        assert len(response_body["family_members"]) == 2

    @pytest.mark.asyncio
    async def test_missing_user_id_returns_error(self):
        """GET without user_id should return error"""
        req = Mock(spec=func.HttpRequest)
        req.method = "GET"
        req.params = {}

        from functions.api.family_members import _get_family_members

        headers = {"Access-Control-Allow-Origin": "*"}
        response = await _get_family_members(req, headers)

        assert response.status_code == 400
        response_body = json.loads(response.get_body())
        assert "user_id" in response_body["error"]


class TestDeleteFamilyMember:
    """Test DELETE family member endpoint"""

    @pytest.mark.asyncio
    @patch('functions.api.family_members.get_db_manager')
    @patch('functions.api.family_members.validate_user_access')
    @patch('shared.auth.is_auth_required')
    async def test_successful_delete(self, mock_auth_required, mock_validate, mock_get_db):
        """DELETE should return success with deletion stats"""
        mock_auth_required.return_value = False  # Skip auth for testing
        mock_validate.return_value = (True, None)

        mock_db = MagicMock()
        mock_db.get_family_member.return_value = {
            "family_member_id": 1,
            "user_id": "test-user-123",
            "first_name": "John",
            "last_name": "Doe"
        }
        mock_db.delete_family_member.return_value = {
            "deleted": True,
            "accounts_deleted": 2,
            "transactions_deleted": 50,
            "balances_deleted": 10
        }
        mock_get_db.return_value = mock_db

        req = Mock(spec=func.HttpRequest)
        req.method = "DELETE"
        req.route_params = {"family_member_id": "1"}
        req.params = {}
        req.headers = {"Authorization": ""}

        from functions.api.family_members import delete_family_member

        response = await delete_family_member(req)

        assert response.status_code == 200
        response_body = json.loads(response.get_body())
        assert response_body["success"] is True
        assert "deleted_data" in response_body

    @pytest.mark.asyncio
    @patch('functions.api.family_members.get_db_manager')
    @patch('shared.auth.is_auth_required')
    async def test_delete_nonexistent_member(self, mock_auth_required, mock_get_db):
        """DELETE non-existent member should return 404"""
        mock_auth_required.return_value = False  # Skip auth for testing

        mock_db = MagicMock()
        mock_db.get_family_member.return_value = None
        mock_get_db.return_value = mock_db

        req = Mock(spec=func.HttpRequest)
        req.method = "DELETE"
        req.route_params = {"family_member_id": "999"}
        req.params = {}
        req.headers = {"Authorization": ""}

        from functions.api.family_members import delete_family_member

        response = await delete_family_member(req)

        assert response.status_code == 404


class TestGenericErrorHandling:
    """Test generic error handling"""

    @pytest.fixture
    def mock_request(self):
        req = Mock(spec=func.HttpRequest)
        req.method = "POST"
        req.get_json.return_value = {
            "user_id": "test-user-123",
            "first_name": "John",
            "last_name": "Doe"
        }
        req.user_info = {"user_id": "test-user-123", "email": "test@example.com"}
        return req

    @pytest.mark.asyncio
    @patch('functions.api.family_members.get_db_manager')
    @patch('functions.api.family_members.validate_user_access')
    @patch('functions.api.family_members.get_user_from_request')
    async def test_generic_database_error(self, mock_get_user, mock_validate, mock_get_db, mock_request):
        """Generic database error should return 500 with generic message"""
        mock_validate.return_value = (True, None)
        mock_get_user.return_value = mock_request.user_info

        mock_db = MagicMock()
        mock_db.create_or_update_user.return_value = {"user_id": "test-user-123"}
        mock_db.create_family_member.side_effect = Exception("Connection timeout")
        mock_get_db.return_value = mock_db

        from functions.api.family_members import _create_family_member

        headers = {"Access-Control-Allow-Origin": "*"}
        response = await _create_family_member(mock_request, headers)

        assert response.status_code == 500
        response_body = json.loads(response.get_body())
        assert "Failed to create family member" in response_body["error"]


class TestUserAccessValidation:
    """Test that user access validation is enforced"""

    @pytest.mark.asyncio
    @patch('functions.api.family_members.validate_user_access')
    async def test_access_denied_returns_error(self, mock_validate):
        """When user access validation fails, should return the error response"""
        error_response = func.HttpResponse(
            json.dumps({"error": "Access denied"}),
            status_code=403,
            mimetype="application/json"
        )
        mock_validate.return_value = (False, error_response)

        req = Mock(spec=func.HttpRequest)
        req.method = "POST"
        req.get_json.return_value = {
            "user_id": "different-user-456",
            "first_name": "John",
            "last_name": "Doe"
        }

        from functions.api.family_members import _create_family_member

        headers = {"Access-Control-Allow-Origin": "*"}
        response = await _create_family_member(req, headers)

        assert response.status_code == 403


class TestOptionsRequest:
    """Test OPTIONS preflight request handling"""

    @pytest.mark.asyncio
    async def test_options_returns_204(self):
        """OPTIONS request should return 204 with CORS headers"""
        req = Mock(spec=func.HttpRequest)
        req.method = "OPTIONS"
        req.headers = {}

        from functions.api.family_members import family_members_handler

        response = await family_members_handler(req)

        assert response.status_code == 204


class TestFamilyMemberIsPrimary:
    """Test is_primary flag handling"""

    @pytest.mark.asyncio
    @patch('functions.api.family_members.get_db_manager')
    @patch('functions.api.family_members.validate_user_access')
    @patch('functions.api.family_members.get_user_from_request')
    async def test_creates_primary_family_member(self, mock_get_user, mock_validate, mock_get_db):
        """Should correctly pass is_primary flag to database"""
        mock_validate.return_value = (True, None)
        mock_get_user.return_value = {"user_id": "test-user-123", "email": "test@example.com"}

        mock_db = MagicMock()
        mock_db.create_or_update_user.return_value = {"user_id": "test-user-123"}
        mock_db.create_family_member.return_value = {
            "family_member_id": 1,
            "first_name": "John",
            "last_name": "Doe",
            "is_primary": True
        }
        mock_get_db.return_value = mock_db

        req = Mock(spec=func.HttpRequest)
        req.method = "POST"
        req.get_json.return_value = {
            "user_id": "test-user-123",
            "first_name": "John",
            "last_name": "Doe",
            "is_primary": True
        }
        req.user_info = {"user_id": "test-user-123", "email": "test@example.com"}

        from functions.api.family_members import _create_family_member

        headers = {"Access-Control-Allow-Origin": "*"}
        response = await _create_family_member(req, headers)

        # Verify is_primary was passed correctly
        mock_db.create_family_member.assert_called_once()
        call_kwargs = mock_db.create_family_member.call_args[1]
        assert call_kwargs["is_primary"] is True
        assert response.status_code == 201
