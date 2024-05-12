import unittest
from decimal import Decimal
from ShortCircuitCalc.tools import config_manager


class TestConfigManager(unittest.TestCase):
    def test_get_config(self):
        self.cm_get1 = config_manager('SQLITE_DB_NAME')
        self.cm_get2 = config_manager('DB_EXISTING_CONNECTION')
        self.cm_get3 = config_manager('DB_TABLES_CLEAR_INSTALL')
        self.cm_get4 = config_manager('ENGINE_ECHO')

        self.cm_get5 = config_manager('SYSTEM_PHASES')
        self.cm_get6 = config_manager('SYSTEM_VOLTAGE_IN_KILOVOLTS')
        self.cm_get7 = config_manager('CALCULATIONS_ACCURACY')

        self.cm_get8 = config_manager('SOMETHING_NOT_EXISTING')

        self.assertEqual(self.cm_get1, 'electrical_product_catalog.db')
        self.assertEqual(self.cm_get2, 'SQLite')
        self.assertEqual(self.cm_get3, True)
        self.assertEqual(self.cm_get4, False)

        self.assertEqual(self.cm_get5, 3)
        self.assertEqual(self.cm_get6, Decimal('0.4'))
        self.assertEqual(self.cm_get7, 3)

        self.assertEqual(self.cm_get8, None)

    def test_set_config(self):
        self.cm_set1 = config_manager('SQLITE_DB_NAME')
        self.cm_set2 = config_manager('SQLITE_DB_NAME', 'config_test.db')
        self.cm_set3 = config_manager('SQLITE_DB_NAME')
        self.cm_set4 = config_manager('SQLITE_DB_NAME', 'electrical_product_catalog.db')
        self.cm_set5 = config_manager('SQLITE_DB_NAME')

        self.assertEqual(self.cm_set1, 'electrical_product_catalog.db')
        self.assertEqual(self.cm_set3, 'config_test.db')
        self.assertEqual(self.cm_set5, 'electrical_product_catalog.db')

        self.cm_set11 = config_manager('DB_EXISTING_CONNECTION')
        self.cm_set12 = config_manager('DB_EXISTING_CONNECTION', False)
        self.cm_set13 = config_manager('DB_EXISTING_CONNECTION')
        self.cm_set14 = config_manager('DB_EXISTING_CONNECTION', 'SQLite')
        self.cm_set15 = config_manager('DB_EXISTING_CONNECTION')

        self.assertEqual(self.cm_set11, 'SQLite')
        self.assertEqual(self.cm_set13, False)
        self.assertEqual(self.cm_set15, 'SQLite')

        self.cm_set21 = config_manager('DB_TABLES_CLEAR_INSTALL')
        self.cm_set22 = config_manager('DB_TABLES_CLEAR_INSTALL', False)
        self.cm_set23 = config_manager('DB_TABLES_CLEAR_INSTALL')
        self.cm_set24 = config_manager('DB_TABLES_CLEAR_INSTALL', True)
        self.cm_set25 = config_manager('DB_TABLES_CLEAR_INSTALL')

        self.assertEqual(self.cm_set21, True)
        self.assertEqual(self.cm_set23, False)
        self.assertEqual(self.cm_set25, True)

        self.cm_set31 = config_manager('SYSTEM_PHASES')
        self.cm_set32 = config_manager('SYSTEM_PHASES', 1)
        self.cm_set33 = config_manager('SYSTEM_PHASES')
        self.cm_set34 = config_manager('SYSTEM_PHASES', 3)
        self.cm_set35 = config_manager('SYSTEM_PHASES')

        self.assertEqual(self.cm_set31, 3)
        self.assertEqual(self.cm_set33, 1)
        self.assertEqual(self.cm_set35, 3)

        self.cm_set41 = config_manager('SYSTEM_VOLTAGE_IN_KILOVOLTS')
        self.cm_set42 = config_manager('SYSTEM_VOLTAGE_IN_KILOVOLTS', 0.4)
        self.cm_set43 = config_manager('SYSTEM_VOLTAGE_IN_KILOVOLTS')
        self.cm_set44 = config_manager('SYSTEM_VOLTAGE_IN_KILOVOLTS', Decimal('0.4'))
        self.cm_set45 = config_manager('SYSTEM_VOLTAGE_IN_KILOVOLTS')

        self.assertEqual(self.cm_set41, Decimal('0.4'))
        self.assertEqual(self.cm_set43, 0.4)
        self.assertEqual(self.cm_set45, Decimal('0.4'))


if __name__ == '__main__':
    unittest.main()
