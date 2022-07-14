from requests import Session
from typing import Union


class UnauthorizedRequestError(Exception):
    pass


class RequestQueryError(Exception):
    pass


class DatabaseHelper:
    """
    Database communication helper class
    """
    def __init__(self, auth: str):
        r"""
        :param str auth: Authentication token to be used in requests
        """
        self.result = []
        self.headers = {
            "Authentication": auth
        }
        self.status_code = None
        self._session = Session()

    def select(self, columns: str, table: str) -> int:
        """
        :param str columns: Columns to select from table
        :param str table: Table to select from
        :return: Status code of the query
        :rtype: int
        :raises UnauthorizedRequestError: If the auth header provided did not work
        :raises RequestQueryError: Something went wrong with the query server-side
        """
        headers = {
            "columns": columns,
            "table": table
        }
        merge = {}
        merge.update(headers)
        merge.update(self.headers)
        resp = self._session.get("http://127.0.0.1:8080/execute", headers=merge)
        if resp.status_code == 400:
            self.status_code = 400
            error = resp.json()["error"]
            raise RequestQueryError("An error occurred: %s" % error)
        elif resp.status_code == 401:
            self.status_code = 401
            raise UnauthorizedRequestError("Unauthorized")
        elif resp.status_code == 500:
            self.status_code = 500
            return 500
        else:
            self.result = resp.json().get("result")
            self.status_code = 200
            return 200

    def insert(self, values: Union[list, str], table: str) -> int:
        """
        :param Union[str, list] values: Values to insert into the table
        :param str table: Table to insert into
        :return: Status code of the query
        :rtype: int
        :raises UnauthorizedRequestError: If the auth header provided did not work
        :raises RequestQueryError: Something went wrong with the query server-side
        """
        headers = {
            "values": values,
            "table": table
        }
        merge = {}
        merge.update(headers)
        merge.update(self.headers)
        resp = self._session.post("http://127.0.0.1:8080/execute", headers=merge)
        if resp.status_code == 400:
            self.status_code = 400
            error = resp.json()["error"]
            raise RequestQueryError("An error occurred: %s" % error)
        elif resp.status_code == 401:
            self.status_code = 401
            raise UnauthorizedRequestError("Unauthorized")
        elif resp.status_code == 500:
            self.status_code = 500
            return 500
        else:
            self.status_code = 200
            return 200

    def delete(self, values: str, where:str, table: str) -> int:
        """
        :param Union[str, list] values: Value for the where
        :param str where: Column condition
        :param str table: Table to delete from
        :return: Status code of the query
        :rtype: int
        :raises UnauthorizedRequestError: If the auth header provided did not work
        :raises RequestQueryError: Something went wrong with the query server-side
        """
        headers = {
            "values": values,
            "table": table,
            "where": where
        }
        merge = {}
        merge.update(headers)
        merge.update(self.headers)
        resp = self._session.delete("http://127.0.0.1:8080/execute", headers=merge)
        if resp.status_code == 400:
            self.status_code = 400
            error = resp.json().get("error")
            error = resp.json()["message"] if error is None else error
            raise RequestQueryError("An error occurred: %s" % error)
        elif resp.status_code == 401:
            self.status_code = 401
            resp.raise_for_status()
        elif resp.status_code == 500:
            self.status_code = 500
            return 500
        else:
            self.status_code = resp.status_code
            return resp.status_code

    def __iter__(self):
        """
        :returns: A list for each result from a select query
        """
        for result in self.result:
            yield result
