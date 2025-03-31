# from fastapi.testclient import TestClient
# import pytest


# @pytest.mark.usefixtures("client")
# class TestAuth:
#     def test_create_role_with_user_token(self, client: TestClient):
#         """Test forbidden access to the POST /roles endpoint with user token to check if user cannot create a role."""
#         response = client.post_without_permissions(url="/roles", json={"role": "new-role", "default": False, "admin": False, "limits": []})
#         assert response.status_code == 403, response.text

#     def test_create_already_existing_role_with_user_token(self, client: TestClient):
#         """Test forbidden access to the POST /roles endpoint with user token to check if user cannot create a role that already exists, instead getting a 400."""
#         response = client.post_without_permissions(url="/roles", json={"role": "test-role-user", "default": False, "admin": False, "limits": []})
#         assert response.status_code == 403, response.text

#     def test_update_role_with_user_token(self, client: TestClient):
#         """Test forbidden access to the PATCH /roles endpoint with user token to check if user cannot update a role."""
#         response = client.patch_without_permissions(url="/roles/test-role-user", json={"role": "test-role-user", "default": False, "admin": True, "limits": []})
#         assert response.status_code == 403, response.text

#     def test_update_inexistent_role_with_user_token(self, client: TestClient):
#         """Test forbidden access to the PATCH /roles endpoint with user token to check if the user cannot update a inexistent role instead getting a 404."""
#         response = client.patch_without_permissions(url="/roles/inexistent-role", json={"role": "inexistent-role", "default": False, "admin": False, "limits": []})
#         assert response.status_code == 403, response.text

#     def test_delete_role_with_user_token(self, client: TestClient):
#         """Test the DELETE /roles endpoint with user token to check if user cannot delete a role."""
#         response = client.delete_without_permissions(url="/roles/test-role-user")
#         assert response.status_code == 403, response.text

#     def test_delete_inexistent_role_with_user_token(self, client: TestClient):
#         """Test forbidden access to the DELETE /roles endpoint with user token to check if the user cannot delete a inexistent role instead getting a 404."""
#         response = client.delete_without_permissions(url="/roles/inexistent-role")
#         assert response.status_code == 403, response.text

#     def test_create_user_with_user_token(self, client: TestClient):
#         """Test forbidden access to the POST /users endpoint with user token to check if user cannot create a user."""
#         response = client.post_without_permissions(url="/users", json={"user": "new-user", "password": "test-password", "role": "test-role-user"})
#         assert response.status_code == 403, response.text

#     def test_create_already_existing_user_with_user_token(self, client: TestClient):
#         """Test forbidden access to the POST /users endpoint with user token to check if user cannot create a user that already exists, instead getting a 400."""
#         response = client.post_without_permissions(url="/users", json={"user": "test-user-user", "password": "test-password", "role": "test-role-user"})
#         assert response.status_code == 403, response.text

#     def test_create_inexistent_user_with_user_token(self, client: TestClient):
#         """Test forbidden access to the POST /users endpoint with user token to check if user cannot create a user with inexistent role instead getting a 404."""
#         response = client.post_without_permissions(url="/users", json={"user": "new-user", "password": "test-password", "role": "inexistent-role"})
#         assert response.status_code == 403, response.text

#     def test_update_user_with_user_token(self, client: TestClient):
#         """Test forbidden access to the PATCH /users endpoint with user token to check if user cannot update a user."""
#         response = client.patch_without_permissions(
#             url="/users/test-user-user", json={"user": "test-user-user", "password": "test-password", "role": "test-role-user"}
#         )
#         assert response.status_code == 403, response.text

#     def test_update_inexistent_user_with_user_token(self, client: TestClient):
#         """Test forbidden access to the PATCH /users endpoint with user token to check if the user cannot update a inexistent user instead getting a 404."""
#         response = client.patch_without_permissions(
#             url="/users/inexistent-user", json={"user": "inexistent-user", "password": "test-password", "role": "test-role-user"}
#         )
#         assert response.status_code == 403, response.text

#     def test_delete_without_permissions_with_user_token(self, client: TestClient):
#         """Test forbidden access to the DELETE /users endpoint with user token to check if user cannot delete a user."""
#         response = client.delete_without_permissions(url="/users/test-user-user")
#         assert response.status_code == 403, response.text

#     def test_delete_inexistent_user_with_user_token(self, client: TestClient):
#         """Test forbidden access to the DELETE /users endpoint with user token to check if the user cannot delete a inexistent user instead getting a 404."""
#         response = client.delete_without_permissions(url="/users/inexistent-user")
#         assert response.status_code == 403, response.text

#     def test_create_token_with_user_token(self, client: TestClient):
#         """Test forbidden access to the POST /tokens endpoint with user token to check if user cannot create a token."""
#         response = client.post_without_permissions(url="/tokens", json={"user": "test-user-user", "token": "test-token"})
#         assert response.status_code == 403, response.text

#     def test_create_token_with_inexistent_user_token(self, client: TestClient):
#         """Test forbidden access to the POST /tokens endpoint with user token to check if user cannot create a token with inexistent user instead getting a 404."""
#         response = client.post_without_permissions(url="/tokens", json={"user": "inexistent-user", "token": "test-token"})
#         assert response.status_code == 403, response.text

#     def test_delete_token_with_user_token(self, client: TestClient):
#         """Test forbidden access to the DELETE /tokens endpoint with user token to check if user cannot delete a token."""
#         response = client.delete_without_permissions(url="/tokens/test-user-user/test-token-user")
#         assert response.status_code == 403, response.text

#     def test_delete_inexistent_token_with_user_token(self, client: TestClient):
#         """Test forbidden access to the DELETE /tokens endpoint with user token to check if the user cannot delete a inexistent token instead getting a 404."""
#         response = client.delete_without_permissions(url="/tokens/test-user-user/inexistent-token")
#         assert response.status_code == 403, response.text

#     def test_create_user_with_user_token_and_root_role(self, client: TestClient):
#         """Test forbidden access to the POST /users endpoint with user token to check if user cannot create a user with root role."""
#         response = client.post_without_permissions(url="/users", json={"user": "test-user", "password": "test-password", "role": "root"})
#         assert response.status_code == 403, response.text

#     def test_create_role_with_admin_token(self, client: TestClient):
#         """Test the POST /roles endpoint with admin token to check response code and text."""
#         response = client.post_with_permissions(url="/roles", json={"role": "test-role", "default": False, "admin": False, "limits": []})
#         assert response.status_code == 201, response.text
#         assert response.json()["id"] == "test-role"

#     def test_update_role_with_admin_token(self, client: TestClient):
#         """Test the PATCH /roles endpoint with admin token to check if role is updated."""
#         response = client.patch_with_permissions(url="/roles/test-role", json={"role": "test-role", "default": False, "admin": True, "limits": []})
#     assert response.status_code == 201, response.text

#     response = client.get_with_permissions(url="/roles/test-role")
#     assert response.status_code == 200, response.text
#     assert response.json()["admin"] is True

# def test_delete_role_with_admin_token(self, client: TestClient):
#     """Test the DELETE /roles endpoint with admin token to check if role is deleted."""
#     response = client.delete_with_permissions(url="/roles/test-role")
#     assert response.status_code == 204, response.text

#     response = client.get_with_permissions(url="/roles/test-role")
#     assert response.status_code == 404, response.text

# def test_delete_inexistent_role_with_admin_token(self, client: TestClient):
#     """Test the DELETE /roles endpoint with admin token to check if inexistent role is not deleted."""
#     response = client.delete_with_permissions(url="/roles/inexistent-role")
#     assert response.status_code == 404, response.text

# def test_update_inexistent_role_with_admin_token(self, client: TestClient):
#     """Test the PATCH /roles endpoint with admin token to check if inexistent role is not updated."""
#     response = client.patch_with_permissions(url="/roles/inexistent-role", json={"role": "inexistent-role", "default": False, "admin": False, "limits": []})
#     assert response.status_code == 404, response.text

# def test_delete_root_role_with_admin_token(self, client: TestClient):
#     """Test the DELETE /roles endpoint with admin token to check if root role cannot be deleted."""
#     response = client.delete_with_permissions(url="/roles/root")
#     assert response.status_code == 403, response.text

# def test_delete_default_role_with_admin_token(self, client: TestClient):
#     """Test the DELETE /roles endpoint with admin token to check if default role cannot be deleted without a new default role."""
#     response = client.delete_with_permissions(url="/roles/default")
#     assert response.status_code == 403, response.text

# def test_delete_role_with_users(self, client: TestClient):
#     """Test the DELETE /roles endpoint with admin token to check if role with users cannot be deleted."""

#     # add a user to the role
#     response = client.post_with_permissions(url="/users", json={"user": "test-user", "password": "test-password", "role": "test-role"})
#     assert response.status_code == 201, response.text

#     # delete the role
#     response = client.delete_with_permissions(url="/roles/test-role")
#     assert response.status_code == 403, response.text

#     # delete the user
#     response = client.delete_with_permissions(url="/users/test-user")
#     assert response.status_code == 204, response.text

#     # delete the role
#     response = client.delete_with_permissions(url="/roles/test-role")
#     assert response.status_code == 204, response.text

# def test_remove_default_role_from_user_with_admin_token(self, client: TestClient):
#     """Test the PATCH /roles endpoint with admin token to remove default role from user. Default role cannot be removed without a new default role."""
#     response = client.patch_with_permissions(url="/roles/test-role", json={"role": "test-role", "default": False, "admin": False, "limits": []})
#     assert response.status_code == 400, response.text

# def test_update_default_role_with_admin_token(self, client: TestClient):
#     """Test the PATCH /roles endpoint with admin token."""

#     response = client.post_with_permissions(url="/roles", json={"role": "test-role", "default": False, "admin": False, "limits": []})
#     assert response.status_code == 201, response.text

#     response = client.patch_with_permissions(url="/roles/test-role", json={"role": "test-role", "default": True, "admin": False, "limits": []})
#     assert response.status_code == 201, response.text

#     response = client.post_with_permissions(url="/users", json={"user": "test-user", "password": "test-password", "role": "test-role"})
#     assert response.status_code == 201, response.text

#     response = client.get_with_permissions(url="/users/test-user")
#     assert response.status_code == 200, response.text
#     assert response.json()["role"] == "test-role"


# create role with user token -> 403
# create role with admin token -> 201
# delete role -> 204
# update role -> 201
# delete role with user token -> 403
# delete role with admin token -> 204
# update role with user token -> 403
# update role with admin token -> 201
# delete root role -> 403
# delete an inexistent role -> 404

# create user with user token -> 403
# create user with admin token -> 201
# delete user -> 204
# update user name -> 201
# update user role -> 201
# update user name with existing name -> 400
# update user role with unexisting role -> 400
# delete root user -> 403
# delete an inexistent user -> 404

# create token with user token -> 403
# create token with admin token -> 201
# delete token -> 204
# delete inexistent token -> 404
# malformed token -> 401
# invalid token -> 401
# expired token -> 401
# check token with user token -> 200
# check token with admin token -> 200
# check inexistent token -> 404


# login with inexistent user -> 401
# login with invalid password -> 401
# login with inexistent role -> 404
# login with invalid role -> 404
# login with root user -> 200
# login with root role -> 200
