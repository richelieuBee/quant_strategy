import os
import pandas as pd
import argparse
from datetime import datetime

def get_market_from_code(stock_code):
    """
    根据股票代码判断所属市场
    """
    # 确保股票代码是6位
    stock_code = str(stock_code).zfill(6)
    
    if stock_code.startswith('6'):
        if stock_code.startswith('688'):
            return 'kcb'  # 科创板
        else:
            return 'sh'  # 沪市
    elif stock_code.startswith('3'):
        return 'cyb'  # 创业板
    elif stock_code.startswith('8'):
        return 'bj'  # 北交所
    else:
        return 'sz'  # 深市

def get_limit_up_percentage(market):
    """
    根据市场获取对应的涨停幅度
    """
    if market == 'sh' or market == 'sz':
        return 1.10  # 沪市、深市主板 10%
    elif market == 'kcb' or market == 'cyb' or market == 'bj':
        return 1.20  # 科创板、创业板、北交所 20%
    else:
        return 1.10  # 默认 10%

def parse_args():
    """
    解析命令行参数
    """
    parser = argparse.ArgumentParser(description='使用贪心算法分析股票收益')
    parser.add_argument('--file', type=str, required=True, help='包含股票异动情况的文件路径或文件夹路径')
    return parser.parse_args()

def analyze_stock_profit(path):
    """
    使用新算法分析股票收益
    """
    # 检查路径是文件还是文件夹
    if os.path.isfile(path):
        # 如果是文件，直接使用
        merged_df_path = path
    else:
        # 如果是文件夹，使用原来的逻辑
        merged_df_path = os.path.join(path, 'analysis_合并异动.csv')
    
    # 读取数据
    try:
        df = pd.read_csv(merged_df_path)
    except Exception as e:
        print(f"读取文件时出错: {e}")
        return []
    
    # 按股票名称和日期排序
    df = df.sort_values(['股票名称', '预测日期'])
    
    # 初始化结果列表
    results = []
    
    # 对每只股票进行计算
    for name, group in df.groupby('股票名称'):
        # 确保按日期排序
        group = group.sort_values('预测日期').reset_index(drop=True)
        
        # 买入价（取第一个交易日的最后一个交易日价格）
        buy_price = group.loc[0, '最后交易日价格']
        
        # 获取股票代码
        stock_code = group.loc[0, '股票代码']
        
        # 获取市场类型
        market = get_market_from_code(stock_code)
        
        # 获取涨停幅度
        limit_up_percentage = get_limit_up_percentage(market)
        
        # 初始化当前价格
        current_price = buy_price
        prev_current = buy_price  # 前一天的价格，用于计算是否涨停
        
        # 初始化最佳收益
        max_return = 0.0
        best_sell_day = 0
        best_sell_price = buy_price
        best_sell_date = None
        
        # 初始化连续涨停跟踪
        current_consecutive = 0
        max_consecutive = 0
        start_date = None
        current_start_date = None
        
        # 遍历每一天
        for i in range(len(group)):
            # 获取当日的限制价（使用合并文件中的异动价格）
            limit_price = group.loc[i, '异动价格']
            
            # 计算潜在价格（涨停价）
            potential_price = prev_current * limit_up_percentage
            
            # 计算当日可能达到的最高价（涨停价与限制价的较小值）
            current_price = min(limit_price, potential_price)
            
            # 判断是否涨停（达到潜在涨停价）
            is_limit_up = (current_price == potential_price)
            
            # 跟踪连续涨停
            if is_limit_up:
                if current_consecutive == 0:
                    current_start_date = group.loc[i, '预测日期']
                current_consecutive += 1
                if current_consecutive > max_consecutive:
                    max_consecutive = current_consecutive
                    start_date = current_start_date
            else:
                current_consecutive = 0
            
            # 计算收益率
            return_rate = (current_price / buy_price - 1) * 100  # 转换为百分比
            
            # 如果当前收益率更高，则更新最佳卖出信息
            if return_rate > max_return:
                max_return = return_rate
                best_sell_day = i + 1  # 第i天（从1开始计数）
                best_sell_price = current_price
                best_sell_date = group.loc[i, '预测日期']
            
            # 更新前一天的价格
            prev_current = current_price
        
        # 将结果保存到列表
        results.append({
            '股票名称': name,
            '股票代码': group.loc[0, '股票代码'],
            '买入价': buy_price,
            '最佳卖出日': best_sell_day,
            '最佳卖出日期': best_sell_date,
            '最佳卖出价': best_sell_price,
            '最大收益率': max_return,
            '最大连续涨停天数': max_consecutive,
            '涨停开始日期': start_date,
            '连板结束日期': best_sell_date if max_consecutive > 0 else None,
            '连板收益': (prev_current / buy_price - 1) * 100 if max_consecutive > 0 else 0
        })
    
    return results

def main():
    """
    主函数
    """
    # 解析命令行参数
    args = parse_args()
    path = args.file
    
    # 验证路径是否存在
    if not os.path.exists(path):
        print(f"路径 {path} 不存在")
        return
    
    # 分析股票收益
    print("正在分析股票收益...")
    results = analyze_stock_profit(path)
    
    if not results:
        print("未找到有效的股票数据")
        return
    
    # 创建结果DataFrame并排序
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('最大收益率', ascending=False)
    
    # 输出结果
    print("=" * 120)
    print("股票最大收益排名（允许提前卖出，追求收益最大化）")
    print("=" * 120)
    print(f"{'排名':<4} {'股票名称':<10} {'代码':<10} {'最大收益率':<12} {'最佳卖出日':<12} {'最佳卖出价':<12} {'买入价':<10} {'最大连续涨停天数':<12} {'涨停开始日期':<12}")
    print("-" * 120)
    
    for i, (_, row) in enumerate(results_df.iterrows(), 1):
        try:
            # 处理可能为None的字段
            stock_name = row.get('股票名称', '未知')
            stock_code = row.get('股票代码')
            stock_code_str = str(stock_code).zfill(6) if stock_code is not None else '未知'
            max_return = row.get('最大收益率', 0)
            best_sell_day = row.get('最佳卖出日', 0)
            best_sell_price = row.get('最佳卖出价', 0)
            buy_price = row.get('买入价', 0)
            max_consecutive = row.get('最大连续涨停天数', 0)
            start_date = row.get('涨停开始日期', '未知')
            
            # 确保所有值都不是None
            stock_name = stock_name or '未知'
            stock_code_str = stock_code_str or '未知'
            max_return = max_return or 0
            best_sell_day = best_sell_day or 0
            best_sell_price = best_sell_price or 0
            buy_price = buy_price or 0
            max_consecutive = max_consecutive or 0
            start_date = start_date or '未知'
            
            print(f"{i:<4} {stock_name:<10} {stock_code_str:<10} "
                  f"{max_return:<10.2f}% 第{best_sell_day:<3}天 "
                  f"{best_sell_price:<10.2f} {buy_price:<10.2f} "
                  f"{max_consecutive:<12} {start_date:<12}")
        except Exception as e:
            print(f"{i:<4} 数据异常: {e}")
            continue
    
    print("\n" + "=" * 120)
    
    # 输出前三名详细信息
    print("\n前三名详细分析：")
    try:
        for i, (_, row) in enumerate(results_df.head(3).iterrows(), 1):
            try:
                # 处理可能为None的字段
                stock_name = row.get('股票名称', '未知')
                stock_code = row.get('股票代码')
                stock_code_str = str(stock_code).zfill(6) if stock_code is not None else '未知'
                buy_price = row.get('买入价', 0)
                best_sell_day = row.get('最佳卖出日', 0)
                best_sell_date = row.get('最佳卖出日期', '未知')
                best_sell_price = row.get('最佳卖出价', 0)
                max_return = row.get('最大收益率', 0)
                max_consecutive = row.get('最大连续涨停天数', 0)
                start_date = row.get('涨停开始日期', '未知')
                
                # 确保所有值都不是None
                stock_name = stock_name or '未知'
                stock_code_str = stock_code_str or '未知'
                buy_price = buy_price or 0
                best_sell_day = best_sell_day or 0
                best_sell_date = best_sell_date or '未知'
                best_sell_price = best_sell_price or 0
                max_return = max_return or 0
                max_consecutive = max_consecutive or 0
                start_date = start_date or '未知'
                
                print(f"\n{i}. {stock_name} ({stock_code_str}):")
                print(f"   买入价: {buy_price:.2f}元")
                print(f"   最佳卖出日: 第{best_sell_day}天 ({best_sell_date})")
                print(f"   最佳卖出价: {best_sell_price:.2f}元")
                print(f"   最大收益率: {max_return:.2f}%")
                print(f"   绝对收益: {best_sell_price - buy_price:.2f}元")
                print(f"   最大连续涨停天数: {max_consecutive}")
                print(f"   涨停开始日期: {start_date}")
            except Exception as e:
                print(f"\n{i}. 数据异常: {e}")
                continue
    except Exception as e:
        print(f"输出详细信息时出错: {e}")
    
    # 保存结果到MD文件
    try:
        if os.path.isdir(path):
            # 如果是文件夹，使用greedy前缀
            md_output_file = os.path.join(path, 'greedy_最大收益计算结果.md')
        else:
            # 如果是文件，使用greedy前缀 + 原文件名（去掉analysis_前缀）
            output_dir = os.path.dirname(path)
            original_filename = os.path.basename(path)
            base_name = os.path.splitext(original_filename)[0]
            # 去掉analysis_前缀
            if base_name.startswith('analysis_'):
                base_name = base_name[9:]  # 去掉'analysis_'前缀（9个字符）
            output_filename = f"greedy_{base_name}.md"
            md_output_file = os.path.join(output_dir, output_filename)
        
        with open(md_output_file, 'w', encoding='utf-8') as f:
            f.write("# 股票最大收益分析报告\n\n")
            f.write(f"生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("免责声明：仅供学习参考，不作为任何投资建议，请谨慎对待。\n1. 因未来时间大盘偏移无法估算，因此第二日及之后的异动价格只作预估！\n2. 可涨幅度按照最后交易日收盘价计算，未进行复利叠加，请自行换算！\n3. 算法粗糙，仅图一乐~\n\n\n\n")
            
            # 第一个表格：贪心算法最大收益
            f.write("## 一、贪心算法最大收益\n\n")
            f.write("| 排名 | 股票名称 | 股票代码 | 最大收益率 | 最佳卖出日 | 最佳卖出价 | 买入价 | 最大连续涨停天数 | 涨停开始日期 |\n")
            f.write("|------|---------|---------|-----------|-----------|-----------|--------|-----------------|-------------|\n")
            
            for i, (_, row) in enumerate(results_df.iterrows(), 1):
                try:
                    # 处理可能为None的字段
                    stock_name = row.get('股票名称', '未知')
                    stock_code = row.get('股票代码')
                    stock_code_str = str(stock_code).zfill(6) if stock_code is not None else '未知'
                    max_return = row.get('最大收益率', 0)
                    best_sell_day = row.get('最佳卖出日', 0)
                    best_sell_price = row.get('最佳卖出价', 0)
                    buy_price = row.get('买入价', 0)
                    max_consecutive = row.get('最大连续涨停天数', 0)
                    start_date = row.get('涨停开始日期', '未知')
                    
                    # 确保所有值都不是None
                    stock_name = stock_name or '未知'
                    stock_code_str = stock_code_str or '未知'
                    max_return = max_return or 0
                    best_sell_day = best_sell_day or 0
                    best_sell_price = best_sell_price or 0
                    buy_price = buy_price or 0
                    max_consecutive = max_consecutive or 0
                    start_date = start_date or '未知'
                    
                    # 写入MD表格行
                    f.write(f"| {i} | {stock_name} | {stock_code_str} | {max_return:.2f}% | 第{best_sell_day}天 | {best_sell_price:.2f} | {buy_price:.2f} | {max_consecutive} | {start_date} |\n")
                except Exception as e:
                    f.write(f"| {i} | 数据异常 | 未知 | 0.00% | 0 | 0.00 | 0.00 | 0 | 未知 |\n")
                    continue
            
            # 第二个表格：贪心算法最大连板
            f.write("\n\n\n## 二、贪心算法最大连板\n\n")
            f.write("| 排名 | 股票名称 | 股票代码 | 连板收益 | 连板天数 | 开始日期 | 结束日期 |\n")
            f.write("|------|---------|---------|---------|---------|---------|---------|\n")
            
            # 按最大连续涨停天数排序，相同天数按连板收益排序
            consecutive_df = results_df.sort_values(['最大连续涨停天数', '连板收益'], ascending=[False, False])
            
            for i, (_, row) in enumerate(consecutive_df.iterrows(), 1):
                try:
                    # 处理可能为None的字段
                    stock_name = row.get('股票名称', '未知')
                    stock_code = row.get('股票代码')
                    stock_code_str = str(stock_code).zfill(6) if stock_code is not None else '未知'
                    consecutive_income = row.get('连板收益', 0)
                    max_consecutive = row.get('最大连续涨停天数', 0)
                    start_date = row.get('涨停开始日期', '未知')
                    end_date = row.get('连板结束日期', '未知')
                    
                    # 确保所有值都不是None
                    stock_name = stock_name or '未知'
                    stock_code_str = stock_code_str or '未知'
                    consecutive_income = consecutive_income or 0
                    max_consecutive = max_consecutive or 0
                    start_date = start_date or '未知'
                    end_date = end_date or '未知'
                    
                    # 写入MD表格行
                    f.write(f"| {i} | {stock_name} | {stock_code_str} | {consecutive_income:.2f}% | {max_consecutive} | {start_date} | {end_date} |\n")
                except Exception as e:
                    f.write(f"| {i} | 数据异常 | 未知 | 0.00% | 0 | 未知 | 未知 |\n")
                    continue
        
        print(f"结果已保存到 '{md_output_file}'")
    except Exception as e:
        print(f"保存结果时出错: {e}")

if __name__ == "__main__":
    main()