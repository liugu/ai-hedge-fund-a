"""
SSL修复模块 - 解决AKShare等数据源的SSL连接问题
"""

import os
import ssl
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 设置环境变量以禁用SSL验证
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''

# 修改默认SSL上下文
_original_create_default_context = ssl.create_default_context

def _create_unverified_context(*args, **kwargs):
    """创建不验证SSL证书的上下文"""
    context = _original_create_default_context(*args, **kwargs)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context

# 替换默认SSL上下文创建函数
ssl.create_default_context = _create_unverified_context

# 修复requests的SSL验证
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.ssl_ import create_urllib3_context

    class NoSSLAdapter(HTTPAdapter):
        """自定义SSL适配器，禁用证书验证"""
        def init_poolmanager(self, *args, **kwargs):
            ctx = create_urllib3_context()
            ctx.check_hostname = False
            ctx.verify_mode = 0
            kwargs['ssl_context'] = ctx
            return super().init_poolmanager(*args, **kwargs)

    # 为所有HTTPS请求挂载适配器
    requests.Session().mount('https://', NoSSLAdapter())

except ImportError:
    pass

# 修复httpx的SSL验证（如果使用）
try:
    import httpx
    # httpx会使用自定义的SSL上下文
except ImportError:
    pass

print("SSL修复已应用 - 已禁用SSL证书验证")
