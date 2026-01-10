import os
import pandas as pd
import argparse
from datetime import datetime

def parse_args():
    """
    解析命令行参数
    """
    parser = argparse.ArgumentParser(description='使用贪心算法分析股票收益')
    parser.add_argument('--file', type=str, required=True, help='包含股票异动情况的文件夹路径')
    return parser.parse_args()

def analyze_stock_profit(folder_path):
    """
    使用新算法分析股票收益
    """
    # 构建文件路径
    merged_df_path = os.path.join(folder_path, 'analysis_合并异动.csv')
    
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
            potential_price = prev_current * 1.10
            
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
            '涨停开始日期': start_date
        })
    
    return results

def main():
    """
    主函数
    """
    # 解析命令行参数
    args = parse_args()
    folder_path = args.file
    
    # 验证文件夹路径
    if not os.path.exists(folder_path):
        print(f"文件夹 {folder_path} 不存在")
        return
    
    if not os.path.isdir(folder_path):
        print(f"路径 {folder_path} 不是一个文件夹")
        return
    
    # 分析股票收益
    print("正在分析股票收益...")
    results = analyze_stock_profit(folder_path)
    
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
        print(f"{i:<4} {row['股票名称']:<10} {str(row['股票代码']).zfill(6):<10} "
              f"{row['最大收益率']:<10.2f}% 第{row['最佳卖出日']:<3}天 "
              f"{row['最佳卖出价']:<10.2f} {row['买入价']:<10.2f} "
              f"{row['最大连续涨停天数']:<12} {row['涨停开始日期']:<12}")
    
    print("\n" + "=" * 120)
    
    # 输出前三名详细信息
    print("\n前三名详细分析：")
    for i, (_, row) in enumerate(results_df.head(3).iterrows(), 1):
        print(f"\n{i}. {row['股票名称']} ({str(row['股票代码']).zfill(6)}):")
        print(f"   买入价: {row['买入价']:.2f}元")
        print(f"   最佳卖出日: 第{row['最佳卖出日']}天 ({row['最佳卖出日期']})")
        print(f"   最佳卖出价: {row['最佳卖出价']:.2f}元")
        print(f"   最大收益率: {row['最大收益率']:.2f}%")
        print(f"   绝对收益: {row['最佳卖出价'] - row['买入价']:.2f}元")
        print(f"   最大连续涨停天数: {row['最大连续涨停天数']}")
        print(f"   涨停开始日期: {row['涨停开始日期']}")
    
    # 保存结果到CSV文件
    output_file = os.path.join(folder_path, '最大收益计算结果.csv')
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n结果已保存到 '{output_file}'")

if __name__ == "__main__":
    main()