import mysql.connector

def connect_to_database():
    connection = mysql.connector.connect(
        
        # Replace the following values with your own database credentials

        host='<hostname>',
        user='<username>',
        password='<password>',
        database='<database>'
    )
    return connection