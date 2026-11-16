CREATE DATABASE IF NOT EXISTS ecotrack
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'ecotrack_user'@'localhost'
IDENTIFIED BY '3688';

ALTER USER 'ecotrack_user'@'localhost'
IDENTIFIED BY '3688';

GRANT ALL PRIVILEGES ON ecotrack.*
TO 'ecotrack_user'@'localhost';

FLUSH PRIVILEGES;