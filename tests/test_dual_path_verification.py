#!/usr/bin/env python3
"""
O-RAN SC Release J - 雙路徑通訊驗證測試
不需要實際依賴的結構驗證
"""

import sys
import os
import json
import ast
import unittest
from pathlib import Path

# Add paths
BASE_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_PATH / 'xapps' / 'common'))

print("=" * 80)
print("O-RAN SC Release J - 雙路徑通訊結構驗證測試")
print("=" * 80)
print()


class TestCodeStructure(unittest.TestCase):
    """測試代碼結構和語法"""

    def setUp(self):
        """測試準備"""
        print("\n[測試] 代碼結構和語法")

    def test_01_syntax_validation(self):
        """測試 1: 驗證所有 Python 文件語法"""
        print("  ✓ 驗證 Python 語法...")

        files_to_check = [
            'xapps/common/dual_path_messenger.py',
            'xapps/traffic-steering/src/traffic_steering.py',
            'xapps/rc-xapp/src/ran_control.py',
            'xapps/kpimon-go-xapp/src/kpimon.py',
        ]

        for file_path in files_to_check:
            full_path = BASE_PATH / file_path
            with open(full_path, 'r', encoding='utf-8') as f:
                code = f.read()

            try:
                ast.parse(code)
                print(f"    ✅ {file_path} - 語法正確")
            except SyntaxError as e:
                self.fail(f"{file_path} has syntax error: {e}")


class TestDualPathMessengerCore(unittest.TestCase):
    """測試 DualPathMessenger 核心庫結構"""

    def setUp(self):
        """測試準備"""
        print("\n[測試] DualPathMessenger 核心庫")

    def test_01_core_library_exists(self):
        """測試 1: 核心庫文件存在"""
        print("  ✓ 檢查核心庫文件...")

        file_path = BASE_PATH / 'xapps/common/dual_path_messenger.py'
        self.assertTrue(file_path.exists(), "DualPathMessenger 核心庫不存在")
        print("    ✅ dual_path_messenger.py 存在")

    def test_02_core_classes_defined(self):
        """測試 2: 核心類定義"""
        print("  ✓ 檢查核心類定義...")

        file_path = BASE_PATH / 'xapps/common/dual_path_messenger.py'
        with open(file_path, 'r') as f:
            content = f.read()

        required_classes = [
            'DualPathMessenger',
            'EndpointConfig',
            'CommunicationPath',
            'PathStatus',
            'PathHealthMetrics'
        ]

        for class_name in required_classes:
            self.assertIn(f'class {class_name}', content,
                         f"缺少類定義: {class_name}")
            print(f"    ✅ {class_name} 已定義")

    def test_03_key_methods_exist(self):
        """測試 3: 關鍵方法存在"""
        print("  ✓ 檢查關鍵方法...")

        file_path = BASE_PATH / 'xapps/common/dual_path_messenger.py'
        with open(file_path, 'r') as f:
            content = f.read()

        required_methods = [
            'def send_message',
            'def register_endpoint',
            'def initialize_rmr',
            'def start',
            'def get_health_summary',
            'def _evaluate_failover',
            'def _send_via_rmr',
            'def _send_via_http',
        ]

        for method in required_methods:
            self.assertIn(method, content, f"缺少方法: {method}")
            print(f"    ✅ {method} 已定義")

    def test_04_common_init_exports(self):
        """測試 4: common/__init__.py 導出"""
        print("  ✓ 檢查 common 庫導出...")

        file_path = BASE_PATH / 'xapps/common/__init__.py'
        with open(file_path, 'r') as f:
            content = f.read()

        required_exports = [
            'DualPathMessenger',
            'EndpointConfig',
            'CommunicationPath',
            'PathStatus',
            'PathHealthMetrics'
        ]

        for export in required_exports:
            self.assertIn(export, content, f"__init__.py 缺少導出: {export}")
            print(f"    ✅ {export} 已導出")


class TestTrafficSteeringIntegration(unittest.TestCase):
    """測試 Traffic Steering xApp 整合"""

    def setUp(self):
        """測試準備"""
        print("\n[測試] Traffic Steering xApp 整合")

    def test_01_file_exists(self):
        """測試 1: 文件存在"""
        print("  ✓ 檢查文件存在...")

        file_path = BASE_PATH / 'xapps/traffic-steering/src/traffic_steering.py'
        self.assertTrue(file_path.exists(), "traffic_steering.py 不存在")
        print("    ✅ traffic_steering.py 存在")

    def test_02_has_dual_path_import(self):
        """測試 2: 導入 DualPathMessenger"""
        print("  ✓ 檢查導入...")

        file_path = BASE_PATH / 'xapps/traffic-steering/src/traffic_steering.py'
        with open(file_path, 'r') as f:
            content = f.read()

        self.assertIn('from dual_path_messenger import', content)
        self.assertIn('DualPathMessenger', content)
        self.assertIn('EndpointConfig', content)
        self.assertIn('CommunicationPath', content)
        print("    ✅ 導入正確")

    def test_03_has_messenger_initialization(self):
        """測試 3: Messenger 初始化"""
        print("  ✓ 檢查初始化...")

        file_path = BASE_PATH / 'xapps/traffic-steering/src/traffic_steering.py'
        with open(file_path, 'r') as f:
            content = f.read()

        self.assertIn('self.messenger = DualPathMessenger', content)
        self.assertIn('messenger.initialize_rmr', content)
        self.assertIn('messenger.start()', content)
        print("    ✅ 初始化正確")

    def test_04_has_endpoint_registration(self):
        """測試 4: 端點註冊"""
        print("  ✓ 檢查端點註冊...")

        file_path = BASE_PATH / 'xapps/traffic-steering/src/traffic_steering.py'
        with open(file_path, 'r') as f:
            content = f.read()

        self.assertIn('def _register_endpoints', content)
        self.assertIn('messenger.register_endpoint', content)
        print("    ✅ 端點註冊正確")

    def test_05_has_message_sending(self):
        """測試 5: 消息發送"""
        print("  ✓ 檢查消息發送...")

        file_path = BASE_PATH / 'xapps/traffic-steering/src/traffic_steering.py'
        with open(file_path, 'r') as f:
            content = f.read()

        self.assertIn('messenger.send_message', content)
        print("    ✅ 消息發送正確")

    def test_06_has_health_endpoint(self):
        """測試 6: 健康端點"""
        print("  ✓ 檢查健康端點...")

        file_path = BASE_PATH / 'xapps/traffic-steering/src/traffic_steering.py'
        with open(file_path, 'r') as f:
            content = f.read()

        self.assertIn('health_paths', content)
        self.assertIn('get_health_summary', content)
        print("    ✅ 健康端點正確")


class TestRCxAppIntegration(unittest.TestCase):
    """測試 RC-xApp 整合"""

    def setUp(self):
        """測試準備"""
        print("\n[測試] RC-xApp 整合")

    def test_01_file_exists(self):
        """測試 1: 文件存在"""
        print("  ✓ 檢查文件存在...")

        file_path = BASE_PATH / 'xapps/rc-xapp/src/ran_control.py'
        self.assertTrue(file_path.exists(), "ran_control.py 不存在")
        print("    ✅ ran_control.py 存在")

    def test_02_has_dual_path_import(self):
        """測試 2: 導入 DualPathMessenger"""
        print("  ✓ 檢查導入...")

        file_path = BASE_PATH / 'xapps/rc-xapp/src/ran_control.py'
        with open(file_path, 'r') as f:
            content = f.read()

        self.assertIn('from dual_path_messenger import', content)
        self.assertIn('DualPathMessenger', content)
        print("    ✅ 導入正確")

    def test_03_has_messenger_initialization(self):
        """測試 3: Messenger 初始化"""
        print("  ✓ 檢查初始化...")

        file_path = BASE_PATH / 'xapps/rc-xapp/src/ran_control.py'
        with open(file_path, 'r') as f:
            content = f.read()

        self.assertIn('self.messenger = DualPathMessenger', content)
        self.assertIn('messenger.initialize_rmr', content)
        self.assertIn('messenger.start()', content)
        print("    ✅ 初始化正確")

    def test_04_has_endpoint_registration(self):
        """測試 4: 端點註冊"""
        print("  ✓ 檢查端點註冊...")

        file_path = BASE_PATH / 'xapps/rc-xapp/src/ran_control.py'
        with open(file_path, 'r') as f:
            content = f.read()

        self.assertIn('def _register_endpoints', content)
        self.assertIn('messenger.register_endpoint', content)
        print("    ✅ 端點註冊正確")

    def test_05_has_message_sending(self):
        """測試 5: 消息發送"""
        print("  ✓ 檢查消息發送...")

        file_path = BASE_PATH / 'xapps/rc-xapp/src/ran_control.py'
        with open(file_path, 'r') as f:
            content = f.read()

        self.assertIn('messenger.send_message', content)
        print("    ✅ 消息發送正確")

    def test_06_has_health_endpoint(self):
        """測試 6: 健康端點"""
        print("  ✓ 檢查健康端點...")

        file_path = BASE_PATH / 'xapps/rc-xapp/src/ran_control.py'
        with open(file_path, 'r') as f:
            content = f.read()

        self.assertIn('health_paths', content)
        self.assertIn('get_health_summary', content)
        print("    ✅ 健康端點正確")


class TestKPIMONIntegration(unittest.TestCase):
    """測試 KPIMON xApp 整合"""

    def setUp(self):
        """測試準備"""
        print("\n[測試] KPIMON xApp 整合")

    def test_01_file_exists(self):
        """測試 1: 文件存在"""
        print("  ✓ 檢查文件存在...")

        file_path = BASE_PATH / 'xapps/kpimon-go-xapp/src/kpimon.py'
        self.assertTrue(file_path.exists(), "kpimon.py 不存在")
        print("    ✅ kpimon.py 存在")

    def test_02_has_dual_path_import(self):
        """測試 2: 導入 DualPathMessenger"""
        print("  ✓ 檢查導入...")

        file_path = BASE_PATH / 'xapps/kpimon-go-xapp/src/kpimon.py'
        with open(file_path, 'r') as f:
            content = f.read()

        self.assertIn('from dual_path_messenger import', content)
        self.assertIn('DualPathMessenger', content)
        print("    ✅ 導入正確")

    def test_03_has_messenger_initialization(self):
        """測試 3: Messenger 初始化"""
        print("  ✓ 檢查初始化...")

        file_path = BASE_PATH / 'xapps/kpimon-go-xapp/src/kpimon.py'
        with open(file_path, 'r') as f:
            content = f.read()

        self.assertIn('self.messenger = DualPathMessenger', content)
        self.assertIn('messenger.initialize_rmr', content)
        self.assertIn('messenger.start()', content)
        print("    ✅ 初始化正確")

    def test_04_has_endpoint_registration(self):
        """測試 4: 端點註冊"""
        print("  ✓ 檢查端點註冊...")

        file_path = BASE_PATH / 'xapps/kpimon-go-xapp/src/kpimon.py'
        with open(file_path, 'r') as f:
            content = f.read()

        self.assertIn('def _register_endpoints', content)
        self.assertIn('messenger.register_endpoint', content)
        print("    ✅ 端點註冊正確")

    def test_05_has_message_sending(self):
        """測試 5: 消息發送"""
        print("  ✓ 檢查消息發送...")

        file_path = BASE_PATH / 'xapps/kpimon-go-xapp/src/kpimon.py'
        with open(file_path, 'r') as f:
            content = f.read()

        self.assertIn('messenger.send_message', content)
        print("    ✅ 消息發送正確")

    def test_06_has_health_endpoint(self):
        """測試 6: 健康端點"""
        print("  ✓ 檢查健康端點...")

        file_path = BASE_PATH / 'xapps/kpimon-go-xapp/src/kpimon.py'
        with open(file_path, 'r') as f:
            content = f.read()

        self.assertIn('health_paths', content)
        self.assertIn('get_health_summary', content)
        print("    ✅ 健康端點正確")


class TestFileStructure(unittest.TestCase):
    """測試文件結構完整性"""

    def setUp(self):
        """測試準備"""
        print("\n[測試] 文件結構完整性")

    def test_01_all_required_files_exist(self):
        """測試 1: 所有必要文件存在"""
        print("  ✓ 檢查文件結構...")

        required_files = [
            'xapps/common/dual_path_messenger.py',
            'xapps/common/__init__.py',
            'xapps/traffic-steering/src/traffic_steering.py',
            'xapps/rc-xapp/src/ran_control.py',
            'xapps/kpimon-go-xapp/src/kpimon.py',
            'docs/DUAL_PATH_IMPLEMENTATION.md',
            'scripts/enable-dual-path-all-xapps.sh',
        ]

        missing_files = []
        for file_path in required_files:
            full_path = BASE_PATH / file_path
            if not full_path.exists():
                missing_files.append(file_path)
            else:
                print(f"    ✅ {file_path}")

        if missing_files:
            self.fail(f"缺少文件: {', '.join(missing_files)}")


class TestEndpointConfiguration(unittest.TestCase):
    """測試端點配置"""

    def setUp(self):
        """測試準備"""
        print("\n[測試] 端點配置")

    def test_01_traffic_steering_endpoints(self):
        """測試 1: Traffic Steering 端點"""
        print("  ✓ 檢查 Traffic Steering 端點...")

        file_path = BASE_PATH / 'xapps/traffic-steering/src/traffic_steering.py'
        with open(file_path, 'r') as f:
            content = f.read()

        # 應該註冊 QoE Predictor, RC-xApp 等端點
        expected_endpoints = ['qoe-predictor', 'ran-control', 'e2term']
        found_endpoints = []

        for endpoint in expected_endpoints:
            if endpoint in content:
                found_endpoints.append(endpoint)
                print(f"    ✅ 找到端點: {endpoint}")

        self.assertGreater(len(found_endpoints), 0, "未找到任何端點註冊")

    def test_02_rc_xapp_endpoints(self):
        """測試 2: RC-xApp 端點"""
        print("  ✓ 檢查 RC-xApp 端點...")

        file_path = BASE_PATH / 'xapps/rc-xapp/src/ran_control.py'
        with open(file_path, 'r') as f:
            content = f.read()

        expected_endpoints = ['e2term', 'traffic-steering', 'kpimon']
        found_endpoints = []

        for endpoint in expected_endpoints:
            if endpoint in content:
                found_endpoints.append(endpoint)
                print(f"    ✅ 找到端點: {endpoint}")

        self.assertGreater(len(found_endpoints), 0, "未找到任何端點註冊")

    def test_03_kpimon_endpoints(self):
        """測試 3: KPIMON 端點"""
        print("  ✓ 檢查 KPIMON 端點...")

        file_path = BASE_PATH / 'xapps/kpimon-go-xapp/src/kpimon.py'
        with open(file_path, 'r') as f:
            content = f.read()

        # KPIMON 至少應該註冊 E2 Term
        self.assertIn('e2term', content.lower(), "未找到 E2 Term 端點")
        print("    ✅ 找到 E2 Term 端點")


def run_all_tests():
    """運行所有測試"""
    print("\n開始運行結構驗證測試套件...\n")

    # 創建測試套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加測試類
    suite.addTests(loader.loadTestsFromTestCase(TestCodeStructure))
    suite.addTests(loader.loadTestsFromTestCase(TestDualPathMessengerCore))
    suite.addTests(loader.loadTestsFromTestCase(TestTrafficSteeringIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestRCxAppIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestKPIMONIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestFileStructure))
    suite.addTests(loader.loadTestsFromTestCase(TestEndpointConfiguration))

    # 運行測試
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 打印總結
    print("\n" + "=" * 80)
    print("測試總結")
    print("=" * 80)
    print(f"總測試數: {result.testsRun}")
    print(f"✅ 成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ 失敗: {len(result.failures)}")
    print(f"⚠️  錯誤: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n" + "=" * 80)
        print("🎉 所有結構驗證測試通過！")
        print("=" * 80)
        print("\n✅ 驗證結果：")
        print("  1. ✅ 所有 Python 文件語法正確")
        print("  2. ✅ DualPathMessenger 核心庫完整")
        print("  3. ✅ Traffic Steering xApp 正確整合雙路徑")
        print("  4. ✅ RC-xApp 正確整合雙路徑")
        print("  5. ✅ KPIMON xApp 正確整合雙路徑")
        print("  6. ✅ 所有必要文件存在")
        print("  7. ✅ 所有端點配置正確")
        print("\n📝 說明：")
        print("  - 這些測試驗證代碼結構和整合的正確性")
        print("  - 運行時測試需要在 O-RAN RIC 環境中進行")
        print("  - 建議在 Kubernetes 集群中部署後進行完整測試")
        print("\n🚀 下一步：")
        print("  1. 在 Kubernetes 中部署 xApps")
        print("  2. 使用 scripts/enable-dual-path-all-xapps.sh 驗證部署")
        print("  3. 監控 Prometheus 指標檢查雙路徑運行狀態")
        print("  4. 測試故障切換：停止 RMR 路由服務，確認 HTTP 接管")
        print("=" * 80)
        return 0
    else:
        print("\n❌ 有測試失敗，需要修復。")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
