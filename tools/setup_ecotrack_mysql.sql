-- ============================================================================
-- EcoTrack - MySQL 8 database setup
-- ============================================================================
-- Smart Waste Management System
--
-- IMPORTANT: This script must be executed in MySQL Workbench (or the MySQL
-- command-line client) using an authorized MySQL administrator account. Do NOT
-- run it from PowerShell or from the EcoTrack application.
--
-- Do NOT modify the MySQL root password. Do NOT grant global privileges.
-- Privileges are granted only on ecotrack.*.
--
-- Before running: replace every occurrence of the placeholder below with a
-- strong, unique password. The same password must be set in the EcoTrack
-- .env file as DB_PASSWORD.
--
-- Placeholder: REPLACE_ME_WITH_A_STRONG_PASSWORD
-- ============================================================================

-- 1. Create the ecotrack database if it does not exist.
CREATE DATABASE IF NOT EXISTS ecotrack
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- 2. Create ecotrack_user if it does not exist (localhost and 127.0.0.1).
--    MySQL 8 treats 'localhost' and '127.0.0.1' as distinct hosts, so both
--    accounts are created for compatibility.
CREATE USER IF NOT EXISTS 'ecotrack_user'@'localhost'
    IDENTIFIED BY 'REPLACE_ME_WITH_A_STRONG_PASSWORD';

CREATE USER IF NOT EXISTS 'ecotrack_user'@'127.0.0.1'
    IDENTIFIED BY 'REPLACE_ME_WITH_A_STRONG_PASSWORD';

-- 3. Update the account password (applies whether the user is new or existing).
ALTER USER 'ecotrack_user'@'localhost'
    IDENTIFIED BY 'REPLACE_ME_WITH_A_STRONG_PASSWORD';

ALTER USER 'ecotrack_user'@'127.0.0.1'
    IDENTIFIED BY 'REPLACE_ME_WITH_A_STRONG_PASSWORD';

-- 4. Grant privileges only on ecotrack.* (no global privileges).
GRANT ALL PRIVILEGES ON ecotrack.* TO 'ecotrack_user'@'localhost';
GRANT ALL PRIVILEGES ON ecotrack.* TO 'ecotrack_user'@'127.0.0.1';

-- 5. Flush privileges.
FLUSH PRIVILEGES;

-- 6. Verify user and host entries.
SELECT user, host FROM mysql.user WHERE user = 'ecotrack_user' ORDER BY host;

SHOW GRANTS FOR 'ecotrack_user'@'localhost';
SHOW GRANTS FOR 'ecotrack_user'@'127.0.0.1';

-- ============================================================================
-- After running this script:
--   - Edit EcoTrack/.env (source) or the .env next to EcoTrack.exe (packaged)
--     and set DB_PASSWORD to the same password chosen above.
--   - Set SECRET_KEY to a strong value (at least 16 characters).
--   - Run migrations from source:  python -m flask --app run.py db upgrade
-- ============================================================================
