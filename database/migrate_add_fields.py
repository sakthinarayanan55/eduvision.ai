"""
Migration script to add 'name' and 'parent_email' columns to 'students' table
and seed realistic student names and parent email IDs for existing records.
File: database/migrate_add_fields.py
"""

import sqlite3
import os
import random

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "student_performance.db")

FIRST_NAMES_MALE = [
    "Aarav", "Rohan", "Aditya", "Vikram", "Karthik", "Siddharth", "Rahul", "Arjun",
    "Pranav", "Nikhil", "Sanjay", "Varun", "Abhishek", "Manish", "Gautam", "Harish",
    "Sai", "Akash", "Deepak", "Vivek", "Vishal", "Anand", "Rajesh", "Surya", "Kunal"
]

FIRST_NAMES_FEMALE = [
    "Ananya", "Priya", "Sneha", "Kavya", "Divya", "Pooja", "Aishwarya", "Deepika",
    "Meera", "Shreya", "Nandini", "Rhea", "Swati", "Neha", "Ishita", "Tanvi",
    "Bhavana", "Keerthi", "Lavanya", "Harini", "Pavithra", "Swetha", "Soundarya", "Gayathri"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Reddy", "Narayanan", "Iyer", "Rao", "Kumar",
    "Gupta", "Singh", "Das", "Menon", "Joshi", "Chopra", "Deshmukh", "Pillai",
    "Bose", "Chatterjee", "Kulkarni", "Nair", "Murthy", "Bhat", "Prasad", "Shetty"
]

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database file not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(students)")
    columns = [row[1] for row in cursor.fetchall()]

    if "name" not in columns:
        print("Adding 'name' column to students table...")
        cursor.execute("ALTER TABLE students ADD COLUMN name VARCHAR(120) DEFAULT 'Student'")

    if "parent_email" not in columns:
        print("Adding 'parent_email' column to students table...")
        cursor.execute("ALTER TABLE students ADD COLUMN parent_email VARCHAR(120)")

    conn.commit()

    # Now populate realistic names and parent emails where missing or default
    cursor.execute("SELECT id, student_id, gender, name, parent_email FROM students")
    students = cursor.fetchall()
    
    updated_count = 0
    random.seed(42)  # Deterministic realistic assignment

    for sid, st_id, gender, name, parent_email in students:
        needs_update = False
        new_name = name
        new_email = parent_email

        if not name or name == "Student":
            if gender == "Female":
                first = FIRST_NAMES_FEMALE[hash(st_id) % len(FIRST_NAMES_FEMALE)]
            else:
                first = FIRST_NAMES_MALE[hash(st_id) % len(FIRST_NAMES_MALE)]
            last = LAST_NAMES[(hash(st_id) // 7) % len(LAST_NAMES)]
            new_name = f"{first} {last}"
            needs_update = True

        if not parent_email:
            st_clean = st_id.lower()
            name_slug = new_name.lower().replace(" ", ".")
            new_email = f"parent.{name_slug}.{st_clean}@college.edu"
            needs_update = True

        if needs_update:
            cursor.execute(
                "UPDATE students SET name = ?, parent_email = ? WHERE id = ?",
                (new_name, new_email, sid)
            )
            updated_count += 1

    conn.commit()
    conn.close()
    print(f"Migration completed successfully! Updated {updated_count} student records.")

if __name__ == "__main__":
    migrate()
