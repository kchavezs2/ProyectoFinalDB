-- Ejecutar cada bloque por separado en el IDE (las plantillas ya están cargadas).
CREATE TABLE IF NOT EXISTS estudiantes (id INTEGER PRIMARY KEY AUTOINCREMENT, carnet TEXT UNIQUE NOT NULL, nombre TEXT NOT NULL, promedio REAL NOT NULL);
INSERT OR IGNORE INTO estudiantes(carnet,nombre,promedio) VALUES ('2026-101','Ana',91.5),('2026-102','Carlos',86.0),('2026-103','Maria',95.2);
SELECT * FROM estudiantes;
UPDATE estudiantes SET promedio=94 WHERE carnet='2026-102';
SELECT * FROM estudiantes;
DELETE FROM estudiantes WHERE carnet='2026-103';
SELECT * FROM estudiantes;
-- Para ALTER TABLE, hacerlo una sola vez sobre la tabla.
-- ALTER TABLE estudiantes ADD COLUMN semestre INTEGER DEFAULT 1;
-- Para reiniciar: DROP TABLE IF EXISTS estudiantes;
