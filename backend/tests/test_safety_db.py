import pytest

from app import db
from app.safety import UnsafeSQLError, validate_sql


@pytest.mark.parametrize("sql", [
    "DELETE FROM orders", "DROP TABLE customers", "UPDATE products SET unit_price = 1",
    "INSERT INTO regions VALUES (9, 'X')", "SELECT 1; DROP TABLE orders", "PRAGMA table_info(orders)",
    "ATTACH DATABASE 'x.db' AS x", "CREATE TABLE t (a int)",
])
def test_blocks_writes(sql):
    with pytest.raises(UnsafeSQLError):
        validate_sql(sql, 200)


def test_allows_select_and_adds_limit():
    assert validate_sql("SELECT * FROM orders", 200).endswith("LIMIT 200")
    assert validate_sql("```sql\nSELECT 1;\n```", 200).startswith("SELECT 1")
    assert "LIMIT 5" in validate_sql("SELECT * FROM orders LIMIT 5", 200)
    assert "LIMIT 200" in validate_sql("SELECT * FROM orders LIMIT 100000", 200)
    # A string value containing a blocked word is fine.
    validate_sql("SELECT * FROM products WHERE product_name = 'Drop Shipping'", 200)


def test_database_is_read_only():
    con = db.connect()
    with pytest.raises(Exception):
        con.execute("DELETE FROM orders")
    con.close()


def test_query_and_schema():
    r = db.run_query("SELECT COUNT(*) AS n FROM customers")
    assert r["columns"] == ["n"] and r["rows"][0][0] == 800
    with pytest.raises(db.QueryError):
        db.run_query("SELECT nope FROM customers")
    text = db.schema_text()
    assert "TABLE orders" in text and "Delivered" in text
