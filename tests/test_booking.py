"""业务核心测试：抢座并发、下单事务、订单数据隔离。"""

import asyncio

import httpx


async def _token(client, username: str) -> str:
    await client.post(
        "/api/v1/auth/register", json={"username": username, "password": "123456"}
    )
    resp = await client.post(
        "/api/v1/auth/login", json={"username": username, "password": "123456"}
    )
    return resp.json()["token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_show_with_seats(client, token: str) -> tuple[int, list[dict]]:
    resp = await client.post(
        "/api/v1/shows",
        json={
            "title": "测试演出",
            "venue": "测试场馆",
            "start_time": "2026-12-01T19:30:00",
        },
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    show_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/shows/{show_id}/seats/generate",
        json={"rows": 1, "cols": 2, "price": "180.00"},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text

    resp = await client.get(f"/api/v1/shows/{show_id}/seats", headers=_auth(token))
    return show_id, resp.json()


async def test_two_users_lock_same_seat_only_one_wins(client):
    """核心用例：并发抢同一座位，只能有一个成功。"""
    token_a = await _token(client, "alice")
    token_b = await _token(client, "bob")
    show_id, seats = await _create_show_with_seats(client, token_a)
    seat_id = seats[0]["id"]

    r1, r2 = await asyncio.gather(
        client.post(
            f"/api/v1/shows/{show_id}/seats/{seat_id}/lock", headers=_auth(token_a)
        ),
        client.post(
            f"/api/v1/shows/{show_id}/seats/{seat_id}/lock", headers=_auth(token_b)
        ),
    )

    assert sorted([r1.status_code, r2.status_code]) == [200, 409], (r1.text, r2.text)


async def test_order_requires_lock_and_seat_sold_once(client):
    token = await _token(client, "alice")
    show_id, seats = await _create_show_with_seats(client, token)
    seat_id = seats[0]["id"]

    # 没锁座直接下单 → 409
    resp = await client.post("/api/v1/orders", json={"seat_id": seat_id}, headers=_auth(token))
    assert resp.status_code == 409

    # 锁座 → 下单成功
    assert (
        await client.post(
            f"/api/v1/shows/{show_id}/seats/{seat_id}/lock", headers=_auth(token)
        )
    ).status_code == 200

    created = await client.post(
        "/api/v1/orders", json={"seat_id": seat_id}, headers=_auth(token)
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "pending"

    # 同一座位再下单 → 409（锁已删除 / 座位已售）
    again = await client.post(
        "/api/v1/orders", json={"seat_id": seat_id}, headers=_auth(token)
    )
    assert again.status_code == 409

    # 座位状态：sold 且不再处于锁定中
    seats_after = (await client.get(f"/api/v1/shows/{show_id}/seats", headers=_auth(token))).json()
    target = next(s for s in seats_after if s["id"] == seat_id)
    assert target["status"] == "sold"
    assert target["is_locked"] is False


async def test_orders_are_isolated_per_user(client):
    """数据隔离：只返回自己的订单。"""
    token_a = await _token(client, "alice")
    token_b = await _token(client, "bob")
    show_id, seats = await _create_show_with_seats(client, token_a)

    for token, seat in ((token_a, seats[0]), (token_b, seats[1])):
        await client.post(
            f"/api/v1/shows/{show_id}/seats/{seat['id']}/lock", headers=_auth(token)
        )
        resp = await client.post(
            "/api/v1/orders", json={"seat_id": seat["id"]}, headers=_auth(token)
        )
        assert resp.status_code == 201, resp.text

    alice_orders = (await client.get("/api/v1/orders", headers=_auth(token_a))).json()
    bob_orders = (await client.get("/api/v1/orders", headers=_auth(token_b))).json()

    assert len(alice_orders) == 1
    assert len(bob_orders) == 1
    assert alice_orders[0]["seat_id"] != bob_orders[0]["seat_id"]
