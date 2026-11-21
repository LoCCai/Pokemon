from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import qweb_stub
from nonebot_plugin_pokemon.config import Config
from nonebot_plugin_pokemon.web import app as web_app
from nonebot_plugin_pokemon.web import qweb as qweb_module
from nonebot_plugin_pokemon.web.auth import (
    AuthDependencies,
    WebAccount,
    load_host_auth,
    unavailable_auth,
)


def test_web_defaults_closed():
    config = Config()
    assert config.pokemon_web_enabled is False
    # 网页默认关闭，但 QWeb 入口本身保留，开启后必须依赖宿主认证。
    assert config.pokemon_qweb_enabled is True


def test_missing_host_dependency_returns_none():
    assert load_host_auth("does.not.exist") is None


def test_unavailable_auth_never_falls_back_to_guest():
    app = FastAPI()
    app.include_router(web_app.create_router(unavailable_auth()), prefix="/qweb")
    client = TestClient(app)

    assert client.get("/qweb/api/health").status_code == 200

    for path in (
        "/qweb/api/bootstrap",
        "/qweb/api/admin/state",
        "/qweb/api/menu",
    ):
        response = client.get(path)
        assert response.status_code == 503, path

    response = client.post("/qweb/api/command", json={"text": "宝可梦帮助"})
    assert response.status_code == 503


def test_setup_web_without_host_does_not_mount(monkeypatch):
    monkeypatch.setattr(web_app, "load_host_auth", lambda: None)
    app = FastAPI()
    assert web_app.setup_web(app, force=True) is False
    assert not [route for route in app.routes if getattr(route, "path", "").startswith("/qweb")]


def test_setup_web_with_injected_auth_mounts():
    auth = AuthDependencies(
        require_membership=qweb_stub.require_membership,
        admin_account=qweb_stub.admin_account,
        csrf_protected=qweb_stub.csrf_protected,
    )
    app = FastAPI()
    assert web_app.setup_web(app, auth=auth, force=True) is True
    client = TestClient(app)
    headers = {"X-Test-Account": "member:test-injected", "X-CSRF-Token": qweb_stub.CSRF_TOKEN}
    response = client.get("/qweb/pokemon/api/bootstrap", headers=headers)
    assert response.status_code == 200
    assert response.json()["identity"]["user_id"] == "test-injected"


def test_mount_requires_auth(monkeypatch):
    monkeypatch.setattr(qweb_module, "load_host_auth", lambda: None)
    app = FastAPI()
    with pytest.raises(RuntimeError):
        qweb_module.mount(app)


def test_account_only_comes_from_qq_and_role():
    account = WebAccount.from_host(
        SimpleNamespace(qq="12345", role="admin", user_id="evil", is_admin=False)
    )
    assert account.qq == "12345"
    assert account.role == "admin"
    assert account.is_admin is True
    ctx = account.to_context()
    assert ctx.user_id == "12345"
    assert ctx.group_id is None
    assert ctx.is_admin is True

    member = WebAccount.from_host(SimpleNamespace(qq="12345", role="member", is_admin=True))
    assert member.is_admin is False


def test_account_without_qq_is_rejected():
    with pytest.raises(HTTPException) as exc:
        WebAccount.from_host(SimpleNamespace(user_id="12345", role="admin", is_admin=True))
    assert exc.value.status_code == 401