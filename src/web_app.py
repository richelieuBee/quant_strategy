import os
import sys
import shutil
import argparse
from datetime import datetime, timedelta

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# 配置matplotlib字体
def configure_matplotlib_fonts():
    import matplotlib
    matplotlib.use('Agg')
    
    # 定义可能的中文字体路径（按优先级排序）
    font_paths = [
        '/usr/share/fonts/chinese/NotoSansCJKsc.otf',
        '/usr/share/fonts/chinese/NotoSansCJKsc-Regular.otf',
        '/usr/share/fonts/chinese/NotoSansCJKsc-Regular.ttf',
        '/usr/share/fonts/google-noto-vf/NotoSansCJKsc-Regular.otf',
        '/usr/share/fonts/google-noto-vf/NotoSansCJKsc-subset.otf',
        '/usr/share/fonts/google-noto-vf/NotoSansSC-Regular.otf',
        '/usr/share/fonts/wqy-microhei/wqy-microhei.ttc',
        '/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc',
        'C:/Windows/Fonts/simhei.ttf',
        'C:/Windows/Fonts/msyh.ttc',
    ]
    
    # 清除matplotlib字体缓存
    matplotlib_cache_dir = matplotlib.get_cachedir()
    print(f"matplotlib缓存目录: {matplotlib_cache_dir}")
    
    # 找到第一个存在的字体
    found_font = None
    for font_path in font_paths:
        if os.path.exists(font_path):
            found_font = font_path
            print(f"找到中文字体: {font_path}")
            break
    
    # 配置matplotlib
    import matplotlib.pyplot as plt
    if found_font:
        font_name = os.path.basename(found_font).replace('.otf', '').replace('.ttf', '')
        plt.rcParams['font.sans-serif'] = [font_name]
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['axes.unicode_minus'] = False
        print(f"使用中文字体配置: {found_font}")
    else:
        print("警告：未找到中文字体，尝试使用系统字体...")
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
    
    return found_font

# 配置字体
CHINESE_FONT_PATH = configure_matplotlib_fonts()

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties
from flask import Flask, render_template, request, jsonify
from io import BytesIO
import base64
import json
import time

from src.analyze_stock import (
    format_stock_code,
    get_market_from_code,
    get_market_category,
    get_market_threshold,
    get_index_code_by_market,
    get_stock_data,
    get_index_data,
    calculate_movement_space,
    analyze_single_stock,
    get_font_path,
    read_stock_list
)
from stock_search import search_stocks

app = Flask(__name__)

CACHE_PNG_DIR = os.path.join(project_root, 'data', 'cache_png')

def get_trading_day():
    """
    获取当前交易日
    - 15点之前：使用昨日作为最后交易日
    - 15点之后：使用今日作为最后交易日
    """
    now = datetime.now()
    today = now.date()
    
    if now.hour < 15:
        # 15点之前，使用昨日
        trading_day = today - timedelta(days=1)
    else:
        # 15点之后，使用今日
        trading_day = today
    
    # 如果是周末，向前找到最近的工作日
    while trading_day.weekday() >= 5:
        trading_day = trading_day - timedelta(days=1)
    
    return trading_day

def get_trading_day_str():
    """获取当前交易日字符串 YYYYMMDD"""
    trading_day = get_trading_day()
    return trading_day.strftime('%Y%m%d')

def clean_old_cache(days=7):
    """删除超过指定天数的缓存目录"""
    if not os.path.exists(CACHE_PNG_DIR):
        return
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    for folder_name in os.listdir(CACHE_PNG_DIR):
        folder_path = os.path.join(CACHE_PNG_DIR, folder_name)
        if os.path.isdir(folder_path):
            try:
                # 尝试解析文件夹名称为日期
                folder_date = datetime.strptime(folder_name, '%Y%m%d')
                if folder_date < cutoff_date:
                    shutil.rmtree(folder_path)
                    print(f"删除过期缓存目录: {folder_path}")
            except ValueError:
                # 不是有效的日期格式，跳过
                continue

def get_cache_file_path(stock_name, stock_code):
    """获取缓存文件路径"""
    trading_day_str = get_trading_day_str()
    cache_folder = os.path.join(CACHE_PNG_DIR, trading_day_str)
    os.makedirs(cache_folder, exist_ok=True)
    
    # 使用股票名称和代码生成文件名
    filename = f'{stock_name}_{stock_code}.png'
    return os.path.join(cache_folder, filename)

def load_cached_png(stock_name, stock_code):
    """从缓存加载PNG图片"""
    cache_path = get_cache_file_path(stock_name, stock_code)
    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            return f.read()
    return None

def save_png_to_cache(stock_name, stock_code, png_data):
    """保存PNG图片到缓存"""
    cache_path = get_cache_file_path(stock_name, stock_code)
    with open(cache_path, 'wb') as f:
        f.write(png_data)

def search_stock_by_name(stock_name):
    data_dir = os.path.join(project_root, 'data')
    if os.path.exists(data_dir):
        for csv_file in os.listdir(data_dir):
            if csv_file.endswith('.csv'):
                csv_path = os.path.join(data_dir, csv_file)
                try:
                    stock_list = read_stock_list(csv_path)
                    for stock in stock_list:
                        if stock['name'] == stock_name:
                            return stock['name'], stock['code']
                except Exception:
                    continue
    return None, None

def search_stock_by_code(stock_code):
    data_dir = os.path.join(project_root, 'data')
    if os.path.exists(data_dir):
        for csv_file in os.listdir(data_dir):
            if csv_file.endswith('.csv'):
                csv_path = os.path.join(data_dir, csv_file)
                try:
                    stock_list = read_stock_list(csv_path)
                    for stock in stock_list:
                        if format_stock_code(stock['code']) == format_stock_code(stock_code):
                            return stock['name'], stock['code']
                except Exception:
                    continue
    return None, None

def plot_stock_movement_to_buffer(stock_name, stock_code, predictions, market_category='main'):
    font_path = get_font_path()
    if font_path:
        font_prop = FontProperties(fname=font_path)
    else:
        font_prop = None

    threshold = get_market_threshold(market_category)
    threshold_pct = int(threshold * 100)
    
    dates = []
    movement_prices = []
    last_prices = []
    
    for pred in predictions:
        dates.append(pred['date'])
        space_10_100 = pred['space_10_100']
        space_30_200 = pred['space_30_200']
        
        if space_10_100['movement_price'] < space_30_200['movement_price']:
            movement_prices.append(space_10_100['movement_price'])
            last_prices.append(space_10_100['last_price'])
        else:
            movement_prices.append(space_30_200['movement_price'])
            last_prices.append(space_30_200['last_price'])
    
    plt.figure(figsize=(18, 7), dpi=120)
    ax = plt.subplot(111)
    
    ax.plot(dates, movement_prices, color='#2E86AB', linewidth=2.5, label='Movement Price')
    
    has_warning = False

    for i, (date, price, current_price) in enumerate(zip(dates, movement_prices, last_prices)):
        if current_price > 0:
            increase = (price - current_price) / current_price
            if increase > threshold:
                marker_color = '#F6AE2D'
                marker_edge = '#D49A00'
            else:
                marker_color = '#E94F37'
                marker_edge = '#C73E3E'
                has_warning = True
        else:
            marker_color = '#E94F37'
            marker_edge = '#C73E3E'

        ax.scatter(date, price, s=120, marker='o', color=marker_color,
                   edgecolor=marker_edge, linewidth=2, zorder=5)

    import matplotlib.lines as mlines

    legend_font_prop = font_prop if font_prop else None

    red_marker = mlines.Line2D([], [], marker='o', color='#E94F37', linestyle='None',
                               markersize=10, markerfacecolor='#E94F37',
                               markeredgecolor='#C73E3E', label=f'剩余涨幅<={threshold_pct}%')
    yellow_marker = mlines.Line2D([], [], marker='o', color='#F6AE2D', linestyle='None',
                                  markersize=10, markerfacecolor='#F6AE2D',
                                  markeredgecolor='#D49A00', label=f'剩余涨幅>{threshold_pct}%')
    
    current_price_line = mlines.Line2D([], [], color='#E94F37', linestyle='--', 
                                       linewidth=2, label='')
    
    for i, (date, price) in enumerate(zip(dates, movement_prices)):
        if i % 2 == 0:
            xytext = (0, 15)
            va = 'bottom'
        else:
            xytext = (0, -25)
            va = 'top'
        
        ax.annotate(f'{price:.2f}', xy=(date, price), xytext=xytext,
                   textcoords='offset points', ha='center', va=va,
                   fontsize=10, fontweight='normal', color='#264653',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='#F6AE2D', 
                            edgecolor='#2E86AB', alpha=0.8),
                   arrowprops=dict(arrowstyle='-', linestyle='--', 
                                  color='#999999', linewidth=1.0))
    
    if last_prices and last_prices[0] > 0:
        current_price = last_prices[0]
        ax.axhline(y=current_price, color='#E94F37', linestyle='--', 
                   linewidth=2)
        current_price_line.set_label(f'当前价格: {current_price:.2f}')
    
    date_labels = [d.strftime('%m-%d') for d in dates]
    ax.set_xticks(dates)
    ax.set_xticklabels(date_labels, fontsize=10)
    
    title_text = f'股票异动价一览：{stock_name} ({stock_code})'
    if font_prop:
        title_font = FontProperties(fname=font_prop.get_file(), size=18)
        ax.set_title(title_text, fontsize=18, fontweight='bold', 
                    color='#1A365D', fontproperties=title_font, 
                    loc='center', y=1.01)
        ax.set_xlabel('未来30个交易日异动价格', fontsize=12, fontproperties=font_prop)
        ax.set_ylabel('Price (CNY)', fontsize=12, fontproperties=font_prop)
        legend = ax.legend(handles=[red_marker, yellow_marker, current_price_line], 
                          loc='upper left', fontsize=10, framealpha=0.9, 
                          prop=legend_font_prop)
    else:
        ax.set_title(title_text, fontsize=18, fontweight='bold', 
                    color='#1A365D', loc='center', y=1.01)
        ax.set_xlabel('Predict Date', fontsize=12)
        ax.set_ylabel('Price (CNY)', fontsize=12)
        legend = ax.legend(handles=[red_marker, yellow_marker, current_price_line], 
                          loc='upper left', fontsize=10, framealpha=0.9)
    
    ax.grid(True, linestyle=':', alpha=0.6, color='#888888')
    ax.set_facecolor('#FAFAFA')
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    
    img_buffer = BytesIO()
    plt.savefig(img_buffer, dpi=120, bbox_inches='tight',
                facecolor='white', edgecolor='none', format='png')
    plt.close()
    img_buffer.seek(0)
    
    return img_buffer

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['GET'])
def search():
    """模糊搜索股票"""
    query = request.args.get('q', '').strip()
    print(f"[DEBUG] 搜索请求: query='{query}'")
    if not query:
        print("[DEBUG] 查询为空")
        return jsonify({'success': True, 'stocks': []})

    print("[DEBUG] 调用 search_stocks...")
    results = search_stocks(query, limit=10)
    print(f"[DEBUG] 搜索结果: {len(results)} 条")
    if results:
        print(f"[DEBUG] 第一条结果: {results[0]}")
    return jsonify({
        'success': True,
        'stocks': results
    })

@app.route('/api/test')
def test():
    """测试接口"""
    print("[DEBUG] 测试接口被调用")
    return jsonify({'success': True, 'message': '测试成功'})

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    stock_input = data.get('stock', '').strip()

    if not stock_input:
        return jsonify({'error': '请输入股票名称或代码'})

    stock_name = None
    stock_code = None

    if stock_input.isdigit():
        stock_code = format_stock_code(stock_input)
        found_name, found_code = search_stock_by_code(stock_code)
        if found_name:
            stock_name = found_name
        else:
            stock_name = stock_code
    else:
        stock_name, stock_code = search_stock_by_name(stock_input)
        if not stock_name or not stock_code:
            # 本地CSV找不到，尝试从全市场股票中搜索
            full_market_results = search_stocks(stock_input, limit=1)
            if full_market_results:
                stock_name = full_market_results[0]['name']
                stock_code = full_market_results[0]['code']

    if not stock_name or not stock_code:
        return jsonify({'error': f'未找到股票: {stock_input}'})

    # 尝试从缓存加载
    cached_png = load_cached_png(stock_name, stock_code)
    if cached_png:
        print(f"从缓存加载 {stock_name} ({stock_code}) 的PNG")
        img_base64 = base64.b64encode(cached_png).decode('utf-8')
        return jsonify({
            'success': True,
            'stock_name': stock_name,
            'stock_code': stock_code,
            'image': f'data:image/png;base64,{img_base64}',
            'from_cache': True
        })

    # 缓存未命中，重新计算
    result = analyze_single_stock({'name': stock_name, 'code': stock_code})
    if not result:
        return jsonify({'error': f'无法获取 {stock_code} 的数据'})

    img_buffer = plot_stock_movement_to_buffer(
        result['stock']['name'],
        result['formatted_code'],
        result['predictions'],
        result['market_category']
    )

    png_data = img_buffer.getvalue()
    
    # 保存到缓存
    save_png_to_cache(stock_name, stock_code, png_data)
    
    img_base64 = base64.b64encode(png_data).decode('utf-8')

    return jsonify({
        'success': True,
        'stock_name': result['stock']['name'],
        'stock_code': result['formatted_code'],
        'image': f'data:image/png;base64,{img_base64}',
        'from_cache': False
    })

@app.route('/api/cache-list')
def cache_list():
    """获取今日缓存的股票列表"""
    trading_day_str = get_trading_day_str()
    cache_folder = os.path.join(CACHE_PNG_DIR, trading_day_str)
    
    if not os.path.exists(cache_folder):
        return jsonify({'success': True, 'cached_stocks': []})
    
    cached_stocks = []
    
    for filename in os.listdir(cache_folder):
        if filename.endswith('.png'):
            name_parts = filename[:-4].split('_')
            if len(name_parts) >= 2:
                stock_name = '_'.join(name_parts[:-1])
                stock_code = name_parts[-1]
                
                file_path = os.path.join(cache_folder, filename)
                mtime = os.path.getmtime(file_path)
                cache_time = datetime.fromtimestamp(mtime).strftime('%H:%M:%S')
                
                status_path = file_path.replace('.png', '_status.json')
                has_warning = False
                if os.path.exists(status_path):
                    try:
                        with open(status_path, 'r', encoding='utf-8') as f:
                            status_data = json.load(f)
                            has_warning = status_data.get('has_warning', False)
                    except Exception:
                        pass
                
                cached_stocks.append({
                    'name': stock_name,
                    'code': stock_code,
                    'cache_time': cache_time,
                    'has_warning': has_warning
                })
    
    # 按警告状态排序（有红点的置顶），然后按缓存时间排序
    cached_stocks.sort(key=lambda x: (-x['has_warning'], x['cache_time']))
    
    return jsonify({'success': True, 'cached_stocks': cached_stocks})

@app.route('/api/load-cached', methods=['POST'])
def load_cached():
    """加载缓存的PNG图片"""
    data = request.get_json()
    stock_name = data.get('stock_name')
    stock_code = data.get('stock_code')
    
    if not stock_name or not stock_code:
        return jsonify({'success': False, 'error': '参数错误'})
    
    cached_png = load_cached_png(stock_name, stock_code)
    if not cached_png:
        return jsonify({'success': False, 'error': '缓存不存在'})
    
    img_base64 = base64.b64encode(cached_png).decode('utf-8')
    
    return jsonify({
        'success': True,
        'image': f'data:image/png;base64,{img_base64}'
    })

def get_csv_files_to_process(csv_file=None):
    """获取需要处理的CSV文件列表"""
    if csv_file and os.path.exists(csv_file):
        return [csv_file]
    
    # 默认路径
    csv_files = [
        os.path.join(project_root, 'data', 'stock_may.csv')
    ]
    return [f for f in csv_files if os.path.exists(f)]

def check_today_cache_complete(csv_file=None):
    """检查今日缓存是否完整"""
    trading_day_str = get_trading_day_str()
    cache_folder = os.path.join(CACHE_PNG_DIR, trading_day_str)
    
    if not os.path.exists(cache_folder):
        return False
    
    cached_codes = set()
    for filename in os.listdir(cache_folder):
        if filename.endswith('.png'):
            name_parts = filename[:-4].split('_')
            if len(name_parts) >= 2:
                cached_codes.add(name_parts[-1])
    
    for csv_file_path in get_csv_files_to_process(csv_file):
        stock_list = read_stock_list(csv_file_path)
        for stock in stock_list:
            if format_stock_code(stock['code']) not in cached_codes:
                return False
    
    return True

def check_predictions_has_warning(predictions, threshold):
    """检测predictions中是否存在红点（警告）"""
    for pred in predictions:
        space_10_100 = pred['space_10_100']
        space_30_200 = pred['space_30_200']
        
        movement_price = space_10_100['movement_price'] if space_10_100['movement_price'] < space_30_200['movement_price'] else space_30_200['movement_price']
        last_price = space_10_100['last_price'] if space_10_100['movement_price'] < space_30_200['movement_price'] else space_30_200['last_price']
        
        if last_price > 0:
            increase = (movement_price - last_price) / last_price
            if increase <= threshold:
                return True
    return False

def batch_generate_cache(csv_file=None):
    """批量生成今日所有股票的PNG缓存"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始批量生成缓存...")
    
    trading_day_str = get_trading_day_str()
    cache_folder = os.path.join(CACHE_PNG_DIR, trading_day_str)
    os.makedirs(cache_folder, exist_ok=True)
    
    total_count = 0
    success_count = 0
    
    for csv_file_path in get_csv_files_to_process(csv_file):
        stock_list = read_stock_list(csv_file_path)
        
        for stock in stock_list:
            total_count += 1
            stock_name = stock['name']
            stock_code = stock['code']
            formatted_code = format_stock_code(stock_code)
            
            cache_path = os.path.join(cache_folder, f'{stock_name}_{formatted_code}.png')
            
            if os.path.exists(cache_path):
                print(f"  跳过 (已存在): {stock_name} ({formatted_code})")
                success_count += 1
                continue
            
            try:
                print(f"  生成中: {stock_name} ({formatted_code})...", end=' ')
                
                result = analyze_single_stock({'name': stock_name, 'code': formatted_code})
                if not result:
                    print("数据获取失败")
                    continue
                
                threshold = get_market_threshold(result['market_category'])
                has_warning = check_predictions_has_warning(result['predictions'], threshold)
                
                img_buffer = plot_stock_movement_to_buffer(
                    result['stock']['name'],
                    result['formatted_code'],
                    result['predictions'],
                    result['market_category']
                )
                
                png_data = img_buffer.getvalue()
                with open(cache_path, 'wb') as f:
                    f.write(png_data)
                
                status_path = cache_path.replace('.png', '_status.json')
                with open(status_path, 'w', encoding='utf-8') as f:
                    json.dump({'has_warning': has_warning}, f)
                
                success_count += 1
                print("成功")
                
            except Exception as e:
                print(f"失败: {e}")
            
            time.sleep(0.5)
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 缓存生成完成: {success_count}/{total_count} 成功")
    return success_count, total_count

def run_scheduler():
    """运行定时任务调度器"""
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    
    scheduler = BackgroundScheduler()
    
    scheduler.add_job(
        func=batch_generate_cache,
        trigger=CronTrigger(hour=15, minute=30),
        id='batch_generate_cache',
        name='每日15:30批量生成股票缓存',
        replace_existing=True
    )
    
    scheduler.start()
    print("定时任务调度器已启动 (每日 15:30 执行)")
    
    return scheduler

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='股票异动分析Web应用')
    parser.add_argument('--file', type=str, default=None, help='股票列表CSV文件路径')
    args = parser.parse_args()
    
    os.makedirs(CACHE_PNG_DIR, exist_ok=True)
    clean_old_cache(7)
    
    print(f"当前交易日: {get_trading_day_str()}")
    print(f"缓存目录: {CACHE_PNG_DIR}")
    if args.file:
        print(f"使用股票列表文件: {args.file}")
    
    if not check_today_cache_complete(args.file):
        print("检测到今日缓存未完成，开始生成...")
        batch_generate_cache(args.file)
    else:
        print("今日缓存已完整")
    
    scheduler = run_scheduler()
    
    try:
        app.run(debug=False, host='0.0.0.0', port=5000)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()