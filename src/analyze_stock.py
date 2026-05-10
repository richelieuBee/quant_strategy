import os
import json
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import argparse
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties

# 全局变量
# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录
project_root = os.path.dirname(current_dir)

# 使用相对路径，确保跨平台兼容
DEFAULT_STOCK_CSV_PATH = os.path.join(project_root, 'data', 'stock.csv')
CACHE_DIR = os.path.join(project_root, 'data', 'cache')
OUTPUT_DIR = os.path.join(project_root, 'output')

def read_stock_list(csv_path):
    """
    读取股票列表
    """
    try:
        df = pd.read_csv(csv_path)
        stock_list = []
        for _, row in df.iterrows():
            stock_list.append({
                'name': row['股票名称'],
                'code': row['股票代码']
            })
        return stock_list
    except Exception as e:
        print(f"读取股票列表失败: {e}")
        return []

def get_stock_data(stock_code, days=60):
    """
    获取股票过去60个自然日的交易数据
    支持缓存机制
    """
    # 生成缓存文件名
    cache_file = os.path.join(CACHE_DIR, f'stock_{stock_code}.json')
    
    # 检查缓存是否存在
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                # 检查缓存是否有效（缓存时间不超过1天）
                cache_time = datetime.fromisoformat(cached_data['cache_time'])
                # 计算时间差（小时）
                time_diff = (datetime.now() - cache_time).total_seconds() / 3600
                if time_diff < 12:
                    print(f"从缓存读取 {stock_code} 数据")
                    return cached_data['data']
        except Exception as e:
            print(f"读取缓存失败: {e}")
    
    # 从akshare获取数据
    print(f"从akshare获取 {stock_code} 数据")
    try:
        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 使用akshare获取股票数据（使用正确的API参数）
        stock_zh_a_daily_df = ak.stock_zh_a_hist(
            symbol=stock_code, 
            period="daily",
            start_date=start_date.strftime('%Y%m%d'), 
            end_date=end_date.strftime('%Y%m%d'), 
            adjust="qfq"
        )
        
        # 转换为列表格式
        data = []
        for _, row in stock_zh_a_daily_df.iterrows():
            # 确保日期是字符串格式
            if '日期' in row:
                date_str = str(row['日期'])
            else:
                continue
            
            # 只获取必要的字段
            item = {
                'date': date_str,
                'close': float(row.get('收盘', 0)),
                'open': float(row.get('开盘', 0)),
                'high': float(row.get('最高', 0)),
                'low': float(row.get('最低', 0)),
                'volume': float(row.get('成交量', 0)),
                'amount': float(row.get('成交额', 0))
            }
            
            # 尝试获取涨跌幅字段
            if '涨跌幅' in row:
                item['change_pct'] = float(row['涨跌幅'])
            else:
                item['change_pct'] = 0
            
            if '涨跌额' in row:
                item['change'] = float(row['涨跌额'])
            else:
                item['change'] = 0
            
            data.append(item)
        
        # 缓存数据
        cache_data = {
            'cache_time': datetime.now().isoformat(),
            'data': data
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        return data
    except Exception as e:
        print(f"获取 {stock_code} 数据失败: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_index_data(index_code, days=60):
    """
    获取指数过去60个自然日的交易数据
    支持缓存机制
    """
    # 生成缓存文件名
    cache_file = os.path.join(CACHE_DIR, f'index_{index_code}.json')
    
    # 检查缓存是否存在
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                # 检查缓存是否有效（缓存时间不超过1天）
                cache_time = datetime.fromisoformat(cached_data['cache_time'])
                # 计算时间差（小时）
                time_diff = (datetime.now() - cache_time).total_seconds() / 3600
                if time_diff < 12:
                    print(f"从缓存读取 {index_code} 数据")
                    return cached_data['data']
        except Exception as e:
            print(f"读取缓存失败: {e}")
    
    # 从akshare获取数据
    print(f"从akshare获取 {index_code} 数据")
    try:
        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 使用akshare获取指数数据（使用正确的API）
        index_df = ak.stock_zh_index_daily(
            symbol=index_code
        )
        
        # 检查是否有日期列（英文列名）
        if 'date' in index_df.columns:
            # 将日期列转换为datetime
            index_df['date'] = pd.to_datetime(index_df['date'])
            # 过滤日期范围
            index_df = index_df[index_df['date'] >= start_date]
            index_df = index_df[index_df['date'] <= end_date]
            
            # 转换为列表格式
            data = []
            for _, row in index_df.iterrows():
                # 确保日期是字符串格式
                if pd.notna(row['date']):
                    date_str = row['date'].strftime('%Y-%m-%d')
                else:
                    continue
                
                # 只获取必要的字段（使用英文列名）
                item = {
                    'date': date_str,
                    'close': float(row.get('close', 0)),
                    'open': float(row.get('open', 0)),
                    'high': float(row.get('high', 0)),
                    'low': float(row.get('low', 0)),
                    'volume': float(row.get('volume', 0)),
                    'amount': 0  # 指数数据可能没有成交额字段
                }
                
                # 指数数据可能没有涨跌幅字段
                item['change_pct'] = 0
                item['change'] = 0
                
                data.append(item)
        else:
            # 如果没有日期列，返回空列表
            data = []
        
        # 缓存数据
        cache_data = {
            'cache_time': datetime.now().isoformat(),
            'data': data
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        return data
    except Exception as e:
        print(f"获取 {index_code} 数据失败: {e}")
        import traceback
        traceback.print_exc()
        return []

def format_stock_code(stock_code):
    """
    格式化股票代码，确保6位数字
    """
    # 确保股票代码是字符串
    stock_code = str(stock_code)
    
    # 补零到6位
    stock_code = stock_code.zfill(6)
    
    return stock_code

def get_market_from_code(stock_code):
    """
    根据股票代码判断所属市场
    """
    # 确保股票代码是6位
    stock_code = str(stock_code).zfill(6)
    
    if stock_code.startswith('6'):
        return 'sh'  # 沪市
    else:
        return 'sz'  # 深市

def get_index_code_by_market(market):
    """
    根据市场获取对应的指数代码
    """
    if market == 'sh':
        return 'sh000002'  # 上证指数
    elif market == 'sz':
        return 'sz399107'  # 深证成指
    elif market == 'kcb':
        return 'sh000688'  # 科创50
    elif market == 'cyb':
        return 'sz399006'  # 创业板指
    elif market == 'bj':
        return 'bj899050'  # 北证50
    else:
        return 'sh000002'  # 默认上证指数

def find_date_range(end_date, days, stock_data):
    """
    寻找日期范围
    从end_date开始倒数，找到days个交易日的起始日期
    """
    cnt = days
    # 从end_date的前一天开始倒数，只保留日期部分
    current_date = (end_date).date()
    
    # 获取今天的日期，只保留日期部分
    today = datetime.now().date()
    # 获取当前时间，判断是否在15点之前
    now = datetime.now()
    is_before_15 = now.hour < 15
    
    # 安全检查：防止日期超出范围
    min_date = datetime(2000, 1, 1).date()  # 设置一个合理的最小日期
    
    print(f"=== 计算日期范围 ===")
    print(f"结束日期: {end_date.strftime('%Y-%m-%d')}")
    print(f"需要倒数天数: {days}")
    print(f"开始从: {current_date} 倒数")
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"是否在15点之前: {is_before_15}")
    
    # 创建股票数据日期集合，方便快速查询，只保留日期部分
    stock_dates = set()
    for item in stock_data:
        try:
            date_str = item['date']
            item_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            stock_dates.add(item_date)
        except Exception:
            continue
    
    
    # 最多计算1000天，防止无限循环
    max_iterations = 1000
    iteration = 0
    
    while cnt > 0 and iteration < max_iterations:
        iteration += 1
        # 检查是否是过去日期，如果当天是交易日，无论任何执行都默认今天是未来时间
        # 根据是否在15点之前调整判断逻辑
        if is_before_15:
            # 15点之前，今天视为未来时间
            if current_date < today:
                # 检查是否有交易数据
                if current_date in stock_dates:
                    cnt -= 1
                    print(f"找到交易日: {current_date}, 剩余天数: {cnt}")
                    # 找到交易日后，继续倒数
                    current_date = current_date - timedelta(days=1)
                else:
                    # 视为节假日，直接跳过
                    current_date = current_date - timedelta(days=1)
            else:
                # 跳过周末
                if current_date.weekday() >= 5:
                    current_date = current_date - timedelta(days=1)
                    continue

                cnt -= 1
                print(f"未来日期: {current_date}, 剩余天数: {cnt}")
                # 继续倒数
                current_date = current_date - timedelta(days=1)
        else:
            # 15点之后，今天视为过去时间
            if current_date <= today:
                # 检查是否有交易数据
                if current_date in stock_dates:
                    cnt -= 1
                    print(f"找到交易日: {current_date}, 剩余天数: {cnt}")
                    # 找到交易日后，继续倒数
                    current_date = current_date - timedelta(days=1)
                else:
                    # 视为节假日，直接跳过
                    current_date = current_date - timedelta(days=1)
            else:
                # 跳过周末
                if current_date.weekday() >= 5:
                    current_date = current_date - timedelta(days=1)
                    continue

                cnt -= 1
                print(f"未来日期: {current_date}, 剩余天数: {cnt}")
                # 继续倒数
                current_date = current_date - timedelta(days=1)
    
    if iteration >= max_iterations:
        print("警告：日期计算达到最大迭代次数，可能数据不足")
    
    print(f"计算完成，起始日期: {current_date}")
    print(f"=== 日期范围计算完成 ===\n")
    
    # 如果超出最小日期范围，返回一个默认日期
    if current_date <= min_date:
        return min_date
    
    return current_date

def find_lowest_price(stock_data, start_date, end_date):
    """
    在指定日期范围内找到最低收盘价
    """
    lowest_price = float('inf')
    lowest_date = None
    
    # 统一日期类型，确保都是date对象
    if hasattr(end_date, 'date'):
        end_date = end_date.date()
    if hasattr(start_date, 'date'):
        start_date = start_date.date()
    
    print(f"查找最低值范围: {start_date} 到 {end_date}")
    
    for item in stock_data:
        try:
            # 只使用YYYY-MM-DD格式
            date_str = item['date']
            item_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        
            if start_date <= item_date <= end_date:
                if item['close'] < lowest_price:
                    lowest_price = item['close']
                    lowest_date = date_str
                    print(f"更新最低值: {lowest_price} at {lowest_date}")
        except Exception as e:
            # 跳过无效的日期格式
            print(f"日期解析错误: {e}")
            continue
    
    # 如果没有找到数据，返回最近的价格
    if lowest_date is None and stock_data:
        # 按日期排序
        sorted_data = []
        for item in stock_data:
            try:
                # 只使用YYYY-MM-DD格式
                date_str = item['date']
                item_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                sorted_data.append((item_date, item))
            except Exception:
                continue
        
        if sorted_data:
            sorted_data.sort(key=lambda x: x[0])
            
            # 找到最接近的日期
            closest_item = None
            min_diff = float('inf')
            
            for item_date, item in sorted_data:
                diff = abs((item_date - end_date).days)
                if diff < min_diff:
                    min_diff = diff
                    closest_item = item
            
            if closest_item:
                lowest_price = closest_item['close']
                lowest_date = closest_item['date']
            else:
                # 如果还是没有找到，返回第一个数据点
                lowest_price = stock_data[0]['close']
                lowest_date = stock_data[0]['date']
        else:
            # 如果没有有效的日期数据，返回第一个数据点
            lowest_price = stock_data[0]['close']
            lowest_date = stock_data[0]['date']
    
    return lowest_price, lowest_date

def calculate_market_change(index_data, start_date, end_date):
    """
    计算指数从start_date到end_date的涨幅
    """
    # 按日期排序
    sorted_index_data = sorted(index_data, key=lambda x: x['date'])
    
    # 找到最接近的起始日期数据
    start_price = None
    for item in sorted_index_data:
        try:
            item_date_str = item['date']
            item_date = datetime.strptime(item_date_str, '%Y-%m-%d').date()
            if item_date <= start_date:
                start_price = item['close']
            else:
                break
        except Exception:
            continue
    
    # 找到最接近的结束日期数据
    end_price = None
    for item in reversed(sorted_index_data):
        try:
            item_date_str = item['date']
            item_date = datetime.strptime(item_date_str, '%Y-%m-%d').date()
            if item_date <= end_date:
                end_price = item['close']
                break
        except Exception:
            continue
    
    if start_price and end_price:
        return (end_price - start_price) / start_price * 100
    else:
        return 0

def calculate_movement_space(stock_data, index_data, end_date, days, percentage):
    """
    计算异动空间
    """
    print(f"\n\n=== 计算异动空间 ===")
    print(f"原始天数: {days}, 调整后天数: {days}")
    print(f"区间终点: {end_date.strftime('%Y-%m-%d')}")
    
    # 调整天数：30日异动使用31天，10日异动使用11天
    adjusted_days = days
    # 找到区间起点
    start_date = find_date_range(end_date, adjusted_days, stock_data)
    
    # 转换为字符串格式
    end_date_str = end_date.strftime('%Y-%m-%d')
    # 检查 start_date 类型，确保能正确转换为字符串
    if hasattr(start_date, 'strftime'):
        start_date_str = start_date.strftime('%Y-%m-%d')
    else:
        start_date_str = str(start_date)
    print(f"区间起点: {start_date_str}")
    
    # 找到最低值（区间起点到区间终点）
    lowest_price, lowest_date = find_lowest_price(stock_data, start_date, end_date)
    print(f"最低值日期: {lowest_date}, 最低值: {lowest_price:.2f}")
    
    # 计算大盘涨跌
    market_change = 0
    if index_data:
        # 将字符串日期转换为 date 对象
        try:
            lowest_date_obj = datetime.strptime(lowest_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            market_change = calculate_market_change(index_data, lowest_date_obj, end_date_obj)
        except Exception as e:
            print(f"计算大盘涨幅时出错: {e}")
        print(f"大盘涨幅: {market_change:.2f}%")
    else:
        print("无指数数据，大盘涨幅默认为0%")
    
    # 计算异动价格（包含大盘涨跌幅）
    adjusted_percentage = percentage + market_change
    movement_price = lowest_price * (1 + adjusted_percentage / 100)
    print(f"异动价格计算: {lowest_price:.2f} * (1 + ({percentage}% + {market_change:.2f}%)) = {movement_price:.2f}")
    
    # 找到最后一个交易日价格
    last_price = None
    last_date = None
    # 获取当前时间，判断是否在15点之前
    now = datetime.now()
    is_before_15 = now.hour < 15
    end_date_only = end_date.date()  # 只保留日期部分
    
    print(f"判断执行时间: {now.strftime('%Y-%m-%d %H:%M:%S')}, 是否在15点之前: {is_before_15}")
    
    if is_before_15:
        # 15点之前，今日作为未来时间，使用昨日作为最后交易日
        # 计算昨日日期
        yesterday = end_date_only - timedelta(days=1)
        print(f"15点之前，使用昨日作为最后交易日: {yesterday}")
        
        # 找到昨日或之前最近的交易日
        for item in reversed(stock_data):
            try:
                item_date_str = item['date']
                item_date = datetime.strptime(item_date_str, '%Y-%m-%d').date()
                if item_date <= yesterday:
                    last_price = item['close']
                    last_date = item_date_str
                    break
            except ValueError:
                continue
    else:
        # 15点之后，今日作为过去时间，使用今日作为最后交易日
        print(f"15点之后，使用今日作为最后交易日: {end_date_only}")
        
        # 找到今日或之前最近的交易日
        for item in reversed(stock_data):
            try:
                item_date_str = item['date']
                item_date = datetime.strptime(item_date_str, '%Y-%m-%d').date()
                if item_date <= end_date_only:
                    last_price = item['close']
                    last_date = item_date_str
                    break
            except ValueError:
                continue
    
    print(f"最后交易日: {last_date}, 最后交易日价格: {last_price:.2f}")
    
    # 计算可涨幅度
    if last_price and movement_price:
        potential_gain = (movement_price - last_price) / last_price * 100
        print(f"可涨幅度计算: ({movement_price:.2f} - {last_price:.2f}) / {last_price:.2f} * 100 = {potential_gain:.2f}%")
    else:
        potential_gain = 0
        print("无法计算可涨幅度，默认为0%")
    
    print(f"=== 计算完成 ===\n\n")
    
    return {
        'start_date': start_date_str,
        'end_date': end_date_str,
        'lowest_date': lowest_date,
        'lowest_price': lowest_price,
        'movement_price': movement_price,
        'last_price': last_price,
        'last_date': last_date,
        '可涨幅度': potential_gain
    }

def analyze_single_stock(stock):
    """
    分析单支股票
    """
    # 格式化股票代码为字符串
    formatted_code = format_stock_code(stock['code'])
    print(f"分析股票: {stock['name']} ({formatted_code})")
    
    try:
        # 获取股票数据
        stock_data = get_stock_data(formatted_code)
        if not stock_data:
            print(f"无法获取 {formatted_code} 的数据，跳过")
            return None
        
        # 获取所属市场
        market = get_market_from_code(formatted_code)
        
        # 获取对应指数数据
        index_code = get_index_code_by_market(market)
        index_data = get_index_data(index_code)
        print(f"获取指数数据: {index_code}, 数据条数: {len(index_data)}")
        # 即使指数数据获取失败，也继续分析股票
        
        # 获取当前日期和时间
        now = datetime.now()
        today = now.date()
        is_before_15 = now.hour < 15
        
        print(f"当前日期: {now}")
        print(f"是否在15点之前: {is_before_15}")
        
        # 预测未来7个交易日
        predictions = []
        # 根据是否在15点之前调整预测起始日期
        if is_before_15:
            # 15点之前，今日作为未来时间的第一日
            current_date = now
            print(f"15点之前，从今日开始预测: {current_date.strftime('%Y-%m-%d')}")
        else:
            # 15点之后，今日作为过去时间，明日作为未来第一日
            current_date = now + timedelta(days=1)
            print(f"15点之后，从明日开始预测: {current_date.strftime('%Y-%m-%d')}")
        
        count = 0
        while count < 20:
            # 检查是否是周末（0-4是工作日，5-6是周末）
            if current_date.weekday() < 5:
                predict_date = current_date
                print(f"预测日期 {count+1}: {predict_date}")
                
                # 计算30日200%异动空间
                print(f"计算30日异动空间...")
                space_30_200 = calculate_movement_space(stock_data, index_data, predict_date, 30, 200)
                print(f"30日异动空间计算完成")
                
                # 计算10日100%异动空间
                print(f"计算10日异动空间...")
                space_10_100 = calculate_movement_space(stock_data, index_data, predict_date, 10, 100)
                print(f"10日异动空间计算完成")
                
                predictions.append({
                    'date': predict_date,
                    'space_30_200': space_30_200,
                    'space_10_100': space_10_100
                })
                count += 1
            # 无论是否是工作日，都增加一天
            current_date += timedelta(days=1)
        
        return {
            'stock': stock,
            'formatted_code': formatted_code,
            'predictions': predictions
        }
    except Exception as e:
        print(f"分析股票 {stock['name']} 时出错: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_font_path():
    """
    获取系统中可用的中文字体路径（优先黑体）
    """
    font_paths = {
        'windows': [
            'C:/Windows/Fonts/simhei.ttf',
            'C:/Windows/Fonts/msyh.ttc',
            'C:/Windows/Fonts/simsun.ttc',
        ],
        'linux': [
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        ],
        'darwin': [
            '/Library/Fonts/SimHei.ttf',
            '/System/Library/Fonts/PingFang.ttc',
            '/Library/Fonts/Songti.ttc',
        ]
    }
    
    import platform
    system = platform.system().lower()
    
    if system == 'windows':
        paths = font_paths['windows']
    elif system == 'linux':
        paths = font_paths['linux']
    elif system == 'darwin':
        paths = font_paths['darwin']
    else:
        paths = font_paths['windows'] + font_paths['linux'] + font_paths['darwin']
    
    for path in paths:
        if os.path.exists(path):
            return path
    return None

def plot_stock_movement(stock_name, stock_code, predictions, output_dir):
    """
    生成股票异动价格折线图
    :param stock_name: 股票名称
    :param stock_code: 股票代码
    :param predictions: 预测数据列表
    :param output_dir: 输出目录
    """
    font_path = get_font_path()
    if font_path:
        font_prop = FontProperties(fname=font_path)
    else:
        font_prop = None
    
    dates = []
    movement_prices = []
    last_price = None
    
    for pred in predictions:
        dates.append(pred['date'])
        space_10_100 = pred['space_10_100']
        space_30_200 = pred['space_30_200']
        
        if space_10_100['movement_price'] < space_30_200['movement_price']:
            movement_prices.append(space_10_100['movement_price'])
            last_price = space_10_100['last_price']
        else:
            movement_prices.append(space_30_200['movement_price'])
            last_price = space_30_200['last_price']
    
    plt.figure(figsize=(12, 7), dpi=120)
    ax = plt.subplot(111)
    
    ax.plot(dates, movement_prices, color='#2E86AB', linewidth=2.5, marker='o', 
            markersize=10, markerfacecolor='#F6AE2D', markeredgecolor='#2E86AB',
            markeredgewidth=2, label='Movement Price')
    
    for i, (date, price) in enumerate(zip(dates, movement_prices)):
        # 交替放置价格标签，避免重叠
        if i % 2 == 0:
            # 偶数索引放在节点上方
            xytext = (0, 15)
            va = 'bottom'
        else:
            # 奇数索引放在节点下方
            xytext = (0, -25)
            va = 'top'
        
        ax.annotate(f'{price:.2f}', xy=(date, price), xytext=xytext,
                   textcoords='offset points', ha='center', va=va,
                   fontsize=10, fontweight='normal', color='#264653',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='#F6AE2D', 
                            edgecolor='#2E86AB', alpha=0.8),
                   arrowprops=dict(arrowstyle='-', linestyle='--', 
                                  color='#999999', linewidth=1.0))
    
    if last_price:
        ax.axhline(y=last_price, color='#E94F37', linestyle='--', 
                   linewidth=2, label=f'Current Price: {last_price:.2f}')
    
    date_labels = [d.strftime('%m-%d') for d in dates]
    ax.set_xticks(dates)
    ax.set_xticklabels(date_labels, fontsize=10)
    
    title_text = f'{stock_name} ({stock_code})'
    if font_prop:
        # 创建标题字体（加粗）
        title_font = FontProperties(fname=font_prop.get_file(), size=24)
        ax.set_title(title_text, fontsize=24, fontweight='bold', 
                    color='#1A365D', fontproperties=title_font, 
                    loc='center', y=1.01)
        ax.set_xlabel('未来20日异动价格', fontsize=12, fontproperties=font_prop)
        ax.set_ylabel('Price (CNY)', fontsize=12, fontproperties=font_prop)
        legend = ax.legend(loc='upper left', fontsize=10, framealpha=0.9)
    else:
        ax.set_title(title_text, fontsize=24, fontweight='bold', 
                    color='#1A365D', loc='center', y=1.01)
        ax.set_xlabel('Predict Date', fontsize=12)
        ax.set_ylabel('Price (CNY)', fontsize=12)
        legend = ax.legend(loc='upper left', fontsize=10, framealpha=0.9)
    
    ax.grid(True, linestyle=':', alpha=0.6, color='#888888')
    ax.set_facecolor('#FAFAFA')
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    
    png_dir = os.path.join(output_dir, 'png')
    os.makedirs(png_dir, exist_ok=True)
    
    filename = f'{stock_name}_{stock_code}.png'
    filepath = os.path.join(png_dir, filename)
    
    plt.savefig(filepath, dpi=120, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    plt.close()
    
    print(f"折线图已保存: {filepath}")

def analyze_stocks(csv_path=DEFAULT_STOCK_CSV_PATH):
    """
    分析股票
    """
    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 读取股票列表
    stock_list = read_stock_list(csv_path)
    print(f"读取到 {len(stock_list)} 支股票")
    
    # 获取当前日期
    today = datetime.now()
    date_str = today.strftime('%Y%m%d')
    
    # 创建日期子文件夹
    date_output_dir = os.path.join(OUTPUT_DIR, date_str)
    os.makedirs(date_output_dir, exist_ok=True)
    
    # 准备CSV输出文件
    # 从CSV路径提取文件名（不含扩展名）
    csv_filename = os.path.basename(csv_path)
    base_name = os.path.splitext(csv_filename)[0]
    output_filename = f"analysis_{base_name}.csv"
    output_file = os.path.join(date_output_dir, output_filename)
    
    # 准备MD输出文件
    md_output_filename = f"analysis_{base_name}.md"
    md_output_file = os.path.join(date_output_dir, md_output_filename)
    
    # 写入CSV头部
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("股票名称,股票代码,预测日期,区间起点,区间终点,最低值日期,最低值,异动类型,异动价格,最后交易日价格,可涨幅度\n")
    
    # 写入MD头部和表格头部
    with open(md_output_file, 'w', encoding='utf-8') as f:
        f.write(f"# 股票异动分析报告\n\n")
        f.write(f"生成日期: {today.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("免责声明：仅供学习参考，不作为任何投资建议，请谨慎对待。\n1. 因未来时间大盘偏移无法估算，因此第二日及之后的异动价格只作预估！\n2. 可涨幅度按照最后交易日收盘价计算，未进行复利叠加，请自行换算！\n\n\n\n\n\n\n")
    
    # 使用线程池并行分析股票
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 提交所有股票分析任务
        future_to_stock = {executor.submit(analyze_single_stock, stock): stock for stock in stock_list}
        
        # 收集结果
        for future in future_to_stock:
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                print(f"分析股票时出错: {e}")
    
    # 处理结果并写入文件
    for result in results:
        stock = result['stock']
        formatted_code = result['formatted_code']
        predictions = result['predictions']
        
        # 写入合并异动数据
        with open(output_file, 'a', encoding='utf-8') as f_csv, open(md_output_file, 'a', encoding='utf-8') as f_md:
            # 为每支股票创建一个单独的表格，添加表头
            f_md.write(f"## {stock['name']} ({formatted_code})\n\n")
            f_md.write("| 股票名称 | 股票代码 | 预测日期 | 区间起点 | 区间终点 | 最低值日期 | 最低值 | 异动类型 | 异动价格 | 最后交易日价格 | 可涨幅度 |\n")
            f_md.write("|---------|---------|---------|---------|---------|---------|---------|---------|---------|---------|---------|\n")
            
            for pred in predictions:
                predict_date_str = pred['date'].strftime('%Y-%m-%d')
                space_10_100 = pred['space_10_100']
                space_30_200 = pred['space_30_200']
                
                # 比较异动价格，选择更低的
                if space_10_100['movement_price'] < space_30_200['movement_price']:
                    # 选择10日异动数据
                    selected_data = space_10_100
                    movement_type = "10日异动"
                else:
                    # 选择30日异动数据
                    selected_data = space_30_200
                    movement_type = "30日异动"
                
                # 写入CSV
                f_csv.write(f"{stock['name']},{formatted_code},{predict_date_str},{selected_data['start_date']},{selected_data['end_date']},{selected_data['lowest_date']},{selected_data['lowest_price']:.2f},{movement_type},{selected_data['movement_price']:.2f},{selected_data['last_price']:.2f},{selected_data['可涨幅度']:.2f}%\n")
                
                # 写入MD表格行
                f_md.write(f"| {stock['name']} | {formatted_code} | {predict_date_str} | {selected_data['start_date']} | {selected_data['end_date']} | {selected_data['lowest_date']} | {selected_data['lowest_price']:.2f} | {movement_type} | {selected_data['movement_price']:.2f} | {selected_data['last_price']:.2f} | {selected_data['可涨幅度']:.2f}% |\n")
            
            # 每支股票输出完空一行
            f_csv.write("\n")
            # 在MD文件中每支股票之间也添加空行
            f_md.write("\n")
            
            # 生成折线图
            plot_stock_movement(stock['name'], formatted_code, predictions, date_output_dir)
    
    print(f"\n分析完成，结果保存到:")
    print(f"合并异动 (CSV): {output_file}")
    print(f"合并异动 (MD): {md_output_file}")

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='股票异动分析工具')
    parser.add_argument('--file', type=str, default=DEFAULT_STOCK_CSV_PATH, 
                        help='指定股票标的CSV文件路径，默认使用 data/stock.csv')
    
    args = parser.parse_args()
    
    # 运行分析
    analyze_stocks(args.file)