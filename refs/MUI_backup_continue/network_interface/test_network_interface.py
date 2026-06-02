"""
Network Interface Test Script

测试本地和云端后端的基本功能
"""

import sys
from network_interface import (
    BackendType,
    LocalBackend,
    CloudBackend,
    CloudConfig,
    TaskManager,
    TaskStatus,
    SimulationTask
)


def test_local_backend():
    """测试本地后端"""
    print("\n" + "="*60)
    print("Testing Local Backend")
    print("="*60)
    
    try:
        backend = LocalBackend()
        print("[1/5] LocalBackend instance created")
        
        # 连接
        config = {}
        if backend.connect(config):
            print("[2/5] Connected to local MATLAB engine")
        else:
            print("[2/5] FAILED: Could not connect to MATLAB")
            return False
        
        # 获取后端信息
        info = backend.get_backend_info()
        print(f"[3/5] Backend info: {info}")
        
        # 提交测试任务
        test_params = {
            'molecule_data': {'test': 'data'},
            'inter': [1, 2, 3],
            'sys_info': {'field': 1.5},
            'spin_system': 'test'
        }
        
        task_id = backend.submit_simulation(test_params)
        print(f"[4/5] Submitted simulation, task_id: {task_id}")
        
        # 获取结果
        result = backend.get_result(task_id)
        print(f"[5/5] Got result: {type(result)}")
        
        # 断开连接
        backend.disconnect()
        print("\nLocal backend test completed successfully")
        return True
        
    except Exception as e:
        print(f"\nLocal backend test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_manager():
    """测试任务管理器"""
    print("\n" + "="*60)
    print("Testing Task Manager")
    print("="*60)
    
    try:
        manager = TaskManager(max_cache_size=10)
        print("[1/8] TaskManager created")
        
        # 创建任务
        task = manager.create_task('test-001', {'param': 'value'})
        print(f"[2/8] Task created: {task.task_id}")
        
        # 更新状态
        manager.update_task_status('test-001', TaskStatus.QUEUED)
        print("[3/8] Task status updated to QUEUED")
        
        manager.update_task_status('test-001', TaskStatus.RUNNING, progress=25.0)
        print("[4/8] Task status updated to RUNNING (25%)")
        
        manager.update_task_status('test-001', TaskStatus.RUNNING, progress=75.0)
        print("[5/8] Task progress updated (75%)")
        
        # 设置结果
        manager.set_task_result('test-001', {'result': 'success'})
        print("[6/8] Task result set")
        
        # 获取任务
        task = manager.get_task('test-001')
        print(f"[7/8] Retrieved task: status={task.status.value}, progress={task.progress}%")
        
        # 统计
        stats = manager.get_statistics()
        print(f"[8/8] Statistics: {stats}")
        
        print("\nTask manager test completed successfully")
        return True
        
    except Exception as e:
        print(f"\nTask manager test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cloud_config():
    """测试云端配置"""
    print("\n" + "="*60)
    print("Testing Cloud Configuration")
    print("="*60)
    
    try:
        # 创建配置
        config = CloudConfig(
            endpoint="https://example.com/api/v1",
            api_key="test-key-12345",
            timeout=30,
            max_retries=3
        )
        print("[1/3] CloudConfig created")
        
        # 保存到文件
        import tempfile
        import os
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        temp_file.close()
        
        config.to_file(temp_file.name)
        print(f"[2/3] Config saved to {temp_file.name}")
        
        # 从文件加载
        loaded_config = CloudConfig.from_file(temp_file.name)
        print(f"[3/3] Config loaded: endpoint={loaded_config.endpoint}")
        
        # 清理
        os.unlink(temp_file.name)
        
        print("\nCloud config test completed successfully")
        return True
        
    except Exception as e:
        print(f"\nCloud config test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simulation_task():
    """测试SimulationTask数据类"""
    print("\n" + "="*60)
    print("Testing SimulationTask")
    print("="*60)
    
    try:
        # 创建任务
        task = SimulationTask(
            task_id='task-123',
            parameters={'field': 1.5},
            status=TaskStatus.PENDING
        )
        print(f"[1/5] Task created: {task.task_id}")
        
        # 转换为字典
        task_dict = task.to_dict()
        print(f"[2/5] Task to dict: {task_dict.keys()}")
        
        # 从字典恢复
        task2 = SimulationTask.from_dict(task_dict)
        print(f"[3/5] Task from dict: {task2.task_id}")
        
        # 状态检查
        print(f"[4/5] Is terminal: {task.is_terminal()}")
        print(f"[5/5] Is active: {task.is_active()}")
        
        print("\nSimulationTask test completed successfully")
        return True
        
    except Exception as e:
        print(f"\nSimulationTask test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Network Interface Module Test Suite")
    print("="*60)
    
    results = {}
    
    # 测试各个组件
    results['SimulationTask'] = test_simulation_task()
    results['CloudConfig'] = test_cloud_config()
    results['TaskManager'] = test_task_manager()
    results['LocalBackend'] = test_local_backend()
    
    # 打印总结
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        symbol = "✓" if passed else "✗"
        print(f"{symbol} {name}: {status}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return all(results.values())


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
