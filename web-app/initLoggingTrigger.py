import os
import psycopg2

psqlConn = psycopg2.connect(dbname=os.getenv("DATABASE_NAME"),
                            user=os.getenv("DATABASE_USER"),
                            password=os.getenv("DATABASE_PASSWORD"),
                            host=os.getenv("DATABASE_HOST"))

psqlConn.autocommit = True
psqlCursor = psqlConn.cursor()

createSchemeQuery = "CREATE SCHEMA logging;"
createTableQuery = """
CREATE TABLE IF NOT EXISTS logging.t_history (
    id serial,
    tstamp timestamp DEFAULT now(),
    schemaname text,
    tabname text,
    operation text,
    new_val json,
    old_val json
);
"""
createTriggerQuery = """
CREATE OR REPLACE FUNCTION change_trigger() RETURNS trigger AS $$
    BEGIN
        IF TG_OP = 'INSERT'
        THEN
            INSERT INTO logging.t_history (tabname, schemaname, operation, new_val)
                    VALUES (TG_RELNAME, TG_TABLE_SCHEMA, TG_OP, row_to_json(NEW));
            RETURN NEW;
        ELSIF TG_OP = 'UPDATE'
        THEN
            INSERT INTO logging.t_history (tabname, schemaname, operation, new_val, old_val)
                    VALUES (TG_RELNAME, TG_TABLE_SCHEMA, TG_OP,
                            row_to_json(NEW), row_to_json(OLD));
            RETURN NEW;
        ELSIF TG_OP = 'DELETE'
        THEN
            INSERT INTO logging.t_history (tabname, schemaname, operation, old_val)
                    VALUES (TG_RELNAME, TG_TABLE_SCHEMA, TG_OP, row_to_json(OLD));
            RETURN OLD;
        END IF;
    END;
$$ LANGUAGE 'plpgsql' SECURITY DEFINER;
"""

try:
    psqlCursor.execute(createSchemeQuery)
    psqlCursor.execute(createTableQuery)
    psqlCursor.execute(createTriggerQuery)
except Exception as e:
    print(e)

print("init log done.")
