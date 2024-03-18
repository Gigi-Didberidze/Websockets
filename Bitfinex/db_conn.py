import mysql.connector


class DatabaseConnector:
    @staticmethod
    def connect_to_database():
        conn = mysql.connector.connect(
            host='<hostName>',
            port='<portNumber>',
            user='<userName>',
            password='<password>',
            database='<database>'
        )
        return conn
