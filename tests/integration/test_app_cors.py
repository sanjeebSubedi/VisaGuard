def test_app_allows_vite_dev_origin_for_api_requests(client):
    response = client.options(
        '/api/workflows/compliance/run',
        headers={
            'Origin': 'http://127.0.0.1:5173',
            'Access-Control-Request-Method': 'POST',
        },
    )

    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'http://127.0.0.1:5173'
