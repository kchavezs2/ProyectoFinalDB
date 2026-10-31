import os
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from database.sql_manager import SQLDatabaseManager
from database.nosql_manager import NoSQLDatabaseManager

class Backends(unittest.TestCase):
    def test_sql_ddl_dml_y_error(self):
        with tempfile.TemporaryDirectory() as d:
            s=SQLDatabaseManager()
            self.assertTrue(s.connect(str(Path(d)/'sql.db'))['success'])
            for q in ('CREATE TABLE demo (id INTEGER PRIMARY KEY, nombre TEXT);',"INSERT INTO demo VALUES (1,'Ana');",'SELECT * FROM demo;'):
                r=s.execute_query(q);self.assertTrue(r['success'],r['message'])
            self.assertEqual(r['rows'][0][1],'Ana')
            self.assertFalse(s.execute_query('SELECT * FROM inexistente;')['success'])
            s.disconnect()
            self.assertTrue(s.connect(str(Path(d)/'sql.db'))['success'])
            self.assertEqual(s.execute_query('SELECT * FROM demo;')['rows'][0][1],'Ana')
            s.disconnect()
    def test_nosql_ddl_dml_persistencia(self):
        with tempfile.TemporaryDirectory() as d:
            n=NoSQLDatabaseManager()
            self.assertTrue(n.connect(str(Path(d)/'nodb'))['success'])
            self.assertTrue(n.execute_command('db.createCollection("proyectos")')['success'])
            self.assertTrue(n.execute_command('db.proyectos.insertOne({"codigo":"P-01","activo":true})')['success'])
            self.assertEqual(len(n.execute_command('db.proyectos.find({})')['rows']),1)
            self.assertTrue(n.execute_command('db.proyectos.updateOne({"codigo":"P-01"},{"$set":{"activo":false}})')['success'])
            self.assertEqual(n.execute_command('db.proyectos.find({"activo":false})')['rows'][0][1], 'P-01')
            n.disconnect()
            self.assertTrue(n.connect(str(Path(d)/'nodb'))['success'])
            self.assertEqual(len(n.execute_command('db.proyectos.find({})')['rows']),1)
            self.assertTrue(n.execute_command('db.proyectos.deleteOne({"codigo":"P-01"})')['success'])
            self.assertEqual(n.execute_command('db.proyectos.find({})')['rows'],[])
            self.assertFalse(n.execute_command('db.proyectos.find({"bad": )')['success'])
            n.disconnect()
if __name__=='__main__':unittest.main(verbosity=2)
