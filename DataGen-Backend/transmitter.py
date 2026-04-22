import httpx

async def send_to_api(api_config: dict, payload: dict) -> str:
    """Sends payload and returns a status string for the UI."""
    if not api_config:
        return ""

    async with httpx.AsyncClient() as client:
        try:
            res = await client.request(
                method=api_config.get('method', 'POST'),
                url=api_config['url'],
                json=payload,
                headers=api_config.get('headers', {}),
                timeout=2.0
            )
            return f"[{res.status_code}] Success -> {api_config['url']}"
        except Exception as e:
            return f"[Error] {str(e)}"