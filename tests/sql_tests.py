import pytest
from core.msexpress.connect_sql import connect_to_sql

def test_empty_host():
    with pytest.raises(ValueError, match="Empty host address"):
        connect_to_sql(host="")

def test_missing_credentials():
    with pytest.raises(ValueError, match="Username and password required"):
        connect_to_sql(host="localhost", database="master", username=None, password=None)

def test_invalid_host():
    with pytest.raises(RuntimeError):
        connect_to_sql(host="invalid_host", database="master", username="user", password="pass")

# Optional: Requires valid test environment
@pytest.mark.skip(reason="Needs real DB setup")
def test_valid_connection():
    conn = connect_to_sql(
        host="localhost\\SQLEXPRESS",
        database="master",
        username="sa",
        password="your_password"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    assert cursor.fetchone()[0] == 1
    conn.close()
