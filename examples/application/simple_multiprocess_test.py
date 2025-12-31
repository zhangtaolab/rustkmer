#!/usr/bin/env python3
"""
简化的multiprocessing测试
"""

import multiprocessing
import time

def simple_worker(args):
    """简单的worker函数"""
    seq_name, seq, process_id = args
    time.sleep(0.1)  # 模拟处理时间
    processed_seq = seq.replace('N', 'A')
    return (seq_name, processed_seq, True, f"进程 {process_id} 完成")

def test_simple_multiprocessing():
    """测试简单的multiprocessing"""
    print("=== 测试简单的multiprocessing ===")
    
    # 测试数据
    test_data = [
        ("序列1", "ATCGNNNNNNNNNNNNCGTA", 1),
        ("序列2", "GCATNNNNNNNNNNNNTTAG", 2),
        ("序列3", "CGTANNNNNNNNNNNNCCGA", 3),
        ("序列4", "TTAGNNNNNNNNNNNNGGCTA", 4),
    ]
    
    try:
        # 使用2个进程
        with multiprocessing.Pool(processes=2) as pool:
            print("✅ Pool创建成功")
            
            # 提交任务
            results = pool.map(simple_worker, test_data)
            
            print("✅ 任务完成")
            for name, processed_seq, success, message in results:
                print(f"  ✅ {name}: {message}")
                
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_simple_multiprocessing()
    if success:
        print("\n🎉 multiprocessing基本功能正常！")
    else:
        print("\n❌ multiprocessing功能异常")




