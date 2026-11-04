"""
Unit & Integration tests for Admin Faculty Management & Access Control.
File: tests/test_faculty_management.py
"""

import unittest
from app import create_app
from database.models import db, User

class TestFacultyManagement(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_unauthenticated_access_blocked(self):
        """Unauthenticated requests to admin faculty routes should redirect to login."""
        res = self.client.get("/admin/faculty", follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers.get("Location", ""))

    def test_non_admin_access_forbidden(self):
        """Faculty or students attempting to access admin routes should be blocked."""
        # 1. Log in as regular faculty
        self.client.post("/login", data={
            "username": "faculty",
            "password": "faculty123"
        }, follow_redirects=True)

        res = self.client.get("/admin/faculty", follow_redirects=True)
        self.assertIn(b"do not have permission", res.data)

        # 2. Log in as student
        self.client.get("/logout", follow_redirects=True)
        self.client.post("/login", data={
            "username": "ENG0001",
            "password": "student123"
        }, follow_redirects=True)

        res_stud = self.client.get("/admin/faculty", follow_redirects=True)
        self.assertIn(b"authorized to access their personal academic portal only", res_stud.data)

    def test_admin_faculty_crud_flow(self):
        """Admin can access faculty page, create new faculty, login with new faculty, reset password, and delete faculty."""
        # Log in as Admin
        login_res = self.client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)

        # 1. Access Faculty Management Page
        page_res = self.client.get("/admin/faculty")
        self.assertEqual(page_res.status_code, 200)
        self.assertIn(b"Faculty & Mentor Access Management", page_res.data)
        self.assertIn(b"Provision Faculty Account", page_res.data)

        # Clean up test user if previously left over
        with self.app.app_context():
            old = User.query.filter_by(username="test_prof_01").first()
            if old:
                db.session.delete(old)
                db.session.commit()

        # 2. Create New Faculty Account
        create_res = self.client.post("/admin/faculty/create", data={
            "username": "test_prof_01",
            "password": "secureProfPassword2026",
            "full_name": "Dr. Alan Turing",
            "email": "a.turing@eduvision.edu",
            "department": "Computer Science",
            "designation": "Professor"
        }, follow_redirects=True)
        self.assertEqual(create_res.status_code, 200)
        self.assertIn(b"successfully created", create_res.data)
        self.assertIn(b"Dr. Alan Turing", create_res.data)

        # 3. Prevent duplicate username
        dup_res = self.client.post("/admin/faculty/create", data={
            "username": "test_prof_01",
            "password": "anotherPassword123"
        }, follow_redirects=True)
        self.assertIn(b"already exists", dup_res.data)

        # 4. Verify New Faculty Can Log In
        self.client.get("/logout", follow_redirects=True)
        faculty_login = self.client.post("/login", data={
            "username": "test_prof_01",
            "password": "secureProfPassword2026"
        }, follow_redirects=True)
        self.assertEqual(faculty_login.status_code, 200)
        self.assertIn(b"Welcome back, test_prof_01", faculty_login.data)

        # 5. Admin resets faculty password
        self.client.get("/logout", follow_redirects=True)
        self.client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)

        with self.app.app_context():
            fac_user = User.query.filter_by(username="test_prof_01").first()
            self.assertIsNotNone(fac_user)
            user_id = fac_user.id

        reset_res = self.client.post(f"/admin/faculty/{user_id}/reset-password", data={
            "new_password": "newSuperPassword99"
        }, follow_redirects=True)
        self.assertIn(b"successfully updated", reset_res.data)

        # 6. Verify Login with New Password
        self.client.get("/logout", follow_redirects=True)
        new_login = self.client.post("/login", data={
            "username": "test_prof_01",
            "password": "newSuperPassword99"
        }, follow_redirects=True)
        self.assertEqual(new_login.status_code, 200)
        self.assertIn(b"test_prof_01", new_login.data)

        # 7. Admin deletes faculty account
        self.client.get("/logout", follow_redirects=True)
        self.client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)

        del_res = self.client.post(f"/admin/faculty/{user_id}/delete", follow_redirects=True)
        self.assertIn(b"permanently removed", del_res.data)

        # Confirm deleted
        with self.app.app_context():
            deleted_check = User.query.filter_by(username="test_prof_01").first()
            self.assertIsNone(deleted_check)

if __name__ == "__main__":
    unittest.main()
