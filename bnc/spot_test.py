from spot import ping_spot_endpoint, get_spot_server_time, get_spot_exchange_info


def test_ping_spot_endpoint():
    ping_spot_endpoint()


def test_get_server_time():
    resp = get_spot_server_time()
    assert resp.data["serverTime"] is not None


def test_get_spot_exchange_info():
    resp = get_spot_exchange_info(
        symbols=["BTCUSDT", "ETHUSDT"]
    )
    assert resp.data["symbols"] is not None


if __name__ == "__main__":
    test_ping_spot_endpoint()
    test_get_server_time()
    test_get_spot_exchange_info()