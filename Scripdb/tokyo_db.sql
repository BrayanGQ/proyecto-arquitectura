-- Database: tokyo_db

-- DROP DATABASE IF EXISTS tokyo_db;

CREATE DATABASE tokyo_db
    WITH
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'Spanish_Spain.1252'
    LC_CTYPE = 'Spanish_Spain.1252'
    LOCALE_PROVIDER = 'libc'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    IS_TEMPLATE = False;

GRANT TEMPORARY, CONNECT ON DATABASE tokyo_db TO PUBLIC;

GRANT CREATE, CONNECT ON DATABASE tokyo_db TO postgres;
GRANT TEMPORARY ON DATABASE tokyo_db TO postgres WITH GRANT OPTION;

CREATE TABLE eventos (
    id SERIAL PRIMARY KEY,
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ubicacion VARCHAR(100) NOT NULL,
    tipo_evento VARCHAR(100) NOT NULL,
    descripcion TEXT,
    sensor VARCHAR(100) NOT NULL
);