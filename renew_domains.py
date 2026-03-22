import requests
import os

# 从环境变量获取推送配置
PUSHPLUS_TOKEN = os.environ.get('PUSHPLUS_TOKEN')
PUSHPLUS_TOPIC = os.environ.get('PUSHPLUS_TOPIC')  # 群组编码

BASE_URL = "https://api005.dnshe.com/index.php?m=domain_hub"

def send_pushplus(content):
    if not PUSHPLUS_TOKEN:
        print("未配置 PushPlus Token，跳过推送")
        return
    
    url = "http://www.pushplus.plus/send"
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": "DNSHE 域名自动续期报告",
        "content": content,
        "template": "txt",
        "topic": PUSHPLUS_TOPIC
    }
    requests.post(url, json=data)

def process_account(api_key, api_secret, account_idx):
    """处理单个账号的域名续期"""
    headers = {
        "X-API-Key": api_key,
        "X-API-Secret": api_secret,
        "Content-Type": "application/json"
    }

    # 1. 获取所有子域名 
    list_url = f"{BASE_URL}&endpoint=subdomains&action=list"
    try:
        resp = requests.get(list_url, headers=headers)
        subdomains = resp.json().get('subdomains', [])
    except Exception as e:
        return [f"❌ 账号 {account_idx}: 获取域名列表失败: {str(e)}"]

    if not subdomains:
        return [f"账号 {account_idx}: 未发现子域名。"]

    results = []
    
    # 2. 遍历并续期 
    for domain in subdomains:
        domain_id = domain['id']
        full_domain = domain['full_domain']
        
        renew_url = f"{BASE_URL}&endpoint=subdomains&action=renew"
        payload = {"subdomain_id": domain_id}
        
        try:
            r_resp = requests.post(renew_url, headers=headers, json=payload).json()
            if r_resp.get('success'):
                new_expiry = r_resp.get('new_expires_at', '未知')
                results.append(f"✅ [账号 {account_idx}] {full_domain}: 续期成功 (新到期: {new_expiry})")
            else:
                results.append(f"❌ [账号 {account_idx}] {full_domain}: 续期失败 ({r_resp.get('message', '未知错误')})")
        except Exception as e:
            results.append(f"❌ [账号 {account_idx}] {full_domain}: 请求异常")

    return results

def main():
    all_results = []
    account_count = 0

    # 支持遍历多个账号配置 (这里设定最多检查10个，你可以随时在 Github Secrets 里加)
    for i in range(1, 11):
        # 兼容原有的无后缀变量名，作为账号1
        if i == 1:
            api_key = os.environ.get(f'DNSHE_API_KEY_{i}') or os.environ.get('DNSHE_API_KEY')
            api_secret = os.environ.get(f'DNSHE_API_SECRET_{i}') or os.environ.get('DNSHE_API_SECRET')
        else:
            api_key = os.environ.get(f'DNSHE_API_KEY_{i}')
            api_secret = os.environ.get(f'DNSHE_API_SECRET_{i}')

        # 只要检测到一对 Key 和 Secret，就执行该账号的续期逻辑
        if api_key and api_secret:
            account_count += 1
            account_results = process_account(api_key, api_secret, i)
            all_results.extend(account_results)
            all_results.append("---") # 账号之间的分隔线

    if account_count == 0:
        msg = "未找到任何有效的 API 密钥配置，请检查环境变量。"
        print(msg)
        send_pushplus(msg)
        return

    # 3. 汇总所有账号的消息并一次性推送 
    if all_results:
        # 移除最后多余的分割线
        if all_results[-1] == "---":
            all_results.pop()
            
        message = "\n".join(all_results)
        print(message)
        send_pushplus(message)

if __name__ == "__main__":
    main()
