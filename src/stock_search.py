import os
import json
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
CACHE_FILE = os.path.join(project_root, 'data', 'stock_name_cache.json')
ALL_STOCKS_JSON = os.path.join(project_root, 'data', 'all_stocks.json')

def load_all_stocks_from_json():
    """从 all_stocks.json 文件加载所有股票"""
    stocks = []

    if os.path.exists(ALL_STOCKS_JSON):
        try:
            with open(ALL_STOCKS_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    code = item.get('code', '').strip().zfill(6)
                    name = item.get('name', '').strip()
                    initials = item.get('initials', [])
                    if name and code:
                        stocks.append({
                            'code': code,
                            'name': name,
                            'initials': initials
                        })
            print(f"从 all_stocks.json 加载到 {len(stocks)} 只股票")
        except Exception as e:
            print(f"读取 all_stocks.json 失败: {e}")

    return stocks

def is_valid_chinese_char(char):
    """检查字符是否为有效的中文字符"""
    return '\u4e00' <= char <= '\u9fff'

def is_valid_stock_name(name):
    """检查股票名称是否有效（包含至少一个中文字符）"""
    if not name:
        return False
    for char in name[:10]:
        if is_valid_chinese_char(char):
            return True
    return False

def load_stock_cache():
    """加载股票缓存"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                cache_date = data.get('date', '')
                today = datetime.now().strftime('%Y%m%d')
                stocks = data.get('stocks', [])
                if cache_date == today and stocks:
                    if len(stocks) > 5000 and stocks and is_valid_stock_name(stocks[0].get('name', '')):
                        print("使用缓存的股票名称数据")
                        return stocks
                    else:
                        print("缓存数据无效（数量不足或名称无效），重新加载")
        except Exception as e:
            print(f"读取缓存失败: {e}")

    stocks = load_all_stocks_from_json()

    cache_data = {
        'date': datetime.now().strftime('%Y%m%d'),
        'stocks': stocks
    }
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        print(f"股票名称缓存已保存: {CACHE_FILE}")
    except Exception as e:
        print(f"保存缓存失败: {e}")

    return stocks

def search_stocks(query, limit=20):
    """搜索股票 - 支持名称、代码、首字母匹配"""
    query = query.strip()
    if not query:
        return []

    stocks = load_stock_cache()
    results = []

    for stock in stocks:
        name = stock['name']
        code = stock['code']
        initials = stock.get('initials', [])

        if code == query or code.endswith(query):
            results.append({'code': code, 'name': name, 'match_type': 'code', 'initials': initials})
        elif query in name:
            results.append({'code': code, 'name': name, 'match_type': 'name', 'initials': initials})
        else:
            for initial in initials:
                if initial.startswith(query.lower()):
                    results.append({'code': code, 'name': name, 'match_type': 'initial', 'initials': initials})
                    break

    results.sort(key=lambda x: (x['match_type'] == 'initial', x['match_type'] == 'name', x['match_type'] == 'code', len(x['name'])))

    return results[:limit]

if __name__ == '__main__':
    stocks = load_stock_cache()
    print(f"\n测试搜索:")
    print(f"搜索 '航天发展': {search_stocks('航天发展')[:3]}")
    print(f"搜索 '603629': {search_stocks('603629')[:3]}")
    print(f"搜索 '航天': {search_stocks('航天')[:5]}")
    print(f"搜索 'htfb': {search_stocks('htfb')[:5]}")
