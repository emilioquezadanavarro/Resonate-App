from app.database import db, User

class UserService:
    @staticmethod
    def create_user(username, first_name, last_name, gender, age):
        """
        Creates a new user safely.
        Returns: The new User object or None if failed.

        """

        try:
            new_user = User(username=username, first_name=first_name, last_name=last_name, gender=gender, age=age)

            db.session.add(new_user)
            db.session.commit()
            print(f"Service: Created user '{username}' ✅")
            return new_user

        except Exception as e:
            print(f"Service Error: {e} ❌")
            db.session.rollback()
            return None

    @staticmethod
    def get_all_users():
        return User.query.all()

    @staticmethod
    def get_user_by_id(user_id):
        return User.query.get(user_id)