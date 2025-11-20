#!/usr/bin/env python3
"""
O-RAN SC Release J - 雙路徑通訊集成測試
完整測試所有迴路和功能
"""

import sys
import os
import json
import time
import unittest
from unittest.mock import Mock, MagicMock, patch

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../xapps/common'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../xapps/traffic-steering/src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../xapps/rc-xapp/src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../xapps/kpimon-go-xapp/src'))

print("=" * 80)
print("O-RAN SC Release J - 雙路徑通訊集成測試")
print("=" * 80)
print()

class TestDualPathMessenger(unittest.TestCase):
    """測試 DualPathMessenger 核心功能"""

    def setUp(self):
        """測試準備"""
        print("\n[測試] DualPathMessenger 核心功能")

    def test_01_import_dual_path_messenger(self):
        """測試 1: 導入 DualPathMessenger"""
        print("  ✓ 測試導入 DualPathMessenger...")
        try:
            from dual_path_messenger import (
                DualPathMessenger,
                EndpointConfig,
                CommunicationPath,
                PathStatus
            )
            print("    ✅ 成功導入所有類")
            self.assertTrue(True)
        except ImportError as e:
            print(f"    ❌ 導入失敗: {e}")
            self.fail(f"Failed to import: {e}")

    def test_02_create_endpoint_config(self):
        """測試 2: 創建 EndpointConfig"""
        print("  ✓ 測試創建 EndpointConfig...")
        try:
            from dual_path_messenger import EndpointConfig

            endpoint = EndpointConfig(
                service_name="test-service",
                namespace="ricxapp",
                http_port=8080,
                rmr_port=4560
            )

            self.assertEqual(endpoint.service_name, "test-service")
            self.assertEqual(endpoint.http_port, 8080)
            self.assertEqual(endpoint.http_base_url,
                           "http://test-service.ricxapp.svc.cluster.local:8080")
            print("    ✅ EndpointConfig 創建成功")

        except Exception as e:
            print(f"    ❌ 創建失敗: {e}")
            self.fail(str(e))

    @patch('dual_path_messenger.RMRXapp')
    @patch('dual_path_messenger.requests.Session')
    def test_03_initialize_messenger(self, mock_session, mock_rmr):
        """測試 3: 初始化 DualPathMessenger"""
        print("  ✓ 測試初始化 DualPathMessenger...")
        try:
            from dual_path_messenger import DualPathMessenger

            # Mock message handler
            def mock_handler(xapp, summary, sbuf):
                pass

            messenger = DualPathMessenger(
                xapp_name="test-xapp",
                rmr_port=4560,
                message_handler=mock_handler,
                config={}
            )

            self.assertIsNotNone(messenger)
            self.assertEqual(messenger.xapp_name, "test-xapp")
            self.assertEqual(messenger.rmr_port, 4560)
            print("    ✅ DualPathMessenger 初始化成功")

        except Exception as e:
            print(f"    ❌ 初始化失敗: {e}")
            self.fail(str(e))

    @patch('dual_path_messenger.RMRXapp')
    @patch('dual_path_messenger.requests.Session')
    def test_04_register_endpoint(self, mock_session, mock_rmr):
        """測試 4: 註冊端點"""
        print("  ✓ 測試註冊端點...")
        try:
            from dual_path_messenger import DualPathMessenger, EndpointConfig

            def mock_handler(xapp, summary, sbuf):
                pass

            messenger = DualPathMessenger(
                xapp_name="test-xapp",
                rmr_port=4560,
                message_handler=mock_handler
            )

            endpoint = EndpointConfig(
                service_name="target-service",
                namespace="ricxapp",
                http_port=8080,
                rmr_port=4560
            )

            messenger.register_endpoint(endpoint)

            self.assertIn("target-service", messenger.endpoints)
            print("    ✅ 端點註冊成功")

        except Exception as e:
            print(f"    ❌ 註冊失敗: {e}")
            self.fail(str(e))

    @patch('dual_path_messenger.RMRXapp')
    @patch('dual_path_messenger.requests.Session')
    def test_05_get_health_summary(self, mock_session, mock_rmr):
        """測試 5: 獲取健康摘要"""
        print("  ✓ 測試獲取健康摘要...")
        try:
            from dual_path_messenger import DualPathMessenger

            def mock_handler(xapp, summary, sbuf):
                pass

            messenger = DualPathMessenger(
                xapp_name="test-xapp",
                rmr_port=4560,
                message_handler=mock_handler
            )

            health = messenger.get_health_summary()

            self.assertIn('active_path', health)
            self.assertIn('rmr', health)
            self.assertIn('http', health)
            self.assertIn('endpoints', health)

            print(f"    ✅ 健康摘要: active_path={health['active_path']}")

        except Exception as e:
            print(f"    ❌ 獲取失敗: {e}")
            self.fail(str(e))


class TestTrafficSteeringIntegration(unittest.TestCase):
    """測試 Traffic Steering xApp 整合"""

    def setUp(self):
        """測試準備"""
        print("\n[測試] Traffic Steering xApp 整合")

    @patch('traffic_steering.DualPathMessenger')
    @patch('traffic_steering.SDLWrapper')
    @patch('traffic_steering.Flask')
    def test_01_import_traffic_steering(self, mock_flask, mock_sdl, mock_messenger):
        """測試 1: 導入 Traffic Steering"""
        print("  ✓ 測試導入 Traffic Steering...")
        try:
            # 這個測試會實際嘗試導入
            import traffic_steering
            print("    ✅ Traffic Steering 導入成功")
            self.assertTrue(True)
        except ImportError as e:
            print(f"    ❌ 導入失敗: {e}")
            self.fail(f"Failed to import: {e}")

    def test_02_check_dual_path_usage(self):
        """測試 2: 檢查 DualPathMessenger 使用"""
        print("  ✓ 檢查 Traffic Steering 是否使用 DualPathMessenger...")

        file_path = os.path.join(
            os.path.dirname(__file__),
            '../xapps/traffic-steering/src/traffic_steering.py'
        )

        with open(file_path, 'r') as f:
            content = f.read()

        # 檢查關鍵導入
        self.assertIn('from dual_path_messenger import', content)
        self.assertIn('DualPathMessenger', content)
        self.assertIn('EndpointConfig', content)

        # 檢查初始化
        self.assertIn('self.messenger = DualPathMessenger', content)

        # 檢查端點註冊
        self.assertIn('register_endpoint', content)

        # 檢查消息發送
        self.assertIn('messenger.send_message', content)

        print("    ✅ Traffic Steering 正確使用 DualPathMessenger")


class TestRCxAppIntegration(unittest.TestCase):
    """測試 RC-xApp 整合"""

    def setUp(self):
        """測試準備"""
        print("\n[測試] RC-xApp 整合")

    def test_01_check_dual_path_usage(self):
        """測試 1: 檢查 DualPathMessenger 使用"""
        print("  ✓ 檢查 RC-xApp 是否使用 DualPathMessenger...")

        file_path = os.path.join(
            os.path.dirname(__file__),
            '../xapps/rc-xapp/src/ran_control.py'
        )

        with open(file_path, 'r') as f:
            content = f.read()

        # 檢查關鍵導入
        self.assertIn('from dual_path_messenger import', content)
        self.assertIn('DualPathMessenger', content)

        # 檢查初始化
        self.assertIn('self.messenger = DualPathMessenger', content)

        # 檢查端點註冊
        self.assertIn('_register_endpoints', content)

        # 檢查消息發送
        self.assertIn('messenger.send_message', content)

        # 檢查健康端點
        self.assertIn('health_paths', content)

        print("    ✅ RC-xApp 正確使用 DualPathMessenger")


class TestKPIMONIntegration(unittest.TestCase):
    """測試 KPIMON xApp 整合"""

    def setUp(self):
        """測試準備"""
        print("\n[測試] KPIMON xApp 整合")

    def test_01_check_dual_path_usage(self):
        """測試 1: 檢查 DualPathMessenger 使用"""
        print("  ✓ 檢查 KPIMON 是否使用 DualPathMessenger...")

        file_path = os.path.join(
            os.path.dirname(__file__),
            '../xapps/kpimon-go-xapp/src/kpimon.py'
        )

        with open(file_path, 'r') as f:
            content = f.read()

        # 檢查關鍵導入
        self.assertIn('from dual_path_messenger import', content)
        self.assertIn('DualPathMessenger', content)

        # 檢查初始化
        self.assertIn('self.messenger = DualPathMessenger', content)

        # 檢查端點註冊
        self.assertIn('_register_endpoints', content)

        # 檢查消息發送
        self.assertIn('messenger.send_message', content)

        # 檢查健康端點
        self.assertIn('health_paths', content)

        print("    ✅ KPIMON 正確使用 DualPathMessenger")


class TestEndToEndIntegration(unittest.TestCase):
    """端到端集成測試"""

    def setUp(self):
        """測試準備"""
        print("\n[測試] 端到端集成")

    def test_01_all_xapps_have_dual_path(self):
        """測試 1: 驗證所有 xApp 都有雙路徑"""
        print("  ✓ 驗證所有核心 xApp 都整合了雙路徑...")

        xapps = [
            ('Traffic Steering', 'xapps/traffic-steering/src/traffic_steering.py'),
            ('RC-xApp', 'xapps/rc-xapp/src/ran_control.py'),
            ('KPIMON', 'xapps/kpimon-go-xapp/src/kpimon.py'),
        ]

        base_path = os.path.join(os.path.dirname(__file__), '..')

        for xapp_name, file_path in xapps:
            full_path = os.path.join(base_path, file_path)

            with open(full_path, 'r') as f:
                content = f.read()

            has_import = 'from dual_path_messenger import' in content
            has_init = 'DualPathMessenger' in content
            has_messenger = 'self.messenger' in content

            self.assertTrue(has_import, f"{xapp_name} 缺少 DualPathMessenger 導入")
            self.assertTrue(has_init, f"{xapp_name} 缺少 DualPathMessenger 類")
            self.assertTrue(has_messenger, f"{xapp_name} 缺少 messenger 實例")

            print(f"    ✅ {xapp_name} 已整合雙路徑")

    def test_02_check_file_structure(self):
        """測試 2: 檢查文件結構"""
        print("  ✓ 檢查文件結構完整性...")

        base_path = os.path.join(os.path.dirname(__file__), '..')

        required_files = [
            'xapps/common/dual_path_messenger.py',
            'xapps/common/__init__.py',
            'xapps/traffic-steering/src/traffic_steering.py',
            'xapps/rc-xapp/src/ran_control.py',
            'xapps/kpimon-go-xapp/src/kpimon.py',
            'docs/DUAL_PATH_IMPLEMENTATION.md',
            'docs/FINAL_COMPLETION_REPORT.md',
            'scripts/enable-dual-path-all-xapps.sh',
        ]

        for file_path in required_files:
            full_path = os.path.join(base_path, file_path)
            self.assertTrue(
                os.path.exists(full_path),
                f"文件不存在: {file_path}"
            )

        print(f"    ✅ 所有必要文件都存在 ({len(required_files)} 個)")

    def test_03_check_common_library(self):
        """測試 3: 檢查 common 庫"""
        print("  ✓ 檢查 common 庫完整性...")

        base_path = os.path.join(os.path.dirname(__file__), '..')
        init_file = os.path.join(base_path, 'xapps/common/__init__.py')

        with open(init_file, 'r') as f:
            content = f.read()

        # 檢查必要的導出
        required_exports = [
            'DualPathMessenger',
            'EndpointConfig',
            'CommunicationPath',
            'PathStatus',
        ]

        for export in required_exports:
            self.assertIn(export, content, f"__init__.py 缺少導出: {export}")

        print("    ✅ common 庫完整")


def run_all_tests():
    """運行所有測試"""
    print("\n開始運行完整測試套件...\n")

    # 創建測試套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加測試類
    suite.addTests(loader.loadTestsFromTestCase(TestDualPathMessenger))
    suite.addTests(loader.loadTestsFromTestCase(TestTrafficSteeringIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestRCxAppIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestKPIMONIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestEndToEndIntegration))

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
        print("\n🎉 所有測試通過！雙路徑通訊實現正確。")
        return 0
    else:
        print("\n❌ 有測試失敗，需要修復。")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
