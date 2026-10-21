"""认证相关测试：注册、登录、令牌鉴权。"""


async def _register(client, username: str, password: str = "123456"):
    return await client.post(
        "/api/v1/auth/register", json={"username": username, "password": password}
    )


async def _login(client, username: str, password: str = "123456") -> str:
    resp = await client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    return resp.json().get("token", "")


async def test_register_never_returns_password_hash(client):
    resp = await _register(client, "alice")

    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "alice"
    assert "password_hash" not in body          # 响应白名单生效


async def test_duplicate_username_conflicts(client):
    await _register(client, "alice")

    resp = await _register(client, "alice")

    assert resp.status_code == 409


async def test_short_password_rejected(client):
    resp = await _register(client, "alice", password="123")

    assert resp.status_code == 422


async def test_login_wrong_password(client):
    await _register(client, "alice")

    resp = await client.post(
        "/api/v1/auth/login", json={"username": "alice", "password": "wrong"}
    )

    assert resp.status_code == 401


async def test_me_requires_valid_token(client):
    await _register(client, "alice")
    token = await _login(client, "alice")
    assert len(token) == 43                      # token_urlsafe(32) 的长度

    ok = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert ok.status_code == 200
    assert ok.json()["username"] == "alice"

    anonymous = await client.get("/api/v1/auth/me")
    assert anonymous.status_code == 401

    fake = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert fake.status_code == 401
