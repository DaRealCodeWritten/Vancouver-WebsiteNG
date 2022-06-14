import json
from mysql.connector import MySQLConnection


class PermissionsManagement:
    def __init__(self, database: MySQLConnection):
        """Helper class for managing user permissions."""
        self.perms: dict = self._load_permissions()
        self.database = database

    def _load_permissions(self):
        """Loads permissions from the config file."""
        with open('utils/permissions.json', 'r') as f:
            return json.load(f)

    def get_permissions(self, user_id):
        """Returns the permissions of a user."""
        cursor = self.database.cursor()
        cursor.execute(f"SELECT permissions FROM dev WHERE cid = {user_id}")
        result = cursor.fetchone()
        if result is None:
            return None, "None"
        if self.perms.get(result[0]) is None:
            return None, "None"
        return self.perms[result[0]], result[0]

    def set_permissions(self, cid, permissions):
        """Sets the permissions of a user."""
        crs = self.database.cursor()
        crs.execute(f"SELECT permissions FROM dev WHERE cid = {cid}")
        result = crs.fetchone()
        if result[0] == "DV":
            return False
        cursor = self.database.cursor()
        cursor.execute(f"UPDATE dev SET permissions = {permissions} WHERE cid = '{cid}'")
        cursor.close()
        self.database.commit()
        return True

    def update_permissions_index(self):
        """Updates the permissions index."""
        self.perms = self._load_permissions()

    def view_permissions_for(self, group):
        """Returns the permissions of a group."""
        return self.perms[group]

    def has_permissions_for(self, group, permissions):
        """Checks if a group has the given permissions."""
        if self.perms.get(group) is None:
            return False
        elif self.perms.get(group).get("Override-All") is True:
            return True
        return permissions in self.perms[group].keys()
