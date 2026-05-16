def build_proxy_kwargs(config) -> dict:
    if not config.proxy_type:
        return {}
    ptype = config.proxy_type
    if ptype == "mtproto":
        from telethon.network import ConnectionTcpMTProxyRandomizedIntermediate
        return {
            "connection": ConnectionTcpMTProxyRandomizedIntermediate,
            "proxy": (config.proxy_host, config.proxy_port, config.proxy_secret),
        }
    import socks
    socks_type = socks.SOCKS5 if ptype == "socks5" else socks.SOCKS4
    proxy = (socks_type, config.proxy_host, config.proxy_port)
    if config.proxy_username:
        proxy += (True, config.proxy_username, config.proxy_password)
    return {"proxy": proxy}
