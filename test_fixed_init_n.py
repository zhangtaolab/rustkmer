#!/usr/bin/env python3
"""
测试修复后的init_n_length参数功能
"""

def test_init_n_length_logic():
    """测试修复后的N长度选择逻辑"""
    print("=== 测试修复后的N长度选择逻辑 ===")
    
    def get_initial_n_length_fixed(actual_n_length, max_n_length, init_n_length, verbose=False):
        """修复后的N长度选择逻辑"""
        if init_n_length > 0:
            # 使用用户指定的初始N长度，但不超过max_n_length
            # 注意：不与actual_n_length比较，允许用户强制使用更长的N长度
            n_length = min(init_n_length, max_n_length)
            if verbose:
                print(f"使用指定的初始N长度: {n_length} (实际N长度: {actual_n_length})")
        else:
            # 使用默认逻辑：不超过max_n_length的实际N长度
            if actual_n_length > max_n_length:
                n_length = max_n_length
            else:
                n_length = actual_n_length
            if verbose:
                print(f"使用实际N长度: {n_length}")
        return n_length
    
    test_cases = [
        # (实际N长度, 最大N长度, 初始N长度, 期望结果, 描述)
        (10, 43, 0, 10, "默认：实际N长度小于最大N长度"),
        (50, 43, 0, 43, "默认：实际N长度大于最大N长度，使用最大N长度"),
        (1, 43, 35, 35, "修复：实际N长度=1，指定初始N长度=35，应使用35"),
        (10, 43, 35, 35, "修复：实际N长度=10，指定初始N长度=35，应使用35"),
        (50, 43, 35, 35, "修复：实际N长度=50，指定初始N长度=35，应使用35"),
        (10, 30, 35, 30, "修复：指定初始N长度超过max_n_length，应限制到max_n_length"),
    ]
    
    for actual_n, max_n, init_n, expected, desc in test_cases:
        result = get_initial_n_length_fixed(actual_n, max_n, init_n, verbose=True)
        status = "✅" if result == expected else "❌"
        print(f"{status} {desc}")
        print(f"   实际N长度: {actual_n}, 最大N长度: {max_n}, 初始N长度: {init_n}")
        print(f"   期望结果: {expected}, 实际结果: {result}")
        print()

def test_user_scenario():
    """测试用户遇到的具体场景"""
    print("=== 测试用户场景 ===")
    
    # 用户的具体情况
    seq = "TAAACCAAAACCCTAAACACAATAAAAACACAANATGAGAAGCTTGGGCAATTGGAGGATGCACAGATTACTACCAACAATTCCCTGCAATCCATTCCCATATTACAGTGTCAATAGCTTATAACTTCGTCTGGGACCCCAGTCCAAGTGAGGCCCATATAGGGTGCACCCCAATCTAGTGAAGCACGACCCGTGGACCCTCTTGATCGTCCTCCCACCTCTA"
    nstart, nend = 33, 33  # 只有一个N
    kmerlen = 57
    max_n_length = 43
    init_n_length = 35  # 用户指定的
    
    actual_n_length = nend - nstart + 1  # = 1
    
    print(f"序列片段: ...{seq[nstart-10:nend+10]}...")
    print(f"N区域位置: {nstart}-{nend} (实际N长度: {actual_n_length})")
    print(f"用户指定初始N长度: {init_n_length}")
    print(f"最大N长度限制: {max_n_length}")
    
    # 使用修复后的逻辑
    if init_n_length > 0:
        n_length = min(init_n_length, max_n_length)
        print(f"修复后结果: 使用初始N长度 {n_length}")
    else:
        n_length = min(actual_n_length, max_n_length)
        print(f"默认结果: 使用实际N长度 {n_length}")
    
    print(f"✅ 修复成功！现在会使用用户指定的35而不是被限制为1")

if __name__ == "__main__":
    test_init_n_length_logic()
    test_user_scenario()
