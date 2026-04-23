from __future__ import annotations

from core.controller.response import ApiResponse


class TestApiResponseSuccess:
    def test_basic(self):
        r = ApiResponse.success()
        assert r["success"] is True
        assert r["message"] == "Success"
        assert r["status"] == 200

    def test_with_data(self):
        r = ApiResponse.success(data={"id": 1})
        assert r["data"] == {"id": 1}

    def test_with_meta(self):
        r = ApiResponse.success(meta={"count": 5})
        assert r["meta"]["count"] == 5

    def test_custom_message(self):
        r = ApiResponse.success(message="All good")
        assert r["message"] == "All good"


class TestApiResponseCreated:
    def test_created(self):
        r = ApiResponse.created(data={"id": 1})
        assert r["success"] is True
        assert r["status"] == 201
        assert r["data"] == {"id": 1}


class TestApiResponseError:
    def test_basic(self):
        r = ApiResponse.error("Bad request")
        assert r["success"] is False
        assert r["status"] == 400

    def test_with_errors(self):
        r = ApiResponse.error("Fail", errors={"name": "required"})
        assert r["errors"] == {"name": "required"}

    def test_with_code(self):
        r = ApiResponse.error("Fail", code="CUSTOM_ERROR")
        assert r["code"] == "CUSTOM_ERROR"


class TestApiResponseShortcuts:
    def test_not_found(self):
        r = ApiResponse.not_found()
        assert r["status"] == 404

    def test_not_found_resource(self):
        r = ApiResponse.not_found(resource="User")
        assert "User" in r["message"]

    def test_validation_error(self):
        r = ApiResponse.validation_error({"email": "invalid"})
        assert r["status"] == 422
        assert r["errors"] == {"email": "invalid"}

    def test_unauthorized(self):
        r = ApiResponse.unauthorized()
        assert r["status"] == 401

    def test_forbidden(self):
        r = ApiResponse.forbidden()
        assert r["status"] == 403

    def test_server_error(self):
        r = ApiResponse.server_error()
        assert r["status"] == 500

    def test_no_content(self):
        r = ApiResponse.no_content()
        assert r["status"] == 204
        assert r["success"] is True


class TestApiResponsePaginated:
    def test_paginated(self):
        items = [{"id": i} for i in range(5)]
        r = ApiResponse.paginated(items, total=50, page=1, per_page=5)
        assert r["success"] is True
        assert len(r["data"]) == 5
        assert r["meta"]["pagination"]["total"] == 50
        assert r["meta"]["pagination"]["page"] == 1
        assert r["meta"]["pagination"]["total_pages"] == 10
        assert r["meta"]["pagination"]["has_next"] is True
        assert r["meta"]["pagination"]["has_prev"] is False

    def test_last_page(self):
        r = ApiResponse.paginated([], total=20, page=4, per_page=5)
        assert r["meta"]["pagination"]["has_next"] is False
        assert r["meta"]["pagination"]["has_prev"] is True


class TestApiResponseCollection:
    def test_collection(self):
        items = [1, 2, 3]
        r = ApiResponse.collection(items)
        assert r["data"] == [1, 2, 3]
        assert r["meta"]["count"] == 3
