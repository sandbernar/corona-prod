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

createExtensionQuery = "CREATE EXTENSION postgis;"
addGeomColumnQuery = "SELECT AddGeometryColumn('Address', 'geom', 4326, 'Point',2);"
createGeomTriggerQuery = """
CREATE OR REPLACE FUNCTION add_geom() RETURNS trigger AS
    $$
    BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF NEW.lng IS DISTINCT FROM OLD.lng OR NEW.lat IS DISTINCT FROM OLD.lat THEN
            UPDATE "Address" SET geom = ST_SetSRID(ST_MakePoint(NEW.lng, NEW.lat), 4326) WHERE id=NEW.id;
        END IF;
    ELSE 
        UPDATE "Address" SET geom = ST_SetSRID(ST_MakePoint(NEW.lng, NEW.lat), 4326) WHERE id=NEW.id;
    END IF;
    RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
"""
addGeomTriggerQuery = 'CREATE TRIGGER add_geom_trigger AFTER INSERT OR UPDATE ON "Address" FOR EACH ROW EXECUTE PROCEDURE add_geom();'

# logging.history trigger
try:
    psqlCursor.execute(createSchemeQuery)
    psqlCursor.execute(createTableQuery)
    psqlCursor.execute(createTriggerQuery)
except Exception as e:
    print(e)

# POSTGIS EXTENSION
try:
    psqlCursor.execute(createExtensionQuery)
    try: # ADD GEOM COLUMN
        psqlCursor.execute(addGeomColumnQuery)
        try: # CREATE TRIGGER FUNCTION add_geom
            psqlCursor.execute(createGeomTriggerQuery)
            try: # ADD TRIGGER TO ADDRESS
                psqlCursor.execute(addGeomTriggerQuery)
            except Exception as e:
                print(e)
        except Exception as e:
            print(e)

        addresses = psqlCursor.execute('SELECT * FROM "Address";')
        for address in addresses:
            if address["geom"] is None and address["lng"] is not None and address["lat"] is not None:
                psqlCursor.execute('UPDATE "Address" SET geom = ST_SetSRID(ST_MakePoint(%d, %d), 4326) WHERE id=%d;' % (
                    address["lng"],
                    address["lat"],
                    address["id"]
                ))
    except Exception as e:
        print(e)
except Exception as e:
    print(e)

print("init log done.")
