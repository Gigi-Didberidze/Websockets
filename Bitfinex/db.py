from db_conn import connect_to_database

connection = connect_to_database()

cursor = connection.cursor()

create_order_table = """
CREATE TABLE IF NOT EXISTS order_data (
    channel_id INT,
    price DECIMAL(18, 10),
    count INT,
    amount DECIMAL(18, 10)
);
"""

cursor.execute(create_order_table)
connection.commit()

cursor.close()
connection.close()
