import pytest


@pytest.fixture
def user_data():
    return {"name": "John", "email": "john@example.com", "age": 30}


@pytest.fixture
def invalid_data():
    return {"name": "", "email": "invalid", "age": 17}
