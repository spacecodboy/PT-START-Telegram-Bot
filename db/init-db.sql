\c telegram_bot

CREATE ROLE repl_user WITH REPLICATION LOGIN ENCRYPTED PASSWORD 'Qq12345';
SELECT pg_create_physical_replication_slot('replication_slot');

CREATE TABLE emails (
  id SERIAL PRIMARY KEY,
  email VARCHAR(100) NOT NULL
);

CREATE TABLE phone_numbers (
  id SERIAL PRIMARY KEY,
  phone_number VARCHAR(18) NOT NULL
);

INSERT INTO emails (email) VALUES ('ivan.pepe@nstu.ru'), ('olga.petrova@gmail.com');

INSERT INTO phone_numbers (phone_number) VALUES ('+7 (900) 567 21 22'), ('8(905)-376-99-45');
