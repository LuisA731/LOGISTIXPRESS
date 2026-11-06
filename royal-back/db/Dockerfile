FROM postgres:16-alpine

COPY 01_esquema.sql /docker-entrypoint-initdb.d/01_esquema.sql
COPY 02_semilla.sql /docker-entrypoint-initdb.d/02_semilla.sql
RUN chmod 0644 /docker-entrypoint-initdb.d/*.sql
