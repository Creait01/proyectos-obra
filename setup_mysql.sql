-- Script para crear la base de datos en MySQL
-- Ejecutar en MySQL como administrador

-- Crear la base de datos
CREATE DATABASE IF NOT EXISTS proyectos_obra 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- Crear usuario para la aplicación (opcional, puedes usar root)
-- CREATE USER 'proyectos_user'@'%' IDENTIFIED BY 'tu_password_seguro';
-- GRANT ALL PRIVILEGES ON proyectos_obra.* TO 'proyectos_user'@'%';
-- FLUSH PRIVILEGES;

-- Usar la base de datos
USE proyectos_obra;

-- Las tablas se crean automáticamente al iniciar la aplicación
-- gracias a SQLAlchemy
