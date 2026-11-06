-- ATENCIÓN: borra todos los esquemas del PoC. Solo para desarrollo.
BEGIN;

DROP SCHEMA IF EXISTS operaciones CASCADE;
DROP SCHEMA IF EXISTS auditoria CASCADE;
DROP SCHEMA IF EXISTS almacen CASCADE;
DROP SCHEMA IF EXISTS seguridad CASCADE;

DROP ROLE IF EXISTS rol_admin;
DROP ROLE IF EXISTS rol_operador;
DROP ROLE IF EXISTS rol_auditor;

COMMIT;
